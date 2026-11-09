"""Everything the Brief's synthesis needs, in one small file (brief.md Steps 1-4). Added 2026-11-02.

Why. The Brief used to read the store, metrics, tariff terms, state and run records into its own context and
then hand much of it to the writing subagent. This script computes the parts that are mechanical -
which events are new since the last brief (after overlays and supersessions), what changed on older events,
the 30-day milestone list with URGENT and "outcome needed", the counts that must reconcile (events vs rows),
the Sweep's headline numbers - and writes them to one JSON file. The writing subagent reads only that file
(plus the brief rules); the Brief's own session reads only the printed summary line.

It is a read-only view of a store already loaded byte-exact into store_live/. It writes no store file.

usage
  python tracker/brief_input.py --store store_live --asof 2026-11-09 [--since 2026-11-02]
        [--run store_live/runs/<newest>.json] [--out work/brief_input.json]
    --since defaults to state.last_brief_date (or 2026-09-18). Prints one summary line, e.g.
    "BRIEF_INPUT 9 new events (14 rows; 4 high) · 3 changes on older events · 12 milestones (2 URGENT,
     1 outcome needed) · quiet=False -> work/brief_input.json".
  exit 0 always when the store loads; 2 when it cannot.
"""
import argparse
import glob
import json
import os
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rowstore  # noqa
import statefile  # noqa
import subtables  # noqa
from vocab import COLUMNS  # noqa

IX = {c: i for i, c in enumerate(COLUMNS)}
HIGH = "High / near-term"


