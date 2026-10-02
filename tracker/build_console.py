"""Assemble the publishable console package from the row store.

usage: python build_console.py OUTDIR --asof YYYY-MM-DD [--status status.json] [--narrative brief.md]

OUTDIR receives: index.html, data.json, metrics.json, tariff_terms.json,
status.json, Grid_Docket_Tracker_MASTER.xlsx and (optionally) the weekly
narrative as .docx. The Brief publishes OUTDIR to the existing console URL
with the Artifact tool's `files` map, so no binary ever passes through a
connector by hand.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import rowstore  # noqa
import build_tracker  # noqa

XLSX = "Grid_Docket_Tracker_MASTER.xlsx"


def narrative_docx(md_path, out_path):
    """Markdown -> .docx with Arial body text, via pandoc and python-docx."""
    subprocess.run(["pandoc", md_path, "-o", out_path], check=True)
    import docx
    from docx.shared import Pt
    d = docx.Document(out_path)
    for st in d.styles:
        try:
            if st.type == 1:  # paragraph styles
                st.font.name = "Arial"
                if st.name == "Normal":
                    st.font.size = Pt(10)
        except Exception:
            pass
    d.save(out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--asof", required=True)
    ap.add_argument("--status")
    ap.add_argument("--narrative")
    ap.add_argument("--store", default=rowstore.STORE)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    _, rows = rowstore.load(a.store)
    res = build_tracker.build(rows, os.path.join(a.outdir, XLSX), asof=a.asof)
    ev = rowstore.events(rows)
    files = {"xlsx": {"path": XLSX, "name": XLSX}}
    if a.narrative:
        name = f"Grid_Docket_Weekly_{a.asof}.docx"
        narrative_docx(a.narrative, os.path.join(a.outdir, name))
        files["docx"] = {"path": name, "name": name}
    data = {"generated": a.asof, "asof": a.asof, "events": len(ev), "rows": len(rows), "data": ev, "files": files}
    json.dump(data, open(os.path.join(a.outdir, "data.json"), "w"), ensure_ascii=False)
    for f in ("metrics.json", "tariff_terms.json"):
        shutil.copy(os.path.join(a.store, f), os.path.join(a.outdir, f))
    shutil.copy(os.path.join(ROOT, "console", "index.html"), os.path.join(a.outdir, "index.html"))
    status = json.load(open(a.status)) if a.status else None
    json.dump(status, open(os.path.join(a.outdir, "status.json"), "w"), ensure_ascii=False)
    out = {"events": len(ev), "rows": len(rows), "xlsx_problems": res["problems"], "files": sorted(os.listdir(a.outdir))}
    print(json.dumps(out))
    sys.exit(1 if res["problems"] else 0)


if __name__ == "__main__":
    main()
