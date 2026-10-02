"""Render the weekly narrative (markdown) to PDF and DOCX.

PDF: pandoc -> HTML fragment, wrapped in a print stylesheet that matches the
console, printed by headless Chromium (Playwright). Falls back to LibreOffice
(docx -> pdf) when Chromium is unavailable. DOCX: pandoc, then Arial body text.

usage: python narrative.py brief.md --asof YYYY-MM-DD --pdf out.pdf [--docx out.docx]
"""
import argparse
import html
import os
import shutil
import subprocess
import tempfile

CSS = """
@page { size: Letter; margin: 0.8in 0.85in 0.8in 0.85in; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 10pt; line-height: 1.5; color: #1b2430; }
.mast { border-bottom: 2px solid #1F3243; padding-bottom: 8pt; margin-bottom: 14pt; }
.eyebrow { font-size: 7.5pt; letter-spacing: .14em; text-transform: uppercase; color: #6b7280; margin: 0 0 3pt; }
h1 { font-size: 17pt; margin: 0; color: #1F3243; }
.sub { font-size: 8.5pt; color: #6b7280; margin-top: 3pt; font-family: "Courier New", monospace; }
h2 { font-size: 12pt; color: #1F3243; margin: 14pt 0 4pt; }
h3 { font-size: 8.5pt; letter-spacing: .1em; text-transform: uppercase; color: #6b7280; margin: 14pt 0 4pt;
     border-top: 1px solid #D9D9D9; padding-top: 6pt; }
h3:first-of-type { border-top: 0; padding-top: 0; }
p { margin: 4pt 0; } ul { margin: 3pt 0; padding-left: 14pt; } li { margin: 2.5pt 0; }
a { color: #1F3243; } strong { color: #111; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; margin: 6pt 0; }
th { background: #1F3243; color: #fff; text-align: left; padding: 3pt 5pt; }
td { border-bottom: 1px solid #D9D9D9; padding: 3pt 5pt; vertical-align: top; }
.foot { margin-top: 18pt; border-top: 1px solid #D9D9D9; padding-top: 6pt; font-size: 7.5pt; color: #6b7280; }
"""


def _html(md_path, asof):
    frag = subprocess.run(["pandoc", md_path, "-f", "gfm", "-t", "html5"], check=True,
                          capture_output=True, text=True).stdout
    title = "Grid Docket — weekly update"
    first = open(md_path, encoding="utf-8").readline().strip()
    if first.startswith("#"):
        title = first.lstrip("#").strip()
        # drop the duplicate h1/h2 pandoc made from the title line
        i = frag.find("</h1>") if frag.lstrip().startswith("<h1") else frag.find("</h2>") if frag.lstrip().startswith("<h2") else -1
        if i >= 0:
            frag = frag[i + 5:]
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="mast"><p class="eyebrow">Blue Owl Digital Infrastructure · Grid Docket</p>
<h1>{html.escape(title)}</h1><div class="sub">Week to {html.escape(asof)} · prepared for the BODI deal team</div></div>
{frag}
<div class="foot">Verified = primary document read; Reported = secondary source; Unverified figures are never published.
Events and rows are distinct counts: one event can touch several entities. Full row-level detail is in the Excel tracker.</div>
</body></html>"""


def to_pdf(md_path, pdf_path, asof):
    doc = _html(md_path, asof)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.set_content(doc, wait_until="load")
            pg.pdf(path=pdf_path, format="Letter", print_background=True, prefer_css_page_size=True)
            b.close()
        return "chromium"
    except Exception as e:  # fall back to LibreOffice
        tmp = tempfile.mkdtemp()
        d = os.path.join(tmp, "narrative.docx")
        to_docx(md_path, d)
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, d], check=True,
                       capture_output=True, timeout=180)
        shutil.move(os.path.join(tmp, "narrative.pdf"), pdf_path)
        return f"libreoffice (chromium failed: {e!r:.120})"


def to_docx(md_path, out_path):
    subprocess.run(["pandoc", md_path, "-f", "gfm", "-o", out_path], check=True)
    import docx
    from docx.shared import Pt
    d = docx.Document(out_path)
    for st in d.styles:
        try:
            if st.type == 1:
                st.font.name = "Arial"
                if st.name == "Normal":
                    st.font.size = Pt(10)
        except Exception:
            pass
    d.save(out_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("--asof", required=True)
    ap.add_argument("--pdf")
    ap.add_argument("--docx")
    a = ap.parse_args()
    if a.pdf:
        print("pdf via", to_pdf(a.md, a.pdf, a.asof))
    if a.docx:
        to_docx(a.md, a.docx)
        print("docx", a.docx)