def d(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except Exception:  # noqa
        return None


def event_date_from_id(eid):
    return f"{eid[2:6]}-{eid[6:8]}-{eid[8:10]}"


def compact(e, rows):
    """One event as the writer needs it: every field it may cite, no column noise."""
    return {"id": e["id"], "date": e["date"], "subject": e["subject"], "venue": e["venue"], "instrument": e["instrument"],
            "document": e["document"], "headline": e["headline"], "takeaway": e["takeaway"], "status": e["status"],
            "next": e["nm"], "next_date": e["nd"], "materiality": e["mat"], "confidence": e["conf"],
            "appeal": e["appeal"], "levers": e["levers"], "url": e["url"],
            "entities": [f"{u} ({j})" for u, j in e["ents"]], "rows": len(e["ents"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="store_live")
    ap.add_argument("--asof", required=True)
    ap.add_argument("--since")
    ap.add_argument("--run")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out", default="work/brief_input.json")
    a = ap.parse_args()
    try:
        _, rows = rowstore.load(a.store)
        state = statefile.load(a.store)
    except Exception as e:  # noqa
        print(f"cannot load the store in {a.store}: {e}", file=sys.stderr)
        sys.exit(2)
    asof = d(a.asof)
    since = a.since or state.get("last_brief_date") or "2026-09-18"
    since_c = since.replace("-", "")
    evs = rowstore.events(rows)
    live = [e for e in evs if e["sup"] != "Yes"]
    new = [e for e in live if e["id"][2:10] > since_c]
    new_sorted = sorted(new, key=lambda e: (e["mat"] != HIGH, e["subject"], e["date"]), reverse=False)

    # changes on older events since the last brief: overlays and supersessions written by parts after `since`
    changes = []
    try:
        import build_console
        _, ch, _ = build_console.history(a.store)
        for c in ch:
            if (c.get("date") or "") > since and c.get("event_id", "")[2:10] <= since_c:
                changes.append({k: c.get(k) for k in ("kind", "event_id", "new_event_id", "column", "before", "after", "reason")})
    except Exception as e:  # noqa
        changes = [{"error": f"history not computed: {e}"}]

    # milestones: open rows with Next Date within --days, plus state.near_term_milestones; dedupe; URGENT <= 7 days
    ms, seen = [], set()
    horizon = asof + timedelta(days=a.days)
    for e in live:
        nd = d(e["nd"])
        if not nd:
            continue
        if asof - timedelta(days=a.days) <= nd < asof and (e["status"] or "").lower() not in ("closed", "decided", "final"):
            kind = "outcome needed"
        elif asof <= nd <= horizon:
            kind = "URGENT" if (nd - asof).days <= 7 else ""
        else:
            continue
        key = (str(nd), (e["document"] or "")[:40].lower())
        if key in seen:
            continue
        seen.add(key)
        ms.append({"date": str(nd), "days": (nd - asof).days, "flag": kind, "what": e["nm"], "event": e["id"],
                   "document": e["document"], "entities": sorted({j for _, j in e["ents"]})})
    for m in state.get("near_term_milestones") or []:
        md = d(m.get("date") if isinstance(m, dict) else None)
        if not md or md > horizon or md < asof - timedelta(days=a.days):
            continue
        what = m.get("item") or m.get("what") or m.get("milestone") or ""
        key = (str(md), (m.get("docket") or what)[:40].lower())
        if key in seen:
            continue
        seen.add(key)
        past = md < asof
        if past and not m.get("outcome_needed") and "outcome needed" not in json.dumps(m).lower():
            continue
        ms.append({"date": str(md), "days": (md - asof).days,
                   "flag": "outcome needed" if past else ("URGENT" if (md - asof).days <= 7 else ""),
                   "what": what, "document": m.get("docket"), "note": m.get("note") or m.get("status"), "from": "state"})
    ms.sort(key=lambda m: (m["flag"] != "URGENT", m["flag"] != "outcome needed", m["date"]))

    run = None
    rp = a.run or (sorted(glob.glob(os.path.join(a.store, "runs", "*.json")))[-1:] or [None])[0]
    if rp and os.path.exists(rp):
        try:
            r = json.load(open(rp, encoding="utf-8"))
            run = {k: r.get(k) for k in ("run_id", "status", "mode", "events_found", "rows_written", "rows_superseded",
                                          "documents_read", "DEFERRED_NEEDS_MANUAL", "CANARY_MISS", "SUSPECT_ZERO",
                                          "ACCESS_REGRESSION", "CIRCUIT_OPEN", "read_backlog_size", "usage")}
            chk = r.get("check")
            # check should be check_run's JSON verdict or {"method": "hand", ...}; a run that wrote a sentence
            # (2026-11-02-1157) must not cost the writer the whole Sweep summary.
            run["check_ok"] = chk.get("ok") if isinstance(chk, dict) else None
            if isinstance(chk, dict) and chk.get("method"):
                run["check_method"] = chk.get("method")
            elif isinstance(chk, str):
                run["check_note"] = chk[:500]
        except Exception as e:  # noqa
            run = {"error": str(e)}

    try:
        tariffs = subtables.merge(a.store) if hasattr(subtables, "merge") else None
    except Exception:  # noqa
        tariffs = None
    metrics = None
    mp = os.path.join(a.store, "metrics.json")
    if os.path.exists(mp):
        metrics = json.load(open(mp, encoding="utf-8"))

    high = [e for e in new if e["mat"] == HIGH]
    out = {
        "asof": a.asof, "since": since,
        "counts": {"new_events": len(new), "new_rows": sum(len(e["ents"]) for e in new), "new_high": len(high),
                   "store_events": len({r[1] for r in rows}), "store_rows": len(rows),
                   "changes_on_older_events": len([c for c in changes if "error" not in c])},
        "quiet": not new and not [c for c in changes if "error" not in c],
        "new_events": [compact(e, rows) for e in new_sorted],
        "changes": changes,
        "milestones": ms,
        "standing_facts": state.get("standing_facts_for_the_brief"),
        "pipeline_baselines": state.get("pipeline_baselines_for_delta"),
        "remaining_gaps": state.get("REMAINING_GAPS"),
        "explicit_negatives": state.get("EXPLICIT_NEGATIVES"),
        "metrics": metrics,
        "tariff_terms": tariffs,
        "sweep": run,
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    urgent = sum(1 for m in ms if m["flag"] == "URGENT")
    need = sum(1 for m in ms if m["flag"] == "outcome needed")
    print(f"BRIEF_INPUT {len(new)} new events ({out['counts']['new_rows']} rows; {len(high)} high) · "
          f"{out['counts']['changes_on_older_events']} changes on older events · {len(ms)} milestones "
          f"({urgent} URGENT, {need} outcome needed) · quiet={out['quiet']} · {os.path.getsize(a.out):,} bytes -> {a.out}")


if __name__ == "__main__":
    main()
