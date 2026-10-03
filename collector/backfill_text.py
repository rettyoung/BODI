"""Backfill enrichment: download and extract the documents behind the one-off docket-history backfill.

The backfill run (data/backfill/<date>.jsonl) listed every filing in the watched dockets since 2025-11-07, but its
document budget ran out after FERC and Louisiana, so most items are metadata only. A party's brief is often
filed under its attorney's name (the Aug 2026 Microsoft closing brief in the APS case reads "Albert H. Acken,
Atty."), so metadata alone cannot find what matters. Each nightly run spends its spare time here: it ranks the
substantive filings, fetches their documents, matches watched parties on the cover page, and appends the result
to data/backfill/enriched.jsonl, which the Sweep reads in tier order (corrections queue C-07).

Tiers: 1 = issued by the commission/agency (orders, decisions, staff recommendations, notices of hearing);
2 = filed by a watched party; 3 = briefs, testimony, applications, tariffs, settlements; 4 = other comments/reports.
"""
import glob, json, os, re, time

from common import DATA, ROOT, save_json, load_json, now_utc

SUBSTANTIVE = re.compile(r"brief|testimony|application|order|decision|ruling|tariff|rate schedule|settlement|stipulation|"
                         r"comments|petition|complaint|protest|exceptions|recommend|proposal for (decision|adoption)|"
                         r"agreement|contract|compliance|report|memo|notice of hearing|rule", re.I)
NOISE = re.compile(r"intervene|intervention|appearance|service list|certificate of service|errata|consumer comment|"
                   r"public comment|transcript|substitution of counsel|withdraw|pro hac|notice of filing|cover letter|"
                   r"affidavit of publication|proof of publication|request for inclusion|telecom|telephone|natural gas|"
                   r"water company|water service|sewer|motor carrier", re.I)
ISSUED = re.compile(r"\border\b|decision|ruling|proposal for decision|recommended (opinion|order|adoption)|"
                    r"staff (memo|recommendation)|notice of (hearing|proposed)|final rule|\bPUC RULES|ALJ|hearing examiner", re.I)
FILED_BRIEF = re.compile(r"brief|testimony|application|petition|tariff|rate schedule|settlement|stipulation|exceptions|"
                         r"complaint|protest", re.I)
OUT = os.path.join(DATA, "backfill", "enriched.jsonl")


def _hits(text, terms):
    t = (text or "").lower()
    return sorted({p for p in terms if p.lower() in t})


RESPONSIVE = re.compile(r"comments? (on|to|of)|repl(y|ies) to|exceptions to|response to|responses to|motion|"
                        r"request for|in support of|objection", re.I)
TX_ISSUER = re.compile(r"^(PUC|PUBLIC UTILITY COMMISSION|COMMISSION|SOAH|STATE OFFICE OF ADMIN)", re.I)
TX_LOW = {"LTRS", "PC", "PL"}   # public letters, public comments, pleadings by individuals: tier 4 unless a party


def tier(item, parties):
    title = item.get("title") or ""
    who = f"{title} {item.get('entity') or ''}"
    parts = [p.strip() for p in title.split("|")]
    if item.get("source") == "tx_puct" and len(parts) >= 4:      # "date | filer | type | description"
        filer, typ, desc = parts[1], parts[2].upper(), " ".join(parts[3:])
        if TX_ISSUER.search(filer):
            return 1
        if _hits(filer, parties):
            return 2
        if typ in TX_LOW:
            return 4
        return 3 if FILED_BRIEF.search(desc) else 4
    if ISSUED.search(title) and not RESPONSIVE.search(title):
        return 1
    if _hits(who, parties):
        return 2
    if FILED_BRIEF.search(title):
        return 3
    return 4


def _has_text(it):
    try:
        f = json.load(open(os.path.join(ROOT, it["filing"])))
    except Exception:
        return True   # no filing file: nothing to enrich
    return not f.get("fetch") or any(d.get("text") for d in f.get("documents") or [])


