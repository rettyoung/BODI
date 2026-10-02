"""Build Grid_Docket_Tracker_MASTER.xlsx from the row store.

Reproduces the established workbook exactly: Tracker sheet (26 columns, Arial 9,
centre/middle, wrap, freeze C2, autofilter, materiality by font colour,
confidence by fill, alternating band per Event ID) and Summary sheet (live
COUNTIF/SUMPRODUCT formulas, never hard-coded). Refuses to ship when a
controlled-vocabulary total does not reconcile to the row count.

usage: python build_tracker.py OUT.xlsx [--store DIR] [--asof YYYY-MM-DD]
"""
import argparse
import collections
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

import rowstore
from vocab import COLUMNS, LEVERS, SUBJECTS, VENUES, MATERIALITY, CONFIDENCE, JURISDICTIONS

WIDTHS = [11, 16, 16, 12, 22, 21, 16, 36, 44, 66, 20, 24, 12, 16, 12, 9, 11,
          11, 11, 11, 11, 11, 11, 11, 11, 38]
NAVY, BAND, GRID = "1F3243", "F7F5F1", "D9D9D9"
MAT_FONT = {"High / near-term": ("9A2F2F", True), "Medium / long-term": ("8A6414", False)}
CONF_FILL = {"Verified": "E3F0E8", "Reported": "F8EED6", "Unverified": "F6E2E0"}
GREY = "6B7280"

thin = Side(style="thin", color=GRID)
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)


def fill(rgb):
    return PatternFill("solid", fgColor=rgb)


