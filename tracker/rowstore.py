"""Load, validate and merge the Grid Docket row store.

The system of record is OneDrive /GridDocket/ (rows.json manifest + immutable
rows_pN.json parts). `store/` in this repo is a mirror of those immutable parts
so the builders can run without transcribing the store through a connector.
Each run checks the mirror against the OneDrive manifest (part names, row
counts, sha256) before building.
"""
import hashlib
import json
import os
import re

from vocab import COLUMNS, LEVERS, SUBJECTS, VENUES, INSTRUMENTS, MATERIALITY, CONFIDENCE, YESNO, JURISDICTIONS

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(os.path.dirname(HERE), "store")
EID = re.compile(r"^E-\d{8}-\d{3}$")


def part_sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load(store=STORE):
    """Return (columns, rows) concatenated in manifest order."""
    man = json.load(open(os.path.join(store, "rows.json")))
    rows, columns = [], None
    for p in man["parts"]:
        d = json.load(open(os.path.join(store, p["file"])))
        if d.get("columns"):
            columns = d["columns"]
        rows.extend(d["data"])
    columns = columns or man.get("columns") or COLUMNS
    if columns != COLUMNS:
        raise ValueError(f"column order differs from schema: {columns}")
    return columns, rows


def validate(rows):
    """Return a list of problems. Empty list = clean."""
    probs = []
    ix = {c: i for i, c in enumerate(COLUMNS)}
    checks = {"Subject": SUBJECTS, "Venue": VENUES, "Instrument": INSTRUMENTS, "Materiality": MATERIALITY,
              "Confidence": CONFIDENCE, "Appeal": YESNO, "Superseded": YESNO, "Jurisdiction": JURISDICTIONS}
    for n, r in enumerate(rows, start=2):
        if len(r) != 26:
            probs.append(f"row {n}: {len(r)} cells, expected 26")
            continue
        if not EID.match(str(r[ix["Event ID"]])):
            probs.append(f"row {n}: bad Event ID {r[ix['Event ID']]!r}")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(r[ix["Date"]])):
            probs.append(f"row {n}: bad Date {r[ix['Date']]!r}")
        for col, vocab in checks.items():
            if r[ix[col]] not in vocab:
                probs.append(f"row {n}: {col} {r[ix[col]]!r} outside vocabulary")
        for lv in LEVERS:
            if r[ix[lv]] not in (1, None, ""):
                probs.append(f"row {n}: lever {lv} = {r[ix[lv]]!r} (must be 1 or blank)")
    # adjacency of exploded events after sort
    return probs


def sort_rows(rows):
    """(Date, Event ID) descending; rows sharing an Event ID stay adjacent in
    their stored order."""
    order = {}
    for i, r in enumerate(rows):
        order.setdefault(r[1], i)
    return sorted(rows, key=lambda r: (r[0], r[1], -order[r[1]]), reverse=True)


def events(rows):
    """Group rows into events in display order (console data shape)."""
    out, by = [], {}
    for r in sort_rows(rows):
        eid = r[1]
        if eid not in by:
            e = {"id": eid, "date": r[0], "subject": r[4], "venue": r[5], "instrument": r[6],
                 "document": r[7], "headline": r[8], "takeaway": r[9], "status": r[10],
                 "nm": r[11], "nd": r[12] or None, "mat": r[13], "conf": r[14], "appeal": r[15],
                 "sup": r[16], "levers": [LEVERS[i] for i in range(8) if r[17 + i] == 1],
                 "url": r[25], "ents": []}
            by[eid] = e
            out.append(e)
        by[eid]["ents"].append([r[2], r[3]])
    return out