def shortlist(parties, done):
    out = []
    # tier 0: this window's collector candidates whose documents did not extract (they feed the next Sweep)
    for f in sorted(glob.glob(os.path.join(DATA, "candidates", "*.jsonl")))[-21:]:
        for line in open(f):
            it = json.loads(line)
            if it.get("filing") and it["id"] not in done and it.get("source") not in ("watch_pages", "rss", "mirrors") \
                    and not _has_text(it):
                it["_candidate"] = True
                out.append((0, it.get("filed") or "", it))
    files = sorted(f for f in glob.glob(os.path.join(DATA, "backfill", "*.jsonl"))
                   if re.search(r"/\d{4}-\d{2}-\d{2}\.jsonl$", f))
    for f in files:
        for line in open(f):
            it = json.loads(line)
            title = it.get("title") or ""
            if it["id"] in done or not SUBSTANTIVE.search(title) or NOISE.search(title):
                continue
            out.append((tier(it, parties), it.get("filed") or "", it))
    out.sort(key=lambda t: t[1], reverse=True)   # newest first...
    out.sort(key=lambda t: t[0])                 # ...within each tier (stable sort)
    return out


def enrich(http, cfg, state, fetch_docs, keyword_hit, ctx_factory, seconds, max_docs):
    """Spend up to `seconds` and `max_docs` documents enriching backfill items. Returns a health record."""
    t0 = time.time()
    st = state.setdefault("backfill_text", {"done": []})
    done = set(st["done"])
    attempts = st.setdefault("attempts", {})
    tried_tonight = set()
    parties, kws = cfg.get("parties", []), cfg.get("keywords", [])
    queue = shortlist(parties, done)
    rec = {"queue": len(queue), "enriched": 0, "docs": 0, "errors": 0, "status": "ok"}
    if not queue:
        rec["status"] = "complete"
        return rec
    ctx = ctx_factory()
    try:
        for t, _, it in queue:
            if time.time() - t0 > seconds or rec["docs"] >= max_docs:
                break
            if it["id"] in tried_tonight:
                continue
            tried_tonight.add(it["id"])
            path = os.path.join(ROOT, it["filing"])
            filing = load_json(path, None)
            if not filing or not filing.get("fetch"):
                done.add(it["id"])
                continue
            docs = fetch_docs(http, filing, ctx)
            rec["docs"] += len(docs)
            rec["errors"] += sum(1 for d in docs if d.get("error"))
            if not any(d.get("text") for d in docs):
                # nothing extracted (fetch error, or no document link found): retry on later nights, give up after 3
                n = attempts.get(it["id"], 0) + 1
                attempts[it["id"]] = n
                if n < 3:
                    rec["retry_later"] = rec.get("retry_later", 0) + 1
                    continue
                rec["gave_up"] = rec.get("gave_up", 0) + 1
            cover = " ".join((d.get("text") or "")[:3000] for d in docs[:1])
            phits = _hits(f"{it.get('title') or ''} {it.get('entity') or ''} {cover}", parties)
            hits = keyword_hit(filing, docs, kws)
            filing.update(documents=docs, keywords=hits, party_hits=phits, enriched_at=now_utc())
            save_json(path, filing)
            if it.get("_candidate"):        # a current candidate: the Sweep reads its filing file directly
                done.add(it["id"])
                rec["candidates_filled"] = rec.get("candidates_filled", 0) + 1
                continue
            line = {k: it.get(k) for k in ("id", "jur", "source", "kind", "docket", "title", "filed", "url", "entity", "filing")}
            line.update(tier=t if not (t > 2 and phits) else 2, keywords=hits, party_hits=phits, enriched_at=now_utc(),
                        docs=[{"url": d.get("url"), "quality": d.get("quality"), "ocr": d.get("ocr"),
                               "chars": len(d.get("text") or ""), "error": d.get("error")} for d in docs])
            with open(OUT, "a") as f:
                f.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
            done.add(it["id"])
            rec["enriched"] += 1
    finally:
        ctx.close()
        st["done"] = sorted(done)
        st["attempts"] = {k: v for k, v in attempts.items() if k not in done}
    rec["remaining"] = max(0, len(queue) - rec["enriched"])
    rec["seconds"] = round(time.time() - t0, 1)
    return rec