def build(rows, out, asof=None, baseline_note=None):
    probs = rowstore.validate(rows)
    rows = rowstore.sort_rows(rows)
    n = len(rows) + 1  # last data row

    wb = Workbook()
    ws = wb.active
    ws.title = "Tracker"
    ws.append(COLUMNS)
    ws.row_dimensions[1].height = 34
    for c in ws[1]:
        c.font = Font(name="Arial", size=9, bold=True, color="FFFFFF")
        c.fill = fill(NAVY)
        c.alignment = CENTER
        c.border = BORDER

    band, last_eid = False, None
    for r in rows:
        if r[1] != last_eid:
            band = not band if last_eid is not None else False
            last_eid = r[1]
        vals = list(r)
        for i in range(17, 25):
            vals[i] = 1 if vals[i] in (1, "1") else None
        ws.append(vals)
        rr = ws.max_row
        ws.row_dimensions[rr].height = 76
        for ci, c in enumerate(ws[rr]):
            c.font = Font(name="Arial", size=9)
            c.alignment = CENTER
            c.border = BORDER
            if band:
                c.fill = fill(BAND)
        mcell = ws.cell(rr, 14)
        col, bold = MAT_FONT.get(mcell.value, (None, False))
        mcell.font = Font(name="Arial", size=9, bold=bold, color=col)
        ccell = ws.cell(rr, 15)
        if ccell.value in CONF_FILL:
            ccell.fill = fill(CONF_FILL[ccell.value])

    for i, w in enumerate(WIDTHS):
        ws.column_dimensions[chr(65 + i)].width = w
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:Z{n}"

    # ---------------- Summary ----------------
    s = wb.create_sheet("Summary")
    s.column_dimensions["A"].width = 44
    s.column_dimensions["B"].width = 12
    A = lambda r: f"Tracker!${r}$2:${r}${n}"
    row = [1]

    def put(a, b=None, bold=False, size=10, italic=False, color=None):
        r = row[0]
        s.cell(r, 1, a).font = Font(name="Arial", size=size, bold=bold, italic=italic, color=color)
        if b is not None:
            s.cell(r, 2, b).font = Font(name="Arial", size=size, bold=bold)
        row[0] += 1
        return r

    def blank():
        s.cell(row[0], 1).font = Font(name="Arial", size=11)
        row[0] += 1

    distinct = len({r[1] for r in rows})
    baseline = sum(1 for r in rows if str(r[1]).startswith("E-20260918"))
    put("GRID DOCKET — MASTER TRACKER", bold=True, size=13)
    put(baseline_note or (
        f"Row store through {asof or rows[0][0]}: {distinct} events / {len(rows)} rows. "
        f"Baseline 7 Nov 2025 to 18 Sep 2026 ({baseline} rows), all three phases plus the gap-closing second pass; "
        f"weekly sweeps thereafter. Materiality floor High and Medium only."), size=9, italic=True, color=GREY)
    put("Event ID prefix E-20260918 = loaded as baseline, not observed in flight. Later prefixes are the discovery "
        "date of the sweep that found the item. Rows sharing an Event ID are ONE event exploded across entities and "
        "jurisdictions — count events, not rows.", size=9, italic=True, color=GREY)
    blank()
    put("Scale", "Count", bold=True)
    r_rows = put("Rows (entity exposures)", f"=COUNTA({A('A')})", bold=True)
    r_ev = put("Distinct events", f'=SUMPRODUCT(({A("B")}<>"")/COUNTIF({A("B")},{A("B")}&""))', bold=True)
    put("Avg rows per event", f"=IFERROR(B{r_rows}/B{r_ev},0)")

    def block(title, col, values, total=True, by_value=True):
        blank()
        put(title, "Count", bold=True)
        first = row[0]
        for v in values:
            crit = f"A{row[0]}" if by_value else "1"
            put(v, f"=COUNTIF({A(col)},{crit})")
        if total:
            put("TOTAL", f"=SUM(B{first}:B{row[0]-1})", bold=True)

    present = lambda idx, vocab: [v for v in vocab if v in {r[idx] for r in rows}] + \
        sorted({r[idx] for r in rows} - set(vocab) - {None, ""})
    block("Materiality (rows)", "N", MATERIALITY)
    block("Confidence (rows)", "O", CONFIDENCE)
    subj_order = [v for v, _ in collections.Counter(r[4] for r in rows).most_common()]
    block("Subject (rows)", "E", subj_order + [v for v in SUBJECTS if v not in subj_order])
    ven_order = [v for v, _ in collections.Counter(r[5] for r in rows).most_common()]
    block("Venue (rows)", "F", ven_order + [v for v in VENUES if v not in ven_order])
    blank()
    put("Lever (rows)", "Count", bold=True)
    for i, lv in enumerate(LEVERS):
        put(lv, f"=COUNTIF({A(chr(65 + 17 + i))},1)")
    blank()
    put("(multi-select — exceeds row count)", size=8, italic=True, color=GREY)
    jur_order = [v for v, _ in collections.Counter(r[3] for r in rows).most_common()]
    block("Jurisdiction (rows)", "D", jur_order + [v for v in JURISDICTIONS if v not in jur_order])
    blank()
    put("Flags (rows)", "Count", bold=True)
    put("On appeal", f'=COUNTIF({A("P")},"Yes")')
    put("Superseded", f'=COUNTIF({A("Q")},"Yes")')

    # ---------------- sanity check (the formulas' own arithmetic, done in Python) ----------------
    total = len(rows)
    for name, idx in (("Materiality", 13), ("Confidence", 14), ("Subject", 4), ("Venue", 5), ("Jurisdiction", 3)):
        vocab = {"Materiality": MATERIALITY, "Confidence": CONFIDENCE, "Subject": SUBJECTS,
                 "Venue": VENUES, "Jurisdiction": JURISDICTIONS}[name]
        counted = sum(1 for r in rows if r[idx] in vocab)
        if counted != total:
            bad = sorted({str(r[idx]) for r in rows if r[idx] not in vocab})
            probs.append(f"{name} totals {counted} != {total} rows; out-of-vocabulary: {bad}")

    wb.active = 0
    wb.save(out)
    return {"rows": total, "events": distinct, "problems": probs, "path": out}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--store", default=rowstore.STORE)
    ap.add_argument("--asof")
    a = ap.parse_args()
    _, rows = rowstore.load(a.store)
    res = build(rows, a.out, asof=a.asof)
    print(res)
    sys.exit(1 if res["problems"] else 0)
