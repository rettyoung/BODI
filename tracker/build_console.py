"""Assemble the publishable console package from the row store.

usage: python build_console.py OUTDIR --asof YYYY-MM-DD [--status status.json] [--narrative brief.md]
                               [--deliverables DIR]

OUTDIR receives what the Artifact tool can serve: index.html (with the in-browser
workbook builder inlined), data.json (events for the views + the full 26-column
row table the workbook is built from), metrics.json, tariff_terms.json,
status.json and, with --narrative, narrative.md and the narrative PDF.

The Excel tracker itself cannot be served as an artifact file, so the page builds
it in the browser (console/tracker_xlsx.js) from the same rows. The canonical
Python-built workbook (and the narrative .docx) go to --deliverables, which the
Brief commits to the repo each week. CI (xlsx-parity) checks the two builds agree.
"""
import argparse
import json
import os
import shutil
import sys

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--asof", required=True)
    ap.add_argument("--status")
    ap.add_argument("--narrative")
    ap.add_argument("--deliverables")
    ap.add_argument("--store", default=rowstore.STORE)
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
    data = {"generated": a.asof, "asof": a.asof, "events": len(ev), "rows": len(rows),
            "data": ev, "table": table, "columns": build_tracker.COLUMNS if hasattr(build_tracker, "COLUMNS") else None,
            "files": files}
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
