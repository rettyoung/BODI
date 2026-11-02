"""Deterministic triage and excerpting for the Sweep (sweep.md Steps 3.2-3.4, 8.7, 8.8). Added 2026-11-02.

Why. The Sweep used to read every candidate line and every chosen document into its own (Opus) context:
hundreds of candidate lines, then up to 25 documents x 40,000 characters. Everything that can be decided
mechanically - watched docket, party hit, instrument words in the title, noise, duplicates, already-seen
ids - is decided here, in Python, for free. The model sees one short table and, per document, an excerpt
of at most ~8,000 characters (cover page plus the passages around beat keywords, parties, MW/GW/$ figures
and ordering language). The full text stays on disk; a subagent opens it only when the excerpt says the
document matters (e.g. a table of contents pointing at terms the excerpt cut).

Nothing here classifies or writes rows. The score only orders and filters; the Sweep's judgment still
decides what becomes a row, and it can pull any item back from the "dropped" list in the JSON output.

usage
  python tracker/shortlist.py candidates --since 2026-10-26 [--state store_live/state.json]
        [--seen store_live/seen_index.json] [--top 40] [--out work/shortlist.json] [--excerpts work/excerpts]
      Every data/candidates/<date>.jsonl dated after --since. Prints one line per kept item (at most --top,
      highest priority first) plus one summary line; the JSON holds kept, backlog (kept beyond --top, for
      state.read_backlog) and dropped (with reasons).
  python tracker/shortlist.py backfill [--state store_live/state.json] [--n 25] [--out work/backfill.json]
        [--excerpts work/excerpts]
      Next C-07 batch from data/backfill/enriched.jsonl: refetched lines first, tier 1-2 newest first, then
      tier 3-4 that pass the screen. Tier 3-4 items with no beat signal in title, keywords, parties or
      text are SCREENED OUT (listed in the JSON; the Sweep records them in backfill_cursor.done with
      reason "screened"). Screened items never count toward the 25-item quota.
  python tracker/shortlist.py c08 [--state store_live/state.json] [--n 20] [--out work/c08.json]
      Next C-08 batch (new-source history lines in data/backfill/<date>.jsonl), in the corrections-queue order:
      legistar, state bills that passed a chamber or became law, appellate decisions, Regulations.gov
      watched-party comments, then the rest. Title-only screen; no excerpts (most are metadata-only).
  python tracker/shortlist.py excerpt FILING.json [--cap 8000]
      Print the excerpt for one filing file (what the extraction subagent receives).
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INSTRUMENT_RE = re.compile(r"\b(order|tariff|settlement|stipulation|brief|testimony|compliance|application|"
                           r"petition|contract|agreement|hearing|decision|ruling|rule|directive|executive order|"
                           r"approv\w*|certificate|cpcn|esa|rfp|irp|report|opinion|judgment|response|reply|comments|exhibit)\b", re.I)
ORDER_RE = re.compile(r"\b(final order|order (no\.?|granting|approving|denying|on|establishing|accepting)|"
                      r"decision|ruling|opinion|judgment|directive|executive order)\b", re.I)
TERMS_RE = re.compile(r"\b(tariff|rate schedule|rider|settlement|stipulation|special contract|esa|"
                      r"electric service agreement|minimum bill|collateral)\b", re.I)
NOISE_RE = re.compile(r"\b(notice of appearance|certificate of service|service list|withdrawal of counsel|"
                      r"motor carrier|telecommunications?|telephone|water (and|&) sewer|water utility|"
                      r"gas pipeline safety|pro hac vice|substitution of counsel|errata sheet|"
                      r"request for extension of time to file comments)\b", re.I)
INDIVIDUAL_RE = re.compile(r"^(comment|letter|e-?mail) (of|from) [A-Z][a-z]+ [A-Z][a-z]+\b", re.I)
FIGURE_RE = re.compile(r"(\$\s?\d[\d,.]*\s*(million|billion|bn|m|k)?|\b\d[\d,.]*\s?(MW|GW|kW|MWh|GWh|MVA)\b|"
                       r"\b\d{1,3}(\.\d+)?\s?%|\b\d{1,2}[- ]year\b)", re.I)
ORDERING_RE = re.compile(r"\b(it is (therefore )?ordered|ordered that|shall (be|take) effect|effective (date|on)|"
                         r"minimum (bill|demand|take)|exit fee|termination|notice period|load factor|ramp)\b", re.I)
EXEC_SOURCES = ("page:gov_", "page:ferc", "page:nerc", "page:doe", "page:ercot", "page:miso", "page:spp",
                "page:pjm", "page:caiso", "page:nyiso", "page:isone", "ercot_large_load", "federal_register")
# Keywords too common to carry a candidate on their own (each still counts a little). "ESA" also matches the
# Endangered Species Act; "emergency" every governor's disaster declaration.
WEAK = {"emergency", "interconnection", "queue", "esa", "nuclear", "collateral", "irp", "integrated resource plan",
        "rfp", "battery storage", "combined cycle", "gas turbine", "curtailment", "demand response", "crypto",
        "uprate", "smr", "transmission service", "network upgrade", "cpcn", "certificate of public convenience",
        "load forecast", "cost allocation"}
_BODY_CACHE = {}
# Sources whose items are on-beat by construction (the adapter already filtered them to large-load material).
ALWAYS = ("ercot_large_load", "queues", "ferc_eqr", "nyiso_icap", "ir_decks", "manual")


def body_terms(c, kw_re, limit=60000):
    """Distinct beat keywords in the first `limit` characters of the candidate's documents."""
    key = c.get("filing")
    if key not in _BODY_CACHE:
        f = load_filing(key)
        text = " ".join((d.get("text") or "")[:limit] for d in (f or {}).get("documents") or [])
        _BODY_CACHE[key] = {m.group(1).lower() for m in kw_re.finditer(text)}
    return _BODY_CACHE[key]


