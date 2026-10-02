"""Nightly Grid Docket collection run (GitHub Actions).

Writes, all under data/:
  filings/<jur>/<source>/<id>.json   item metadata + extracted full text of each document
  candidates/<date>.jsonl            one line per NEW item this night (no text; points at the filing file)
  health/<date>.json                 per-source status, counts, errors, circuit breakers
  state/collector_state.json         seen ids, per-source watermarks and failure counts

The Monday Sweep reads candidates since its last run, opens the filing files and
classifies them into tracker rows. The collector never classifies and never
writes the row store.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import signal
import sys
import time
import traceback

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Http, Blocked, DATA, ROOT, extract, load_json, save_json, sha256, slug, now_utc, today  # noqa
import adapters as A  # noqa

STATE = os.path.join(DATA, "state", "collector_state.json")
DEFAULT_SINCE = "2026-09-15"          # first run overlaps the 2026-09-18 baseline by three days
OVERLAP_DAYS = 3
MAX_DOCS = int(os.environ.get("MAX_DOCS", "160"))
MAX_BYTES = 60 * 1024 * 1024
ADAPTER_BUDGET_S = int(os.environ.get("ADAPTER_BUDGET_S", "420"))
BUDGETS = {"ir_decks": 1200, "watch_pages": 900, "edgar": 900, "ferc": 600, "la_lpsc": 600, "mo_efis": 600}
RUN_DEADLINE_S = int(os.environ.get("RUN_DEADLINE_S", str(70 * 60)))   # the job is killed at 90 min; stop well before
BACKFILL_SINCE = os.environ.get("BACKFILL_SINCE") or None   # one-off history pull: candidates go to data/backfill/
PRIORITY = re.compile(r"order|tariff|rate schedule|settlement|stipulation|brief|testimony|compliance|agreement|contract|"
                      r"application|petition|complaint|protest|comments|report|notice of hearing|rule|directive|"
                      r"large load|data cent", re.I)
BASELINE_SOURCES = {"watch_pages", "rss", "ir_decks", "mirrors"}   # undated lists: first sight = baseline


class Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise Timeout()


class Ctx:
    def __init__(self, cfg, state, http):
        self.cfg, self.http, self.root_state = cfg, http, state
        self.today = today()
        self.state = {}
        self.since = DEFAULT_SINCE
        self.notes, self.sub = [], {}
        self._pw = self._browser = None

    def log(self, msg):
        self.notes.append(str(msg)[:400])
        print("  .", msg, flush=True)

    def record(self, sub_id, status, note=""):
        self.sub[sub_id] = {"status": status, "note": note[:300]}

    def render(self, url, wait_ms=4000):
        if not self.http.allowed(url):
            raise Blocked(f"robots.txt disallows {url}")
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch()
        hs = self.http._host(url)
        self.http._wait(hs)
        page = self._browser.new_context(user_agent=self.http.session.headers["User-Agent"]).new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
            page.wait_for_timeout(wait_ms)
            html = page.content()
        finally:
            page.context.close()
        from common import looks_blocked
        m = looks_blocked(html[:30000])
        if m and len(html) < 80000:
            raise Blocked(f"block page ({m}) at {url}")
        return html

    def close(self):
        try:
            if self._browser:
                self._browser.close()
                self._pw.stop()
        except Exception:
            pass


def fetch_docs(http, item, ctx):
    """Download and extract every document an item points at."""
    docs = []
    for spec in item.get("fetch") or []:
        urls = []
        try:
            if "url" in spec:
                urls = [spec["url"]]
            elif "tx_item" in spec:
                urls = A.tx_files(http, *spec["tx_item"])
            elif "ga_document" in spec:
                urls = A.ga_files(http, spec["ga_document"])
            elif "la_document" in spec:
                urls = A.la_files(http, spec["la_document"])
            elif "mo_filing" in spec:
                urls = A.mo_files(http, spec["mo_filing"])
            elif "ferc_file" in spec:
                r = A.ferc_download(http, spec["ferc_file"])
                docs.append(_doc(r.url, r.content, r.headers.get("content-type", ""), spec.get("name")))
                continue
        except Blocked as e:
            docs.append({"url": str(spec)[:300], "error": f"blocked: {e}"})
            continue
        except Exception as e:
            docs.append({"url": str(spec)[:300], "error": repr(e)[:300]})
            continue
        for u in urls[:6]:
            try:
                r = http.get(u, stream=False)
                if len(r.content) > MAX_BYTES:
                    docs.append({"url": u, "error": f"too large ({len(r.content)} bytes)"})
                    continue
                docs.append(_doc(u, r.content, r.headers.get("content-type", ""), None))
            except Blocked as e:
                docs.append({"url": u, "error": f"blocked: {e}"})
            except Exception as e:
                docs.append({"url": u, "error": repr(e)[:300]})
    return docs


def _doc(url, content, ctype, name):
    ex = extract(content, ctype, url)
    return {"url": url, "name": name, "bytes": len(content), "sha256": sha256(content), "ctype": ctype,
            "quality": ex.get("quality"), "ocr": ex.get("ocr", False), "pages": ex.get("pages"),
            "truncated": ex.get("truncated", False), "text": ex.get("text", "")}


def keyword_hit(item, docs, kws):
    hay = " ".join([item.get("title") or "", json.dumps(item.get("meta") or {})[:3000]] +
                   [d.get("text", "")[:200000] for d in docs]).lower()
    return sorted({k for k in kws if k.lower() in hay})


def main(only=None):
    cfg = yaml.safe_load(open(os.path.join(ROOT, "config", "watchlist.yaml")))
    state = load_json(STATE, {"seen": {}, "sources": {}, "baselined": [], "runs": 0})
    state["runs"] = state.get("runs", 0) + 1
    http = Http(delay=float(os.environ.get("DELAY_S", "3")))
    http.session.headers["User-Agent"] = cfg.get("user_agent") or http.session.headers["User-Agent"]
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d-%H%M")
    health = {"backfill_since": BACKFILL_SINCE, "run_id": run_id, "started": now_utc(), "sources": {}, "docs_fetched": 0, "new_items": 0,
              "user_agent": http.session.headers["User-Agent"]}
    cand_path = os.path.join(DATA, "backfill" if BACKFILL_SINCE else "candidates", f"{today()}.jsonl")
    os.makedirs(os.path.dirname(cand_path), exist_ok=True)
    kws = cfg.get("keywords", [])
    parties = cfg.get("parties", [])
    docs_budget = MAX_DOCS
    signal.signal(signal.SIGALRM, _alarm)
    run_t0 = time.time()
    # rotate the starting adapter each run so a slow source never starves the same ones behind it
    names = [n for n in A.ADAPTERS if (not only or n in only) and not (BACKFILL_SINCE and n in BASELINE_SOURCES)]
    k = state["runs"] % len(names) if names else 0
    order = names[k:] + names[:k]

    def checkpoint():
        state["last_run"] = now_utc()
        health["finished"] = now_utc()
        save_json(STATE, state)
        if BACKFILL_SINCE:   # never masquerade as the nightly health record
            save_json(os.path.join(DATA, "backfill", f"health_{run_id}.json"), health)
            return
        save_json(os.path.join(DATA, "health", f"{today()}.json"), health)
        save_json(os.path.join(DATA, "health", "latest.json"), health)

    for name in order:
        fn = A.ADAPTERS[name]
        left = RUN_DEADLINE_S - (time.time() - run_t0)
        if left < 60:
            health["sources"][name] = {"status": "SKIPPED_RUN_DEADLINE", "note": "run deadline reached; first in line next run"}
            print(name, "SKIPPED (run deadline)", flush=True)
            continue
        sst = state["sources"].setdefault(name, {"consecutive_failures": 0})
        cf = sst.get("consecutive_failures", 0)
        if cf >= 6 and state["runs"] % 4 != 0:
            health["sources"][name] = {"status": "CIRCUIT_OPEN", "consecutive_failures": cf,
                                       "last_error": sst.get("last_error")}
            print(name, "CIRCUIT_OPEN", flush=True)
            continue
        ctx = Ctx(cfg, state, http)
        ctx.state = sst.setdefault("data", {})
        last_ok = sst.get("last_ok")
        ctx.since = (dt.date.fromisoformat(last_ok) - dt.timedelta(days=OVERLAP_DAYS)).isoformat() if last_ok else DEFAULT_SINCE
        if BACKFILL_SINCE:
            ctx.since = BACKFILL_SINCE
        t0 = time.time()
        rec = {"since": ctx.since}
        print(f"{name}: since {ctx.since}", flush=True)
        signal.alarm(int(max(30, min(BUDGETS.get(name, ADAPTER_BUDGET_S), left - 30))))
        try:
            items = fn(ctx) or []
            signal.alarm(0)
            # Undated lists (pages, feeds, decks, mirrors): the first time a list is seen, its existing
            # links are the baseline, not news. Tracked per list, so adding a page later never floods.
            bkeys = set(state.setdefault("baselined_keys", []))
            migrated = state.setdefault("bkey_migrated", [])
            if name in BASELINE_SOURCES and name in state["baselined"] and name not in migrated:
                # source baselined before per-list keys existed: its current lists are already baselined
                bkeys |= {(it.get("meta") or {}).get("bkey") for it in items} - {None}
                migrated.append(name)

            def is_baseline(it):
                return name in BASELINE_SOURCES and (it.get("meta") or {}).get("bkey", name) not in bkeys
            new = [it for it in items if it["id"] not in state["seen"]]
            nb = sum(1 for it in new if is_baseline(it))
            rec.update(found=len(items), new=len(new), baselined_now=nb)
            baseline = False
            kept = 0
            for it in new:
                state["seen"][it["id"]] = today()
                if is_baseline(it):
                    continue
                docs = []
                worth = not BACKFILL_SINCE or PRIORITY.search(it.get("title") or "") or it.get("kind") in ("deck", "8-K", "10-Q", "10-K")
                if docs_budget > 0 and it.get("fetch") and worth:
                    docs = fetch_docs(http, it, ctx)
                    docs_budget -= len(docs)
                    health["docs_fetched"] += len(docs)
                hits = keyword_hit(it, docs, kws)
                phits = keyword_hit(it, docs[:1], parties) if parties else []
                if (it.get("meta") or {}).get("keyword_filter") and not hits:
                    continue  # news/mirror link with nothing on-beat
                kept += 1
                fpath = os.path.join("data", "filings", slug(it.get("jur") or "NA", 12), slug(name, 30),
                                     slug(it["id"], 120) + ".json")
                save_json(os.path.join(ROOT, fpath), {**it, "collected_at": now_utc(), "run_id": run_id,
                                                      "keywords": hits, "party_hits": phits, "documents": docs})
                line = {k: it.get(k) for k in ("id", "jur", "source", "kind", "docket", "title", "filed", "url", "entity")}
                line.update(filing=fpath, keywords=hits, party_hits=phits, run_id=run_id,
                            docs=[{"url": d.get("url"), "quality": d.get("quality"), "ocr": d.get("ocr"),
                                   "chars": len(d.get("text") or ""), "error": d.get("error")} for d in docs],
                            meta={k: v for k, v in (it.get("meta") or {}).items() if k not in ("raw",)})
                with open(cand_path, "a") as f:
                    f.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
            if name in BASELINE_SOURCES:
                seen_keys = {(it.get("meta") or {}).get("bkey", name) for it in items}
                state["baselined_keys"] = sorted(bkeys | seen_keys)
                if name not in state["baselined"]:
                    state["baselined"].append(name)
            rec.update(kept=kept, status="ok", subsources=ctx.sub, notes=ctx.notes[-20:])
            health["new_items"] += kept
            sst.update(consecutive_failures=0, last_error=None, **({} if BACKFILL_SINCE else {"last_ok": today()}))
        except Blocked as e:
            signal.alarm(0)
            rec.update(status="ACCESS_REGRESSION", error=str(e)[:300], subsources=ctx.sub)
            sst["consecutive_failures"] = cf + 1
            sst["last_error"] = str(e)[:300]
        except Timeout:
            rec.update(status="PARTIAL", error=f"time budget {BUDGETS.get(name, ADAPTER_BUDGET_S)}s exceeded", subsources=ctx.sub)
            sst["consecutive_failures"] = cf + 1
            sst["last_error"] = "timeout"
        except Exception as e:
            signal.alarm(0)
            rec.update(status="ERROR", error=repr(e)[:300], trace=traceback.format_exc()[-1200:], subsources=ctx.sub)
            sst["consecutive_failures"] = cf + 1
            sst["last_error"] = repr(e)[:300]
        finally:
            ctx.close()
        rec["seconds"] = round(time.time() - t0, 1)
        rec["consecutive_failures"] = sst.get("consecutive_failures", 0)
        health["sources"][name] = rec
        checkpoint()
        print(f"  -> {rec.get('status')} found={rec.get('found')} new={rec.get('new')} kept={rec.get('kept')} {rec.get('error', '')}", flush=True)

    # prune seen ids older than 400 days
    cutoff = (dt.date.today() - dt.timedelta(days=400)).isoformat()
    state["seen"] = {k: v for k, v in state["seen"].items() if v >= cutoff}
    health["http_hosts"] = {h: {"robots": str(s.robots_status), "note": s.robots_note} for h, s in http.hosts.items()}
    health["seconds"] = round(time.time() - run_t0)
    checkpoint()
    bad = [k for k, v in health["sources"].items() if v.get("status") not in ("ok",)]
    print("DONE new_items", health["new_items"], "docs", health["docs_fetched"], "problem sources:", bad)


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
