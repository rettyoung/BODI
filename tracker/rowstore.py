"""Load, validate and merge the Grid Docket row store.

The system of record is OneDrive /GridDocket/ (rows.json manifest + immutable
rows_pN.json parts). Scheduled runs download the live store into store_live/
and run every tool against it (`--store store_live`). `store/` in this repo is a
frozen copy of the 2026-09-18 baseline (rows_p1..p4), kept for tests and CI.
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


# Parts are immutable. A later part changes an earlier event only through overlays, applied
# at load in manifest order, so history stays auditable and no part is ever rewritten:
#   "supersedes": [{"old_event_id", "new_event_id", "reason"}]   -> Superseded = "Yes" on every old row
#   "overlays":   [{"event_id", "column", "value", "reason"}]    -> only the columns below
OVERLAY_COLUMNS = ("Status", "Next Milestone", "Next Date", "Appeal", "Superseded")


def apply_overlays(rows, part):
    ix = {c: i for i, c in enumerate(COLUMNS)}
    probs = []
    ids = {r[1] for r in rows}
    for s in part.get("supersedes") or []:
        if s.get("old_event_id") not in ids:
            probs.append(f"supersedes unknown event {s.get('old_event_id')}")
        for r in rows:
            if r[1] == s.get("old_event_id"):
                r[ix["Superseded"]] = "Yes"
    for o in part.get("overlays") or []:
        if o.get("column") not in OVERLAY_COLUMNS:
            probs.append(f"overlay on non-overlayable column {o.get('column')!r}")
            continue
        if o.get("event_id") not in ids:
            probs.append(f"overlay on unknown event {o.get('event_id')}")
        for r in rows:
            if r[1] == o.get("event_id"):
                r[ix[o["column"]]] = o.get("value") or ""
    return probs


def load(store=STORE, extra_part=None, problems=None):
    """Return (columns, rows) concatenated in manifest order, overlays applied.
    extra_part: a part dict not yet in the manifest (to validate before committing)."""
    man = json.load(open(os.path.join(store, "rows.json")))
    rows, columns = [], None
    parts = [json.load(open(os.path.join(store, p["file"]))) for p in man["parts"]]
    if extra_part:
        parts.append(extra_part)
    for d in parts:
        if d.get("columns"):
            if columns and d["columns"] != columns:
                raise ValueError("column order differs between parts")
            columns = d["columns"]
        rows.extend([list(r) for r in d["data"]])
        pr = apply_overlays(rows, d)
        if problems is not None:
            problems.extend(pr)
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
    # one Event ID = one date (otherwise its rows would not stay adjacent after sorting)
    dates = {}
    for r in rows:
        if len(r) == 26:
            dates.setdefault(r[1], set()).add(r[0])
    for eid, ds in dates.items():
        if len(ds) > 1:
            probs.append(f"{eid}: rows carry different dates {sorted(ds)} — exploded rows must share one date")
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


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Validate the row store, optionally with a new part not yet committed.")
    ap.add_argument("--store", default=STORE)
    ap.add_argument("--part", help="path to a new rows_pN.json to validate together with the store")
    a = ap.parse_args()
    extra = json.load(open(a.part)) if a.part else None
    probs = []
    _, rows = load(a.store, extra_part=extra, problems=probs)
    probs += validate(rows)
    if extra:
        old = set()
        for p in json.load(open(os.path.join(a.store, "rows.json")))["parts"]:
            old |= {r[1] for r in json.load(open(os.path.join(a.store, p["file"])))["data"]}
        clash = sorted({r[1] for r in extra["data"]} & old)
        if clash:
            probs.append(f"new part reuses existing Event IDs: {clash[:10]}")
    ev = len({r[1] for r in rows})
    print(json.dumps({"rows": len(rows), "events": ev, "problems": probs[:50], "n_problems": len(probs)}, indent=1))
    raise SystemExit(1 if probs else 0)