TIER_ORDER = {"order": 0, "party": 1, "terms": 2, "deck": 3, "rest": 4}


def load_watch():
    try:
        import yaml
        w = yaml.safe_load(open(os.path.join(ROOT, "config", "watchlist.yaml"), encoding="utf-8"))
    except Exception as e:  # noqa
        print(f"cannot read config/watchlist.yaml: {e}", file=sys.stderr)
        sys.exit(2)
    kws = [k for k in (w.get("keywords") or []) if isinstance(k, str)]
    parties = [p if isinstance(p, str) else (p or {}).get("name", "") for p in (w.get("parties") or [])]
    dockets = set()
    for v in (w.get("dockets") or {}).values():
        for d in v or []:
            dockets.add(str(d if not isinstance(d, dict) else d.get("id", "")).upper())
    return kws, [p for p in parties if p], dockets


def word_re(terms):
    terms = sorted({t for t in terms if t}, key=len, reverse=True)
    if not terms:
        return re.compile(r"(?!x)x")
    return re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(t) for t in terms) + r")(?![A-Za-z0-9])", re.I)


def as_list(v):
    """Backfill lines written on 3-4 Oct carry lists as their repr strings."""
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.startswith("["):
        try:
            import ast
            return ast.literal_eval(v)
        except Exception:  # noqa
            return []
    return []


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
        elif isinstance(x, str) and len(x) > 6:
            out.add(x)
    try:
        walk(json.load(open(path, encoding="utf-8")))
    except Exception as e:  # noqa
        print(f"warning: seen index unreadable ({e}); seen check skipped", file=sys.stderr)
    return out


def load_filing(rel):
    p = os.path.join(ROOT, rel) if rel and not os.path.isabs(rel) else rel
    if not p or not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:  # noqa
        return None


