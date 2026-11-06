"""Completeness and honesty gate for a manual pass (manual/SKILL.md step 6b; sweep.md Step 5.2b).

Added 2026-11-06, after the pass of that morning stopped early under "Continue until done" without asking,
recorded minutes_used null and a finish time an hour in the future, and labelled four Ohio items "captcha"
although Rett was never asked about them. Nothing outside the pass checked any of it. This script does:
the pass runs it on its own files before it writes the manifest, and the Monday Sweep runs it again on what
it ingests (the pass cannot grade its own homework).

usage:
    python tracker/manual_check.py --dir DIR --run RUN_ID [--manifest DRAFT.json] [--now ISO] [--json]

    DIR        a folder holding the run's files: manual_<run>.json (unless --manifest), manual_<run>_<STATE>.json,
               progress_<run>.json and pass_state.json (a copy of /GridDocket/manual/ works)
    --manifest a draft manifest to check instead of DIR/manual_<run>.json (the pass checks before it writes)
    --now      the time to judge "finished" against (default: now, UTC)
exit 0 = honest and complete as recorded; 1 = problems (printed); 2 = could not read an input.

What it fails:
  1. CLOCK      no progress file (runs from 2026-11-07 on); budget.minutes_used missing or not a number;
                "finished" missing, unparseable, later than --now, or earlier than the progress file's
                "started"; minutes_used more than 5 minutes away from finished - started.
  2. STOP       stopped_by outside list_empty | rett_stop | no_answer | session_limit; list_empty while items
                remain for reason time, not_attempted or partial_read; any other stop without a "stop" record
                in the progress file ({at, reason, asked, answer}); "Continue until done" chosen and the run
                stopped with such items left, unless the stop record shows Rett was asked or said stop.
  3. CAPTCHA    an item carried as "captcha" with no rett_asks entry naming its docket or state.
  4. REASONS    a carry-forward reason outside the step 6 list.
  5. AGREEMENT  a carry-forward item whose reason differs between a state file and pass_state.json, or that
                a state file carries and pass_state.json does not.
  6. COUNTS     manifest documents, carried_forward or carried_forward_by_reason not equal to what the
                saved files hold.
Notes (never a failure): runs before 2026-11-07 without a progress file; pass_state.json last updated by
another run (its carry-forward cannot be compared).
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone

REASONS = {"captcha", "render_failure", "partial_read", "not_located", "not_attempted", "time",
           "deprioritized", "not_yet_filed", "site_down"}
STOPS = {"list_empty", "rett_stop", "no_answer", "session_limit"}
SKIPPED = {"time", "not_attempted", "partial_read"}
PROGRESS_REQUIRED_FROM = "2026-11-07"


def _load(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def _ts(s):
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        t = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _key(item):
    return (str(item.get("state", "")).upper(), str(item.get("docket", "")).strip().lower())


def _until_done(progress):
    for e in progress.get("extensions") or []:
        c = str(e.get("choice", "") if isinstance(e, dict) else e).lower()
        if "until" in c:
            return True
    return False


def check(d, run, manifest_path=None, now=None):
    """Return (problems, notes). Raises OSError/ValueError on unreadable input."""
    problems, notes = [], []
    now = now or datetime.now(timezone.utc)
    man = _load(manifest_path or os.path.join(d, f"manual_{run}.json"))
    prog_path = os.path.join(d, f"progress_{run}.json")
    prog = _load(prog_path) if os.path.exists(prog_path) else None
    ps_path = os.path.join(d, "pass_state.json")
    ps = _load(ps_path) if os.path.exists(ps_path) else None
    states = {}
    for p in sorted(glob.glob(os.path.join(d, f"manual_{run}_*.json"))):
        doc = _load(p)
        states[os.path.basename(p)] = doc
    budget = man.get("budget") or {}

    # 1. CLOCK
    if prog is None:
        (problems if run[:10] >= PROGRESS_REQUIRED_FROM else notes).append(
            f"CLOCK: no progress_{run}.json")
    mu = budget.get("minutes_used")
    if not isinstance(mu, (int, float)) or isinstance(mu, bool):
        problems.append(f"CLOCK: budget.minutes_used is {mu!r}, not a number")
    fin = _ts(man.get("finished"))
    started = _ts((prog or {}).get("started"))
    if fin is None:
        problems.append(f"CLOCK: finished {man.get('finished')!r} is missing or unparseable")
    else:
        if fin > now:
            problems.append(f"CLOCK: finished {man.get('finished')} is later than now ({now.isoformat()[:16]}Z)")
        if started and fin < started:
            problems.append("CLOCK: finished is earlier than the progress file's started")
        if started and isinstance(mu, (int, float)) and abs((fin - started).total_seconds() / 60 - mu) > 5:
            problems.append(f"CLOCK: minutes_used {mu} does not match finished - started "
                            f"({round((fin - started).total_seconds() / 60)})")

    # carry-forward as recorded
    ps_items = []
    if ps is not None and ps.get("updated_by_run") == run:
        ps_items = ps.get("carry_forward") or []
    elif ps is not None:
        notes.append(f"pass_state.json was last updated by {ps.get('updated_by_run')}, not {run}")
    sf_items = []
    for name, doc in states.items():
        for it in doc.get("carry_forward") or []:
            sf_items.append((name, it))
    items = ps_items or [it for _, it in sf_items]
    left = [it for it in items if it.get("reason") in SKIPPED]

    # 2. STOP
    sb = budget.get("stopped_by")
    stop = (prog or {}).get("stop")
    if sb not in STOPS:
        problems.append(f"STOP: stopped_by {sb!r} is not one of {sorted(STOPS)}")
    if sb == "list_empty" and left:
        problems.append(f"STOP: stopped_by list_empty but {len(left)} item(s) remain for time, "
                        "not_attempted or partial_read")
    if sb in STOPS - {"list_empty"} and prog is not None and not isinstance(stop, dict):
        problems.append(f"STOP: stopped_by {sb} has no stop record in the progress file")
    if left and _until_done(prog or {}):
        ok = isinstance(stop, dict) and (stop.get("asked") or "stop" in str(stop.get("answer", "")).lower())
        if not ok:
            problems.append(f"STOP: Rett chose to continue until done and {len(left)} item(s) remain, "
                            "but no stop record shows he was asked or said stop")
    if prog is None and (budget.get("minutes_extended") or "") and "until" in str(budget.get("minutes_extended")).lower() and left:
        problems.append(f"STOP: 'Continue until done' was chosen and {len(left)} item(s) remain, with no record "
                        "of asking before stopping")

    # 3. CAPTCHA
    asks = " ".join(json.dumps(a) for a in (prog or {}).get("rett_asks") or []).lower()
    for name, it in sf_items + [("pass_state.json", it) for it in ps_items]:
        if it.get("reason") == "captcha":
            dk = str(it.get("docket", "")).split("/")[0].strip().lower()
            if not asks or (dk and dk not in asks and str(it.get("state", "")).lower() not in asks):
                problems.append(f"CAPTCHA: {name}: {it.get('state')} {it.get('docket')} carried as captcha, "
                                "but no rett_asks entry shows Rett was asked")

    # 4. REASONS
    for name, it in sf_items + [("pass_state.json", it) for it in ps_items]:
        if it.get("reason") not in REASONS:
            problems.append(f"REASONS: {name}: {it.get('state')} {it.get('docket')} reason "
                            f"{it.get('reason')!r} is not a step 6 reason")

    # 5. AGREEMENT
    if ps_items:
        psmap = {_key(it): it.get("reason") for it in ps_items}
        for name, it in sf_items:
            k = _key(it)
            if k not in psmap:
                problems.append(f"AGREEMENT: {name} carries {it.get('state')} {it.get('docket')}, "
                                "pass_state.json does not")
            elif psmap[k] != it.get("reason"):
                problems.append(f"AGREEMENT: {it.get('state')} {it.get('docket')} is {it.get('reason')!r} in "
                                f"{name} but {psmap[k]!r} in pass_state.json")

    # 6. COUNTS
    ndocs = sum(len(doc.get("documents") or []) for doc in states.values())
    if states and man.get("documents") != ndocs:
        problems.append(f"COUNTS: manifest documents {man.get('documents')} but the state files hold {ndocs}")
    if ps_items:
        if man.get("carried_forward") != len(ps_items):
            problems.append(f"COUNTS: manifest carried_forward {man.get('carried_forward')} but pass_state.json "
                            f"holds {len(ps_items)}")
        by = {}
        for it in ps_items:
            by[it.get("reason")] = by.get(it.get("reason"), 0) + 1
        if (man.get("carried_forward_by_reason") or {}) != by:
            problems.append(f"COUNTS: carried_forward_by_reason {man.get('carried_forward_by_reason')} "
                            f"but pass_state.json gives {by}")
    return problems, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--manifest")
    ap.add_argument("--now")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    now = _ts(a.now) if a.now else None
    if a.now and now is None:
        print(f"bad --now {a.now!r}", file=sys.stderr)
        return 2
    try:
        problems, notes = check(a.dir, a.run, a.manifest, now)
    except (OSError, ValueError) as e:
        print(f"could not read input: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"run_id": a.run, "ok": not problems, "problems": problems, "notes": notes}, indent=1))
    else:
        print(f"manual pass {a.run}: {'OK' if not problems else 'INCOMPLETE'} "
              f"({len(problems)} problem(s), {len(notes)} note(s))")
        for p in problems:
            print("  PROBLEM " + p)
        for n in notes:
            print("  note    " + n)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
