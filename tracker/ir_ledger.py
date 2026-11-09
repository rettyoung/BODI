"""IR disclosure ledger: did the Sweep read every IR issuer's quarterly disclosure? (sweep.md 3.6; added 2026-11-09)

Why. For weeks six IR issuers (Southern, Evergy, Exelon, OGE, Oncor, BHE) were reported as "unreachable": their
events pages refuse the collector. But their earnings 8-Ks, Exelon's deck exhibit and the BHE 10-Q were in the
collector's data all along; the shortlist scored them like any filing and they sat behind the 40-item cut, and
nothing counted, per issuer and quarter, whether the disclosure had been read. This script does the counting.
The shortlist's earnings lane (shortlist.py, "E" lines) puts the filings in front of the Sweep; this ledger says
which issuers are still open and what to do next, and keeps the quarter as obligation IR-<YYYYQn> so
tracker/check_run.py fails a run that lets it go overdue.

usage
  python tracker/ir_ledger.py [--data <clone>/data] [--obligations store_live/obligations.json]
        [--seen store_live/seen_index.json] [--store store_live] [--shortlist work/shortlist.json]
        [--excerpts work/excerpts]
        [--quarter 2026Q3] [--today YYYY-MM-DD] [--out work/ir_ledger.json]
  Prints one line per issuer and a summary line; the JSON holds the same plus "obligation", the IR-<YYYYQn>
  item to merge into obligations.json (its "read" map is carried over from the existing item).

Per issuer (watchlist ir_ledger; edgar names default to the issuer name):
  READ      its earnings release (8-K Item 2.02/7.01) or, for expect: 10q, its 10-Q/10-K, has been read: the
            accession is in the obligation's "read" map, the seen index or a Source URL in the store
  TO_READ   filed and not yet read. NEXT names the shortlist "E" line, or a WebFetch of the EDGAR filing when the
            stored copy has no text (the collector re-collects such filings within 75 days)
  WAITING   nothing filed yet, inside the normal window (quarter end + 60 days)
  MISSING   nothing filed by quarter end + 60 days: check EDGAR by hand and the collector's edgar health
Decks (expect: deck) are reported in DECK but never gate: deck: edgar = an EX-99.2+ exhibit on the 8-K;
ir_page = an ir_decks candidate in the window; webfetch / manual = the route to take (deck_url).
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
EARNINGS_ITEMS = {"2.02", "7.01"}
DUE_DAYS = 75        # quarter end + 75 days: every 10-Q is in (10-Ks for Q4 by early March)
LATE_DAYS = 60       # no earnings filing by quarter end + 60 days = MISSING
DECK_EX_RE = re.compile(r"ex-?99[._-]?0?[2-9]\b|ex99[2-9]|presentation|slides", re.I)


def quarter_end(q):
    y, n = int(q[:4]), int(q[-1])
    return dt.date(y, 3 * n, 31 if n in (1, 4) else 30)


def current_quarter(today):
    """The most recent quarter whose earnings season has begun (ended at least 20 days ago)."""
    d = today - dt.timedelta(days=20)
    q = (d.month - 1) // 3 + 1
    end = quarter_end(f"{d.year}Q{q}")
    if end > d:
        q -= 1
        if q == 0:
            return f"{d.year - 1}Q4"
    return f"{d.year}Q{q}"


def load_watch():
    import yaml
    w = yaml.safe_load(open(os.path.join(ROOT, "config", "watchlist.yaml"), encoding="utf-8"))
    return w.get("ir_ledger") or []


def seen_strings(path):
    out = set()
    if not path or not os.path.exists(path):
        return out

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                out.add(str(k))
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            out.add(x)
    try:
        walk(json.load(open(path, encoding="utf-8")))
    except Exception as e:  # noqa
        print(f"warning: seen index unreadable ({e})", file=sys.stderr)
    return out


def store_urls(store):
    urls = []
    if not store:
        return urls
    for p in sorted(glob.glob(os.path.join(store, "rows_p*.json"))):
        try:
            j = json.load(open(p, encoding="utf-8"))
        except Exception:  # noqa
            continue
        for r in j.get("data") or j.get("rows") or []:
            if isinstance(r, list) and len(r) >= 26 and r[25]:
                urls.append(str(r[25]))
    return urls


def has_text(filing_rel):
    p = os.path.join(os.path.dirname(DATA), filing_rel) if filing_rel and not os.path.isabs(filing_rel) else filing_rel
    if not p or not os.path.exists(p):
        return False
    try:
        return any((d.get("text") or "").strip() for d in json.load(open(p, encoding="utf-8")).get("documents") or [])
    except Exception:  # noqa
        return False


def scan(qend, horizon):
    """EDGAR and ir_decks candidate lines dated in (quarter end, horizon]; one record per id (text-bearing first)."""
    out = {}
    for p in sorted(glob.glob(os.path.join(DATA, "candidates", "*.jsonl"))):
        day = os.path.basename(p)[:10]
        if not (qend.isoformat() < day <= horizon.isoformat()):
            continue
        for line in open(p, encoding="utf-8"):
            try:
                c = json.loads(line)
            except Exception:  # noqa
                continue
            if c.get("source") not in ("edgar", "ir_decks"):
                continue
            prev = out.get(c["id"])
            if prev and any((d or {}).get("chars") for d in prev.get("docs") or []):
                continue
            out[c["id"]] = c
    return list(out.values())


def write_excerpt(c, xdir):
    """Same excerpt the earnings lane writes (shortlist.py: large-load windows, exhibits first, <=12,000 chars)."""
    sys.path.insert(0, HERE)
    import shortlist  # noqa
    shortlist.DATA = DATA
    f = shortlist.load_filing(c.get("filing"))
    f["_path"] = c.get("filing")
    kws, parties, _ = shortlist.load_watch()
    text = shortlist.excerpt(f, shortlist.word_re(kws), shortlist.word_re(parties), cap=12000, win=500,
                             focus=shortlist.LOAD_RE)
    os.makedirs(xdir, exist_ok=True)
    p = os.path.join(xdir, "ir_" + shortlist.safe(c["id"]) + ".txt")
    open(p, "w", encoding="utf-8").write(text)
    return p


def acc_of(cid):
    return cid.split(":", 1)[1] if cid.startswith("SEC:") else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data")
    ap.add_argument("--obligations")
    ap.add_argument("--seen")
    ap.add_argument("--store")
    ap.add_argument("--shortlist")
    ap.add_argument("--quarter")
    ap.add_argument("--today")
    ap.add_argument("--out", default="work/ir_ledger.json")
    ap.add_argument("--excerpts", help="write a large-load excerpt (shortlist.py earnings rules) for each TO_READ "
                                       "filing that is not in this run's earnings lane, e.g. work/excerpts")
    a = ap.parse_args()
    global DATA
    if a.data:
        DATA = os.path.abspath(a.data)
    if not os.path.isdir(DATA):
        print(f"no collector data folder at {DATA}; pass --data <clone>/data", file=sys.stderr)
        sys.exit(2)
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    q = a.quarter or current_quarter(today)
    qend = quarter_end(q)
    due = qend + dt.timedelta(days=DUE_DAYS)
    late = qend + dt.timedelta(days=LATE_DAYS)
    oid = f"IR-{q}"

    obl, item = {}, None
    if a.obligations and os.path.exists(a.obligations):
        obl = json.load(open(a.obligations, encoding="utf-8"))
        item = next((x for x in obl.get("items") or [] if x.get("id") == oid), None)
    read_map = dict((item or {}).get("read") or {})
    seen = seen_strings(a.seen)
    urls = store_urls(a.store)
    lane = {}
    if a.shortlist and os.path.exists(a.shortlist):
        for i, r in enumerate(json.load(open(a.shortlist, encoding="utf-8")).get("earnings") or [], 1):
            lane[r["id"]] = f"E{i}"
    read_accs = {str(v.get("acc") if isinstance(v, dict) else v) for v in read_map.values()}

    def was_read(cid):
        acc = acc_of(cid) or ""
        nodash = acc.replace("-", "")
        return (acc in read_accs or cid in seen or acc in seen
                or (nodash and any(nodash in u for u in urls)))

    cands = scan(qend, min(today, qend + dt.timedelta(days=120)))
    rows, unread, missing = [], 0, 0
    for spec in load_watch():
        issuer = spec["issuer"]
        names = set(spec.get("edgar") or [issuer])
        expect = spec.get("expect", "deck")
        mine = [c for c in cands if c.get("source") == "edgar" and c.get("entity") in names]
        # foreign private issuers (Fortis) furnish releases on 6-K and report annually on 40-F
        rel = [c for c in mine if ((c.get("meta") or {}).get("form") == "8-K"
               and set((c.get("meta") or {}).get("items") or []) & EARNINGS_ITEMS)
               or (c.get("meta") or {}).get("form") == "6-K"]
        per = [c for c in mine if (c.get("meta") or {}).get("form") in ("10-Q", "10-K", "40-F")]
        rel.sort(key=lambda c: ("2.02" not in ((c.get("meta") or {}).get("items") or []), c.get("filed") or ""))
        gate = per if expect == "10q" else (rel or per)
        rec = {"issuer": issuer, "expect": expect, "release": [c["id"] for c in rel], "periodic": [c["id"] for c in per]}
        if issuer in read_map:
            rec.update(status="READ", via=read_map[issuer])
        elif any(was_read(c["id"]) for c in gate):
            c = next(c for c in gate if was_read(c["id"]))
            rec.update(status="READ", via={"acc": acc_of(c["id"]), "how": "seen index or store"})
        elif gate:
            c = gate[0]
            unread += 1
            if not has_text(c.get("filing")):
                nxt = f"WebFetch {c.get('url')} (stored copy has no text)"
            elif c["id"] in lane:
                nxt = f"read excerpt {lane[c['id']]}"
            elif a.excerpts:
                nxt = "read excerpt " + write_excerpt(c, a.excerpts)
            else:
                nxt = f"read {c['id']} (pass --excerpts to write its excerpt)"
            rec.update(status="TO_READ", id=c["id"], filed=c.get("filed"), next=nxt)
        elif today >= late:
            missing += 1
            rec.update(status="MISSING", next=f"no earnings 8-K or 10-Q from {'/'.join(sorted(names))} since {qend}: "
                                               f"check EDGAR and data/health edgar notes")
        else:
            rec.update(status="WAITING")
        # deck (never gates)
        if expect == "deck":
            route = spec.get("deck", "ir_page")
            if route == "edgar":
                ex = [d.get("url") for c in rel for d in c.get("docs") or [] if DECK_EX_RE.search(str((d or {}).get("url") or "").rsplit("/", 1)[-1])]
                rec["deck"] = ("on EDGAR: " + ex[0].rsplit("/", 1)[-1]) if ex else ("expected as an 8-K exhibit" if rel else "-")
            elif route == "ir_page":
                n = sum(1 for c in cands if c.get("source") == "ir_decks" and c.get("entity") == issuer)
                rec["deck"] = f"{n} new IR deck link(s)" if n else "no new IR deck link"
            else:
                rec["deck"] = f"{route}: {spec.get('deck_url', '')}".strip() if rel else "-"
        rows.append(rec)

    n_read = sum(1 for r in rows if r["status"] == "READ")
    complete = unread == 0 and missing == 0 and all(r["status"] != "WAITING" for r in rows)
    ob = {"id": oid, "what": f"IR disclosure ledger {q}: every IR issuer's earnings release (or 10-Q) read "
                             f"(tracker/ir_ledger.py, sweep.md 3.6)",
          "source": "sweep.md 3.6 (2026-11-09)", "due_by": due.isoformat(),
          "status": "done" if complete else (item or {}).get("status", "open") if (item or {}).get("status") == "blocked" else "open",
          "read": read_map}
    if item:
        for k in ("evidence", "progress"):
            if item.get(k):
                ob[k] = item[k]
    out = {"quarter": q, "quarter_end": qend.isoformat(), "due_by": due.isoformat(), "today": today.isoformat(),
           "counts": {"issuers": len(rows), "read": n_read, "unread": unread, "missing": missing,
                      "waiting": sum(1 for r in rows if r["status"] == "WAITING")},
           "issuers": rows, "obligation": ob}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for r in rows:
        print(f"{r['issuer'][:14]:<14} {r['status']:<8} {r.get('id') or (r.get('via') or {}).get('acc', '') if isinstance(r.get('via'), dict) else r.get('id') or '':<26} "
              f"{(r.get('deck') or '')[:44]:<44} {r.get('next') or ''}")
    c = out["counts"]
    print(f"IR LEDGER {q} (due {due}): {c['issuers']} issuers, {c['read']} read, {c['unread']} to read, "
          f"{c['missing']} missing, {c['waiting']} waiting -> {a.out}")


if __name__ == "__main__":
    main()