def norm_hash(text):
    t = re.sub(r"\s+", " ", (text or "")).strip().lower()
    return hashlib.sha256(t.encode("utf-8", "replace")).hexdigest()[:16] if len(t) >= 400 else None


def older_text_hashes(before_date, exclude_ids):
    """{text hash: filing id} for every filing collected before `before_date` (data/filings, all states)."""
    idx = {}
    for p in glob.glob(os.path.join(ROOT, "data", "filings", "*", "*", "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:  # noqa
            continue
        if d.get("id") in exclude_ids or (d.get("collected_at") or "9999")[:10] > before_date:
            continue
        for doc in d.get("documents") or []:
            h = norm_hash(doc.get("text"))
            if h:
                idx.setdefault(h, d.get("id"))
    return idx


def excerpt(filing, kw_re, party_re, cap=8000, cover=1500, win=700):
    """Cover page + merged windows around beat signals, per document, until `cap` characters."""
    out, used = [], 0
    for i, doc in enumerate(filing.get("documents") or []):
        text = doc.get("text") or ""
        head = (f"=== doc {i}: {doc.get('name') or doc.get('url')} | quality={doc.get('quality')} "
                f"ocr={doc.get('ocr')} chars={len(text)} | full text: {filing.get('_path', '')} documents[{i}].text")
        if not text.strip():
            out.append(head + "\n[no text]")
            continue
        spans = [(0, min(cover, len(text)))]
        for rx in (kw_re, party_re, FIGURE_RE, ORDERING_RE):
            for m in rx.finditer(text):
                spans.append((max(0, m.start() - win), min(len(text), m.end() + win)))
        spans.sort()
        merged = []
        for s, e in spans:
            if merged and s <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        body, last = [], 0
        budget = cap - used - len(head)
        for s, e in merged:
            if budget <= 200:
                body.append(f"[... excerpt cap reached; {len(text) - last:,} more characters in the full text]")
                break
            if s > last:
                body.append(f"[... {s - last:,} chars ...]")
            chunk = text[s:e][:budget]
            body.append(chunk)
            budget -= len(chunk)
            last = s + len(chunk)
        else:
            if last < len(text):
                body.append(f"[... {len(text) - last:,} chars ...]")
        block = head + "\n" + "\n".join(body)
        out.append(block)
        used += len(block)
        if used >= cap:
            n_left = len(filing.get("documents") or []) - i - 1
            if n_left > 0:
                out.append(f"[{n_left} more document(s) not excerpted; see the full filing file]")
            break
    return "\n\n".join(out)


def score(c, kw_re, party_re, dockets, exec_ok=True):
    title = (c.get("title") or "").strip()
    src, kind = c.get("source") or "", c.get("kind") or ""
    kws = as_list(c.get("keywords"))
    parties = as_list(c.get("party_hits"))
    why, s = [], 0
    dk = str(c.get("docket") or "").upper()
    watched = bool(dk) and any(dk == w or dk.startswith(w + "-") or w in dk for w in dockets)
    if watched:
        s += 40
        why.append("watched docket")
    if parties:
        s += 30
        why.append("party " + "/".join(parties[:2]))
    if INSTRUMENT_RE.search(title):
        s += 15
        why.append("instrument in title")
    hits = {m.group(1).lower() for m in kw_re.finditer(title)} | {str(k).lower() for k in kws}
    strong = {h for h in hits if h not in WEAK}
    weak = hits - strong
    body = body_terms(c, kw_re) if c.get("filing") else set()
    body_strong = {h for h in body if h not in WEAK}
    if strong:
        s += min(50, 25 * len(strong))
        why.append("kw " + ",".join(sorted(strong)[:3]))
    elif weak:
        s += min(10, 5 * len(weak))
        why.append("weak kw " + ",".join(sorted(weak)[:3]))
    if len(body_strong - strong) >= 2:
        s += 15
        why.append("text " + ",".join(sorted(body_strong - strong)[:3]))
    beat = bool(strong or len(body_strong) >= 2 or parties)
    if src.startswith(ALWAYS):
        s += 45
        why.append("always-read source")
    if src == "edgar" or kind == "deck" or src == "ir_decks":
        s += 45
        why.append("tracked-issuer disclosure")
    elif src.startswith("edgar"):
        s += 20
        why.append("EDGAR full-text hit")
    if (c.get("meta") or {}).get("new_docket") and strong:
        s += 15
        why.append("new docket")
    if exec_ok and src.startswith(EXEC_SOURCES) and beat:
        s += 15
        why.append("exec/RTO/agency page")
    if kind in ("court", "legislation", "agenda", "queue_delta", "order", "minutes") and beat:
        s += 10
    noise = None
    if NOISE_RE.search(title):
        noise = "routine filing"
    elif INDIVIDUAL_RE.search(title) or str(c.get("entity") or "").lower().startswith(("individual", "['individual")):
        noise = "individual comment"
    if noise and not parties:
        s -= 60
        why.append(noise)
    if ORDER_RE.search(title) and (watched or beat):
        group = "order"
    elif parties:
        group = "party"
    elif TERMS_RE.search(title):
        group = "terms"
    elif kind in ("deck", "disclosure") or src.startswith("edgar"):
        group = "deck"
    else:
        group = "rest"
    return s, group, why


def doc_summary(c):
    docs = c.get("docs") if isinstance(c.get("docs"), list) else []
    if not docs:
        return "no docs"
    q = {}
    for d in docs:
        q[d.get("quality") or "?"] = q.get(d.get("quality") or "?", 0) + 1
    chars = sum(d.get("chars") or 0 for d in docs)
    return f"{len(docs)}d {chars // 1000}k " + "/".join(f"{k}{v}" for k, v in q.items())


def safe(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:120]


def write_excerpt(c, kw_re, party_re, xdir, cap):
    f = load_filing(c.get("filing"))
    if not f:
        return None, 0
    f["_path"] = c.get("filing")
    text = excerpt(f, kw_re, party_re, cap=cap)
    os.makedirs(xdir, exist_ok=True)
    p = os.path.join(xdir, safe(c["id"]) + ".txt")
    open(p, "w", encoding="utf-8").write(text)
    return p, sum(len(d.get("text") or "") for d in f.get("documents") or [])


def text_hashes(c):
    f = load_filing(c.get("filing"))
    return [h for h in (norm_hash(d.get("text")) for d in (f or {}).get("documents") or []) if h]


def cmd_candidates(a):
    kws, parties, dockets = load_watch()
    kw_re, party_re = word_re(kws), word_re(parties)
    seen = seen_strings(a.seen)
    files = sorted(p for p in glob.glob(os.path.join(ROOT, "data", "candidates", "*.jsonl"))
                   if os.path.basename(p)[:10] > a.since)
    items, ids = [], set()
    for p in files:
        for line in open(p, encoding="utf-8"):
            try:
                c = json.loads(line)
            except Exception:  # noqa
                continue
            if c.get("id") in ids:
                continue
            ids.add(c.get("id"))
            c["_file"] = os.path.basename(p)
            items.append(c)
    # state.read_backlog: kept items earlier runs could not read (ids, or dicts with "id"); pull their lines back in
    backlog_ids = set()
    if a.state and os.path.exists(a.state):
        try:
            rb = json.load(open(a.state, encoding="utf-8")).get("read_backlog") or []
            backlog_ids = {x if isinstance(x, str) else (x or {}).get("id") for x in rb} - {None} - ids
        except Exception as e:  # noqa
            print(f"warning: state unreadable ({e}); read_backlog not merged", file=sys.stderr)
    if backlog_ids:
        for p in sorted(glob.glob(os.path.join(ROOT, "data", "candidates", "*.jsonl"))):
            if os.path.basename(p)[:10] > a.since:
                continue
            for line in open(p, encoding="utf-8"):
                if not any(b in line for b in backlog_ids):
                    continue
                c = json.loads(line)
                if c.get("id") in backlog_ids and c["id"] not in ids:
                    ids.add(c["id"])
                    c["_file"], c["_backlog"] = os.path.basename(p), True
                    items.append(c)
    hidx = older_text_hashes(a.since, ids) if items else {}
    kept, dropped = [], []
    window_hashes = {}
    for c in items:
        if (c.get("id") in seen and not c.get("_backlog")) or (c.get("url") and c["url"] in seen and "filelist" not in c["url"]):
            dropped.append({"id": c["id"], "title": (c.get("title") or "")[:100], "why": "already in seen_index"})
            continue
        hs = text_hashes(c)
        dup = next((hidx[h] for h in hs if h in hidx), None) or next((window_hashes[h] for h in hs if h in window_hashes), None)
        if hs and dup and all((h in hidx or h in window_hashes) for h in hs):
            dropped.append({"id": c["id"], "title": (c.get("title") or "")[:100], "why": f"same text as {dup}"})
            continue
        for h in hs:
            window_hashes.setdefault(h, c["id"])
        s, group, why = score(c, kw_re, party_re, dockets)
        if c.get("_backlog"):
            s, why = s + 10, why + ["from read_backlog"]
        rec = {"id": c["id"], "jur": c.get("jur"), "source": c.get("source"), "kind": c.get("kind"),
               "docket": c.get("docket"), "title": re.sub(r"\s+", " ", c.get("title") or "")[:160],
               "filed": c.get("filed"), "url": c.get("url"), "filing": c.get("filing"), "score": s,
               "group": group, "why": why, "docs": doc_summary(c),
               "not_document": any((d or {}).get("quality") == "not_document" for d in (c.get("docs") or []) if isinstance(d, dict))}
        (kept if s >= a.min_score else dropped).append(rec if s >= a.min_score else
                                                       {"id": c["id"], "title": rec["title"][:100], "why": f"score {s}: " + "; ".join(why or ["no beat signal"])})
    kept.sort(key=lambda r: (TIER_ORDER[r["group"]], -r["score"], r.get("filed") or ""), reverse=False)
    top, backlog = kept[:a.top], kept[a.top:]
    full_chars = ex_chars = 0
    for r in top:
        p, n = write_excerpt(r, kw_re, party_re, a.excerpts, a.cap)
        r["excerpt"] = p
        if p:
            full_chars += n
            ex_chars += os.path.getsize(p)
    out = {"since": a.since, "files": [os.path.basename(p) for p in files], "candidates": len(items),
           "kept": top, "backlog": backlog, "dropped": dropped,
           "chars": {"full_text": full_chars, "excerpts": ex_chars},
           "newest_file": os.path.basename(files[-1])[:10] if files else None}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for i, r in enumerate(top, 1):
        print(f"{i:>2} {r['score']:>3} {r['group']:<5} {r['id'][:34]:<34} {(r['docket'] or '-')[:16]:<16} "
              f"{r['docs']:<16} {r['title'][:70]}")
    print(f"SHORTLIST {len(items)} candidates in {len(files)} files -> {len(top)} to read, {len(backlog)} backlog, "
          f"{len(dropped)} dropped; excerpts {ex_chars:,} chars vs {full_chars:,} full text -> {a.out}")


def done_sets(state_path):
    if not state_path or not os.path.exists(state_path):
        return set(), set()
    try:
        st = json.load(open(state_path, encoding="utf-8"))
    except Exception as e:  # noqa
        print(f"cannot read state: {e}", file=sys.stderr)
        sys.exit(2)
    bc = st.get("backfill_cursor") or {}
    done = bc.get("done") or []
    done = set(done if isinstance(done, list) else list(done))
    ref = bc.get("refetched_done") or []
    return done, set(ref if isinstance(ref, list) else list(ref))


def cmd_backfill(a):
    kws, parties, dockets = load_watch()
    kw_re, party_re = word_re(kws), word_re(parties)
    done, ref_done = done_sets(a.state)
    lines = {}
    for line in open(os.path.join(ROOT, "data", "backfill", "enriched.jsonl"), encoding="utf-8"):
        try:
            c = json.loads(line)
        except Exception:  # noqa
            continue
        if c.get("refetched"):
            if c["id"] in ref_done:
                continue
            c["_refetch"] = True
        elif c["id"] in done:
            continue
        prev = lines.get(c["id"])
        if prev is None or c.get("_refetch"):
            lines[c["id"]] = c
    take, screened = [], []
    for c in lines.values():
        tier = c.get("tier") or 4
        kwl, pl = as_list(c.get("keywords")), as_list(c.get("party_hits"))
        if c.get("_refetch") or tier <= 2:
            take.append(c)
            continue
        signal = bool(pl)
        if kwl and not signal:
            f = load_filing(c.get("filing"))
            text = " ".join((d.get("text") or "")[:20000] for d in (f or {}).get("documents") or [])
            strong = {m.group(1).lower() for m in kw_re.finditer(c.get("title") or "")}
            body = {m.group(1).lower() for m in kw_re.finditer(text)}
            signal = bool(strong) or len(body) >= 2 or bool(party_re.search(text))
        if signal:
            take.append(c)
        else:
            screened.append({"id": c["id"], "tier": tier, "title": (c.get("title") or "")[:100],
                             "why": "no keyword or party" if not kwl else "keywords only in metadata, <2 beat terms in text"})
    # corrections_queue C-07 order: refetched first, then tier 1-2, then passing tier 3-4; newest first within each
    take.sort(key=lambda c: c.get("filed") or "", reverse=True)
    take.sort(key=lambda c: (0 if c.get("_refetch") else 1, 0 if (c.get("tier") or 4) <= 2 else 1))
    batch = take[:a.n]
    out_batch = []
    for c in batch:
        p, n = write_excerpt(c, kw_re, party_re, a.excerpts, a.cap)
        out_batch.append({"id": c["id"], "tier": c.get("tier"), "refetched": bool(c.get("_refetch")),
                          "jur": c.get("jur"), "docket": c.get("docket"), "title": re.sub(r"\s+", " ", c.get("title") or "")[:160],
                          "filed": c.get("filed"), "url": c.get("url"), "filing": c.get("filing"), "excerpt": p})
    out = {"batch": out_batch, "screened_out": screened, "remaining_after_batch": len(take) - len(batch),
           "remaining_passing": len(take), "done_before": len(done)}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for i, r in enumerate(out_batch, 1):
        print(f"{i:>2} t{r['tier']}{'R' if r['refetched'] else ' '} {r['id'][:34]:<34} {(r['docket'] or '-')[:16]:<16} {r['title'][:70]}")
    print(f"C-07 BATCH {len(out_batch)} (quota {a.n}); {len(take) - len(batch)} passing items remain after it; "
          f"{len(screened)} screened out (record in backfill_cursor.done as screened) -> {a.out}")


C08_SOURCES = ("openstates", "courtlistener", "congress", "regulations_gov", "legistar", "ercot_large_load", "studies", "osti")
PASSED_RE = re.compile(r"\b(signed|enacted|chaptered|became law|approved by (the )?governor|passed (the )?(house|senate|assembly)|"
                       r"act no\.|effective)\b", re.I)


def cmd_c08(a):
    kws, parties, dockets = load_watch()
    kw_re, party_re = word_re(kws), word_re(parties)
    done, _ = done_sets(a.state)
    items, seen_ids = [], set()
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "backfill", "20*.jsonl"))):
        for line in open(p, encoding="utf-8"):
            try:
                c = json.loads(line)
            except Exception:  # noqa
                continue
            src = c.get("source") or ""
            if not str(c.get("run_id") or "").startswith("2026-10-0") or not src.startswith(C08_SOURCES):
                continue
            if c["id"] in done or c["id"] in seen_ids:
                continue
            seen_ids.add(c["id"])
            items.append(c)
    take, screened = [], []
    for c in items:
        src, title = c.get("source") or "", c.get("title") or ""
        meta = c.get("meta") if isinstance(c.get("meta"), dict) else {}
        latest = str(meta.get("latest_action") or meta.get("latest_action_description") or "")
        signal = bool(kw_re.search(title) or party_re.search(title) or as_list(c.get("party_hits")))
        if src.startswith("ercot_large_load") or src.startswith(("studies", "osti")):
            signal = True
        if src.startswith("openstates"):
            rank = 1 if PASSED_RE.search(latest + " " + title) else 5
        elif src.startswith("legistar"):
            rank = 0
        elif src.startswith("courtlistener"):
            rank = 2
        elif src.startswith("regulations_gov"):
            rank = 3 if as_list(c.get("party_hits")) else 6
        else:
            rank = 4
        if not signal:
            screened.append({"id": c["id"], "source": src, "title": title[:100], "why": "title has no beat term or party"})
            continue
        take.append((rank, c))
    take.sort(key=lambda x: (x[0], x[1].get("filed") or ""))
    batch = [c for _, c in take[:a.n]]
    out = {"batch": [{"id": c["id"], "source": c.get("source"), "jur": c.get("jur"), "title": re.sub(r"\s+", " ", c.get("title") or "")[:160],
                      "filed": c.get("filed"), "url": c.get("url"), "filing": c.get("filing"),
                      "meta": {k: v for k, v in (c.get("meta") if isinstance(c.get("meta"), dict) else {}).items()
                               if k in ("latest_action", "latest_action_description", "table_metrics", "court", "status")}}
                     for c in batch],
           "screened_out": screened, "remaining_after_batch": len(take) - len(batch), "unprocessed_total": len(items)}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for i, c in enumerate(batch, 1):
        print(f"{i:>2} {(c.get('source') or '')[:14]:<14} {c['id'][:34]:<34} {re.sub(chr(10), ' ', c.get('title') or '')[:70]}")
    print(f"C-08 BATCH {len(batch)} (quota {a.n}); {len(take) - len(batch)} passing remain; {len(screened)} screened out "
          f"(triage done for all {len(items)} unprocessed lines) -> {a.out}")


