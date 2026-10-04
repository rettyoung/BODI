"""Assemble the publishable console package from the row store.

usage: python build_console.py OUTDIR --asof YYYY-MM-DD [--status status.json] [--narrative brief.md]
                               [--deliverables DIR] [--state state.json] [--manual-dir DIR] [--since YYYY-MM-DD]

OUTDIR receives what the Artifact tool can serve: index.html (with the in-browser
workbook builder inlined), data.json (events for the views + the full 26-column
row table the workbook is built from), metrics.json, tariff_terms.json,
status.json and, with --narrative, narrative.md and the narrative PDF.

The Excel tracker itself cannot be served as an artifact file, so the page builds
it in the browser (console/tracker_xlsx.js) from the same rows. The canonical
Python-built workbook (and the narrative .docx) go to --deliverables, which the
Brief commits to the repo each week. CI (xlsx-parity) checks the two builds agree.

data.json also carries what the console's change, coverage and party views need:
  parts / changes  the store's history replayed part by part: which part added each event, and every
                   overlay and supersession with its value before and after (read from the parts, never
                   inferred);
  since            the previous brief's date (state.last_brief_date unless --since is given), the default
                   "changed since" point;
  coverage         per jurisdiction: route, last successful read (collector state, the Sweep's date for
                   WebFetch routes, complete manual-pass manifests for manual routes), explicit negatives
                   and open gaps from state.json, plus the last nights of collector health;
  annotations      console/annotations.json (coverage marks, matter labels, party groups);
  parties          the party watch list from config/watchlist.yaml.
Every addition is optional for the page: a build without them (the Brief's repo-less path) still renders.
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import rowstore  # noqa
import build_tracker  # noqa
import narrative as narr  # noqa

XLSX = "Grid_Docket_Tracker_MASTER.xlsx"


def page(out):
    src = open(os.path.join(ROOT, "console", "index.html"), encoding="utf-8").read()
    js = open(os.path.join(ROOT, "console", "tracker_xlsx.js"), encoding="utf-8").read()
    assert "/*@@TRACKER_XLSX@@*/" in src
    src = src.replace("/*@@TRACKER_XLSX@@*/", js.replace("</script", "<\\/script"))
    open(out, "w", encoding="utf-8").write(src)


def history(store):
    """Replay the store part by part: where each event first appeared, and every overlay and
    supersession with the value it replaced. Uses rowstore.apply_overlays, so it matches load()."""
    from vocab import COLUMNS
    ix = {c: i for i, c in enumerate(COLUMNS)}
    man = json.load(open(os.path.join(store, "rows.json")))
    rows, parts, changes, first = [], [], [], {}
    for n, p in enumerate(man["parts"]):
        d = json.load(open(os.path.join(store, p["file"])))
        new = []
        for r in d["data"]:
            if r[1] not in first:
                first[r[1]] = n
                new.append(r[1])
        disc = sorted({e[2:10] for e in new})
        date = (d.get("written") or "")[:10] or (f"{disc[-1][:4]}-{disc[-1][4:6]}-{disc[-1][6:]}" if disc else None)
        rows.extend([list(r) for r in d["data"]])
        for s_ in d.get("supersedes") or []:
            changes.append({"part": n, "date": date, "kind": "supersede", "event_id": s_.get("old_event_id"),
                            "new_event_id": s_.get("new_event_id"), "column": "Superseded",
                            "before": next((r[ix["Superseded"]] for r in rows if r[1] == s_.get("old_event_id")), None),
                            "after": "Yes", "reason": s_.get("reason") or ""})
        for o in d.get("overlays") or []:
            col = o.get("column")
            before = next((r[ix[col]] for r in rows if r[1] == o.get("event_id")), None) if col in ix else None
            changes.append({"part": n, "date": date, "kind": "overlay", "event_id": o.get("event_id"), "column": col,
                            "before": before if before is not None else "", "after": o.get("value") or "",
                            "reason": o.get("reason") or ""})
        rowstore.apply_overlays(rows, d)
        parts.append({"file": p["file"], "date": date, "run_id": d.get("run_id") or p.get("run_id"),
                      "rows": len(d["data"]), "events": len(new),
                      "overlays": len(d.get("overlays") or []), "supersedes": len(d.get("supersedes") or [])})
    return parts, changes, first


STATE_NAMES = {"ALABAMA": "AL", "ARIZONA": "AZ", "GEORGIA": "GA", "ILLINOIS": "IL", "KANSAS": "KS",
               "LOUISIANA": "LA", "MISSOURI": "MO", "NORTH CAROLINA": "NC", "NEW MEXICO": "NM", "NEVADA": "NV",
               "OHIO": "OH", "OKLAHOMA": "OK", "PENNSYLVANIA": "PA", "SOUTH CAROLINA": "SC", "TEXAS": "TX",
               "VIRGINIA": "VA", "WEST VIRGINIA": "WV", "FERC": "FERC", "GRDA": "OK", "ERCOT": "TX", "PUCT": "TX"}


def _jur_of(text):
    """Jurisdiction named at the start of a state.json note ("OHIO — ...", "Arizona TEP", "FERC EL26-68 ...")."""
    t = text.upper()
    for name in sorted(STATE_NAMES, key=len, reverse=True):     # WEST VIRGINIA before VIRGINIA
        if re.match(rf"^{name}\b", t):
            return STATE_NAMES[name]
    return None


def coverage(state, manual_dir, asof):
    wl = yaml.safe_load(open(os.path.join(ROOT, "config", "watchlist.yaml")))
    cs_path = os.path.join(ROOT, "data", "state", "collector_state.json")
    cs = json.load(open(cs_path)) if os.path.exists(cs_path) else {}
    src = cs.get("sources") or {}
    nights = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "health", "2*.json")))[-10:]:
        h = json.load(open(f))
        s = h.get("sources") or {}
        bad = sorted(k for k, v in s.items() if (v or {}).get("status") not in ("ok", "refused_known", "skipped", None))
        nights.append({"date": os.path.basename(f)[:10], "run_id": h.get("run_id"), "sources": len(s),
                       "failing": bad, "gap": bool(h.get("collector_gap")), "complete": bool(h.get("finished"))})
    manual = {}
    for f in sorted(glob.glob(os.path.join(manual_dir, "manual_*.json"))) if manual_dir else []:
        m = json.load(open(f))
        if not m.get("complete") or not re.match(r"^manual_[^_]+\.json$", os.path.basename(f)):
            continue
        day = str(m.get("run_id", ""))[:10]
        for st_, res in (m.get("states") or {}).items():
            cur = manual.setdefault(st_, {"last_ok": None, "last_try": None, "last_result": None})
            if not cur["last_try"] or day >= cur["last_try"]:
                cur["last_try"], cur["last_result"] = day, res
            if res == "ok" and (not cur["last_ok"] or day > cur["last_ok"]):
                cur["last_ok"] = day
    negs, gaps = {}, {}
    for k, v in ((state or {}).get("EXPLICIT_NEGATIVES") or {}).items():
        if k.startswith("_"):
            continue
        j = _jur_of(k) or _jur_of(str(v))
        if j:
            negs.setdefault(j, []).append(f"{k}: {v}")
    for g in (state or {}).get("REMAINING_GAPS") or []:
        j = _jur_of(str(g))
        if j:
            gaps.setdefault(j, []).append(str(g))
    sweep = (state or {}).get("last_successful_sweep")
    jur = []

    def adapter_read(names):
        oks = [src.get(a, {}).get("last_ok") for a in names if src.get(a, {}).get("last_ok")]
        fails = max([src.get(a, {}).get("consecutive_failures") or 0 for a in names] or [0])
        errs = [src.get(a, {}).get("last_error") for a in names if src.get(a, {}).get("last_error")]
        return (max(oks) if oks else None), fails, (errs[0] if errs else None)

    for code, cfg in (wl.get("jurisdictions") or {}).items():
        route = cfg.get("route")
        e = {"code": code, "route": route, "note": cfg.get("note") or "", "negatives": negs.get(code, []),
             "gaps": gaps.get(code, [])}
        if route == "collector":
            e["last_read"], e["failures"], e["last_error"] = adapter_read([cfg.get("adapter")])
            e["read_by"] = "Nightly collector"
        elif route == "webfetch":
            e["last_read"], e["failures"], e["last_error"] = sweep, 0, None
            e["read_by"] = "Monday Sweep (web reader)"
        else:
            mm = manual.get(code) or {}
            e["last_read"], e["failures"], e["last_error"] = mm.get("last_ok"), 0, None
            e["last_try"], e["last_result"] = mm.get("last_try"), mm.get("last_result")
            e["read_by"] = "Friday manual pass"
        jur.append(e)
    fed = adapter_read(["federal_register", "congress", "regulations_gov"])
    jur.append({"code": "US-Federal", "route": "collector", "read_by": "Nightly collector",
                "note": "Federal Register, congress.gov and Regulations.gov", "last_read": fed[0],
                "failures": fed[1], "last_error": fed[2], "negatives": negs.get("US-Federal", []),
                "gaps": gaps.get("US-Federal", [])})
    lf = cs.get("last_full_run") or {}
    return {"asof": asof, "last_sweep": sweep, "collector_last_full_run": lf.get("finished"),
            "nights": nights, "jurisdictions": jur,
            "manual_runs": sorted({v["last_try"] for v in manual.values() if v["last_try"]})}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--asof", required=True)
    ap.add_argument("--status")
    ap.add_argument("--narrative")
    ap.add_argument("--deliverables")
    ap.add_argument("--store", default=rowstore.STORE)
    ap.add_argument("--state", help="OneDrive state.json (for the change baseline, explicit negatives and gaps)")
    ap.add_argument("--manual-dir", help="folder holding the complete manual-pass manifests manual_<run_id>.json")
    ap.add_argument("--since", help="'changed since' date for the console; default state.last_brief_date")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    for f in os.listdir(a.outdir):          # never publish a stale file from an earlier build
        os.remove(os.path.join(a.outdir, f))

    _, rows = rowstore.load(a.store)
    problems = rowstore.validate(rows)
    ev = rowstore.events(rows)
    files, notes = {}, {}
    if a.narrative:
        shutil.copy(a.narrative, os.path.join(a.outdir, "narrative.md"))
        files["md"] = {"path": "narrative.md", "name": f"Grid_Docket_Weekly_{a.asof}.md"}
        pdf = f"Grid_Docket_Weekly_{a.asof}.pdf"
        notes["pdf"] = narr.to_pdf(a.narrative, os.path.join(a.outdir, pdf), a.asof)
        files["pdf"] = {"path": pdf, "name": pdf}
    table = [[("" if v is None else v) for v in r[:26]] for r in rows]
    parts, changes, first = history(a.store)
    for e in ev:
        e["part"] = first.get(e["id"])
    state = json.load(open(a.state)) if a.state else None
    ann = json.load(open(os.path.join(ROOT, "console", "annotations.json")))
    wl = yaml.safe_load(open(os.path.join(ROOT, "config", "watchlist.yaml")))
    data = {"generated": a.asof, "asof": a.asof, "events": len(ev), "rows": len(rows),
            "data": ev, "table": table, "columns": build_tracker.COLUMNS if hasattr(build_tracker, "COLUMNS") else None,
            "files": files, "parts": parts, "changes": changes,
            "since": a.since or (state or {}).get("last_brief_date"),
            "coverage": coverage(state, a.manual_dir, a.asof),
            "annotations": ann, "parties": wl.get("parties") or []}
    json.dump(data, open(os.path.join(a.outdir, "data.json"), "w"), ensure_ascii=False)
    for f in ("metrics.json", "tariff_terms.json"):
        shutil.copy(os.path.join(a.store, f), os.path.join(a.outdir, f))
    page(os.path.join(a.outdir, "index.html"))
    status = json.load(open(a.status)) if a.status else None
    json.dump(status, open(os.path.join(a.outdir, "status.json"), "w"), ensure_ascii=False)

    xres = None
    if a.deliverables:
        os.makedirs(a.deliverables, exist_ok=True)
        xres = build_tracker.build(rows, os.path.join(a.deliverables, XLSX), asof=a.asof)
        problems += xres.get("problems", [])
        if a.narrative:
            narr.to_docx(a.narrative, os.path.join(a.deliverables, f"Grid_Docket_Weekly_{a.asof}.docx"))
            shutil.copy(os.path.join(a.outdir, files["pdf"]["path"]), a.deliverables)
            shutil.copy(a.narrative, os.path.join(a.deliverables, f"Grid_Docket_Weekly_{a.asof}.md"))
    out = {"events": len(ev), "rows": len(rows), "problems": problems, "notes": notes,
           "files": sorted(os.listdir(a.outdir)),
           "deliverables": sorted(os.listdir(a.deliverables)) if a.deliverables else None}
    print(json.dumps(out))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
