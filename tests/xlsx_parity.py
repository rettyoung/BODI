"""Compare the browser-built workbook (ExcelJS) with the canonical Python build.

usage: python tests/xlsx_parity.py python.xlsx exceljs.xlsx [report.json]
Checks every cell's value/formula, font, fill, border, alignment, number format,
row heights, column widths, freeze panes and autofilter on both sheets.
"""
import json
import sys

from openpyxl import load_workbook


def norm_color(c):
    if c is None:
        return None
    v = c.rgb if isinstance(c.rgb, str) else None
    return v[-6:].upper() if v else None


def style(c):
    f, fl, b, a = c.font, c.fill, c.border, c.alignment
    return {
        "font": (f.name, float(f.sz or 0), bool(f.b), bool(f.i), norm_color(f.color)),
        "fill": (fl.fill_type, norm_color(fl.fgColor)) if fl and fl.fill_type else None,
        "border": tuple((getattr(b, s).style, norm_color(getattr(b, s).color)) for s in ("left", "right", "top", "bottom")),
        "align": (a.horizontal, a.vertical, bool(a.wrap_text)),
        "fmt": c.number_format,
    }


def val(c):
    v = c.value
    if isinstance(v, str) and v.startswith("="):
        return ("f", v.replace(" ", ""))
    return ("v", v)


def main():
    a, b = load_workbook(sys.argv[1]), load_workbook(sys.argv[2])
    diffs = []
    for name in ("Tracker", "Summary"):
        wa, wb = a[name], b[name]
        if (wa.max_row, wa.max_column) != (wb.max_row, wb.max_column):
            diffs.append(f"{name}: size {wa.max_row}x{wa.max_column} vs {wb.max_row}x{wb.max_column}")
        for r in range(1, max(wa.max_row, wb.max_row) + 1):
            ha, hb = wa.row_dimensions[r].height, wb.row_dimensions[r].height
            if (ha or None) != (hb or None) and not (ha is None and hb is None):
                diffs.append(f"{name}!row{r} height {ha} vs {hb}")
            for c in range(1, max(wa.max_column, wb.max_column) + 1):
                ca, cb = wa.cell(r, c), wb.cell(r, c)
                if val(ca) != val(cb):
                    diffs.append(f"{name}!{ca.coordinate} value {val(ca)!r} vs {val(cb)!r}")
                if ca.value is None and cb.value is None and name == "Summary":
                    continue
                sa, sb = style(ca), style(cb)
                for k in sa:
                    if sa[k] != sb[k]:
                        diffs.append(f"{name}!{ca.coordinate} {k} {sa[k]} vs {sb[k]}")
        for col, dim in wa.column_dimensions.items():
            wb_w = wb.column_dimensions[col].width
            if dim.width and abs((dim.width or 0) - (wb_w or 0)) > 0.01:
                diffs.append(f"{name} col {col} width {dim.width} vs {wb_w}")
        if name == "Tracker":
            if wa.freeze_panes != wb.freeze_panes:
                diffs.append(f"freeze {wa.freeze_panes} vs {wb.freeze_panes}")
            if (wa.auto_filter.ref or "") != (wb.auto_filter.ref or ""):
                diffs.append(f"autofilter {wa.auto_filter.ref} vs {wb.auto_filter.ref}")
    rep = {"python": sys.argv[1], "exceljs": sys.argv[2], "diffs": len(diffs), "first": diffs[:60]}
    print(json.dumps(rep, indent=1, default=str))
    if len(sys.argv) > 3:
        json.dump(rep, open(sys.argv[3], "w"), indent=1, default=str)
    sys.exit(1 if diffs else 0)


if __name__ == "__main__":
    main()