def cmd_excerpt(a):
    kws, parties, _ = load_watch()
    f = load_filing(a.filing)
    if not f:
        print("cannot read filing", file=sys.stderr)
        sys.exit(2)
    f["_path"] = a.filing
    print(excerpt(f, word_re(kws), word_re(parties), cap=a.cap))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("candidates")
    p.add_argument("--since", required=True, help="collector_from: read candidate files dated after this")
    p.add_argument("--state")
    p.add_argument("--seen")
    p.add_argument("--top", type=int, default=40)
    p.add_argument("--min-score", type=int, default=45)
    p.add_argument("--cap", type=int, default=8000)
    p.add_argument("--out", default="work/shortlist.json")
    p.add_argument("--excerpts", default="work/excerpts")
    p.set_defaults(fn=cmd_candidates)
    p = sp.add_parser("backfill")
    p.add_argument("--state")
    p.add_argument("--n", type=int, default=25)
    p.add_argument("--cap", type=int, default=8000)
    p.add_argument("--out", default="work/backfill.json")
    p.add_argument("--excerpts", default="work/excerpts")
    p.set_defaults(fn=cmd_backfill)
    p = sp.add_parser("c08")
    p.add_argument("--state")
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--out", default="work/c08.json")
    p.set_defaults(fn=cmd_c08)
    p = sp.add_parser("excerpt")
    p.add_argument("filing")
    p.add_argument("--cap", type=int, default=8000)
    p.set_defaults(fn=cmd_excerpt)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
