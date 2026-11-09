"""Split tracker state (added 2026-11-09 after sweep 2026-11-09-1155 could not upload a 104 KB state.json).

Why. A scheduled run can write to OneDrive only by sending a file's full text through the Microsoft 365
connector, so every byte of a rewritten file is retyped. state.json grew to 104 KB, mostly
backfill_cursor.done (1,500+ opaque ids a run), and could not be sent. The fix keeps every file a run REWRITES
small, and puts anything that only grows into append-only parts that are written once and never again.

Layout in /GridDocket/ (and store_live/):
  state.json            CORE: cursors and run bookkeeping (last_successful_sweep, collector_cursor,
                        manual_ingested, corrections_done, read_backlog, mail_seen, backfill_cursor without
                        "done", row_store, baseline, ...). Rewritten every run; target < 20 KB.
  state_tracking.json   near_term_milestones and REMAINING_GAPS. Rewritten when they change.
  state_reference.json  slow-moving knowledge: REGISTRY_CORRECTIONS, STRUCTURAL_FINDINGS,
                        ACCESS_METHOD_FINDINGS, EXPLICIT_NEGATIVES, WATCH_SIGNALS,
                        standing_facts_for_the_brief, pipeline_baselines_for_delta. Rarely rewritten.
  backfill_done_pN.json append-only: {"schema": "grid-docket-backfill-done-v1", "run_id", "written",
                        "ids": [...]} — the C-07/C-08 items a run actually READ (or sent to the manual queue).
                        Items shortlist.py screens out are NOT stored: the screen is deterministic, so
                        re-running it screens them again (record only the count in the run record).
  state_frozen_*.json   a frozen pre-split state.json; only its backfill_cursor.done is read (legacy ids).

Every reader sees ONE merged dict (load / load_path), exactly the old state.json shape, with
backfill_cursor.done = the union of the legacy list and every backfill_done_p*.json. So "state.X" in the
prompts still means the same thing.

usage
  python tracker/statefile.py merge STORE [--out FILE]
        Write the merged view (default STORE/_state_merged.json) and print one line of counts. Edit that
        file (Python, by key) during the run; never hand-edit the split files.
  python tracker/statefile.py split MERGED STORE
        Write STORE/state.json, state_tracking.json and state_reference.json from a merged dict. Drops
        backfill_cursor.done (it lives in the parts) and drops resolved milestones dated more than 45 days
        ago (the row store keeps the outcome). mail_seen.ids should hold only the ids this run processed (the
        mail filter overlaps by one day; the ids exist only to skip that overlap). Prints each file's size and which
        files changed versus what was there, so only changed files are uploaded. Warns above 32 KB.
  python tracker/statefile.py done-part STORE --run RUN_ID --ids ID [ID ...] | --ids-from FILE.json
        Write the next backfill_done_pN.json (N = one past the highest present). --ids-from takes a
        shortlist.py backfill/c08 output and uses its "batch" ids. Upload it with conflictBehavior "fail".
  python tracker/statefile.py sizes STORE
        Size of each state file and the merged done count.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

TRACKING_KEYS = ("near_term_milestones", "REMAINING_GAPS")
REFERENCE_KEYS = ("REGISTRY_CORRECTIONS", "STRUCTURAL_FINDINGS", "ACCESS_METHOD_FINDINGS", "EXPLICIT_NEGATIVES",
                  "WATCH_SIGNALS", "standing_facts_for_the_brief", "pipeline_baselines_for_delta")
FILES = {"state_tracking.json": TRACKING_KEYS, "state_reference.json": REFERENCE_KEYS}
DONE_RE = re.compile(r"^backfill_done_p(\d+)\.json$")
WARN_BYTES = 32 * 1024
DONE_SCHEMA = "grid-docket-backfill-done-v1"


def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _dump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"


def done_parts(store):
    parts = []
    for p in glob.glob(os.path.join(store, "backfill_done_p*.json")):
        m = DONE_RE.match(os.path.basename(p))
        if m:
            parts.append((int(m.group(1)), p))
    return [p for _, p in sorted(parts)]


def done_ids(store, core=None):
    """Union of every recorded done id: legacy lists (core state, frozen states) + append-only parts."""
    out, seen = [], set()

    def add(ids):
        for i in ids or []:
            if i not in seen:
                seen.add(i)
                out.append(i)
    if core:
        add((core.get("backfill_cursor") or {}).get("done"))
    for p in sorted(glob.glob(os.path.join(store, "state_frozen_*.json"))):
        add((_read(p).get("backfill_cursor") or {}).get("done"))
    for p in done_parts(store):
        add(_read(p).get("ids"))
    return out


def load(store):
    """The merged state dict for a store folder (old single-file state.json still works)."""
    core = _read(os.path.join(store, "state.json"))
    st = dict(core)
    for name, keys in FILES.items():
        p = os.path.join(store, name)
        if os.path.exists(p):
            side = _read(p)
            for k in keys:
                if k in side:
                    st[k] = side[k]
    bc = dict(st.get("backfill_cursor") or {})
    bc["done"] = done_ids(store, core)
    st["backfill_cursor"] = bc
    return st


def load_path(state_path):
    """Merged view given a path to state.json (what scripts receive as --state)."""
    return load(os.path.dirname(os.path.abspath(state_path)) or ".")


def _trim(st, today):
    cutoff = (today - timedelta(days=45)).isoformat()
    nt = st.get("near_term_milestones")
    if isinstance(nt, list):
        st["near_term_milestones"] = [m for m in nt if not (
            isinstance(m, dict) and str(m.get("status", "")).upper().startswith("RESOLVED")
            and str(m.get("date", "9999")) < cutoff)]
    return st


def split(merged, store, today=None):
    today = today or date.today()
    st = _trim(json.loads(json.dumps(merged)), today)
    side = {}
    for name, keys in FILES.items():
        side[name] = {"schema": "grid-docket-" + name[:-5].replace("_", "-") + "-v1",
                      "_doc": "Part of the tracker state (tracker/statefile.py). Readers merge state.json, "
                              "state_tracking.json, state_reference.json and backfill_done_p*.json."}
        for k in keys:
            if k in st:
                side[name][k] = st.pop(k)
    bc = dict(st.get("backfill_cursor") or {})
    bc.pop("done", None)
    bc["_done_doc"] = ("Done ids live in backfill_done_p*.json (append-only, one per run) plus the legacy list in "
                       "state_frozen_*.json; tracker/statefile.py merges them. Screened items are not stored.")
    st["backfill_cursor"] = bc
    st["_split_doc"] = ("Core state only. near_term_milestones and REMAINING_GAPS are in state_tracking.json; "
                        "reference blocks in state_reference.json; done ids in backfill_done_p*.json. "
                        "Read with tracker/statefile.py merge.")
    out = {"state.json": st}
    out.update(side)
    report = []
    for name, obj in out.items():
        text = _dump(obj)
        p = os.path.join(store, name)
        old = open(p, "rb").read() if os.path.exists(p) else None
        changed = old != text.encode("utf-8")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        n = len(text.encode("utf-8"))
        report.append((name, n, changed))
    return report


def write_done_part(store, run_id, ids):
    nums = [int(DONE_RE.match(os.path.basename(p)).group(1)) for p in done_parts(store)]
    n = (max(nums) + 1) if nums else 1
    name = f"backfill_done_p{n}.json"
    obj = {"schema": DONE_SCHEMA, "run_id": run_id, "written": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
           "ids": list(dict.fromkeys(ids))}
    with open(os.path.join(store, name), "w", encoding="utf-8") as f:
        f.write(_dump(obj))
    return name, len(obj["ids"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge"); m.add_argument("store"); m.add_argument("--out")
    s = sub.add_parser("split"); s.add_argument("merged"); s.add_argument("store"); s.add_argument("--today")
    d = sub.add_parser("done-part"); d.add_argument("store"); d.add_argument("--run", required=True)
    d.add_argument("--ids", nargs="*"); d.add_argument("--ids-from")
    z = sub.add_parser("sizes"); z.add_argument("store")
    a = ap.parse_args()
    if a.cmd == "merge":
        st = load(a.store)
        out = a.out or os.path.join(a.store, "_state_merged.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=1)
        print(f"MERGED state -> {out}: {len(st)} keys; backfill done ids {len(st['backfill_cursor']['done'])}; "
              f"manual_ingested {len(st.get('manual_ingested') or [])}; last_successful_sweep "
              f"{st.get('last_successful_sweep')}")
    elif a.cmd == "split":
        today = date.fromisoformat(a.today) if a.today else None
        rep = split(_read(a.merged), a.store, today)
        warn = False
        for name, n, ch in rep:
            flag = " WARNING over 32 KB — move growing data to an append-only part" if n > WARN_BYTES else ""
            warn = warn or bool(flag)
            print(f"{name} {n} bytes {'CHANGED (upload)' if ch else 'unchanged (do not upload)'}{flag}")
        sys.exit(1 if warn else 0)
    elif a.cmd == "done-part":
        ids = list(a.ids or [])
        if a.ids_from:
            j = _read(a.ids_from)
            ids += [b["id"] if isinstance(b, dict) else b for b in (j.get("batch") or [])]
        if not ids:
            print("no ids: nothing written"); sys.exit(0)
        name, n = write_done_part(a.store, a.run, ids)
        p = os.path.join(a.store, name)
        print(f"{name} {n} ids {os.path.getsize(p)} bytes (upload with conflictBehavior fail)")
    elif a.cmd == "sizes":
        for name in ["state.json", *FILES, *[os.path.basename(p) for p in done_parts(a.store)]]:
            p = os.path.join(a.store, name)
            if os.path.exists(p):
                print(f"{name} {os.path.getsize(p)}")
        print(f"merged done ids {len(done_ids(a.store, _read(os.path.join(a.store, 'state.json'))))}")


if __name__ == "__main__":
    main()
