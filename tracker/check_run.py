"""Completeness gate for a Sweep run (sweep.md Step 9.3; brief.md Step 2).

The Sweep runs this BEFORE it writes its run record to OneDrive, on a draft of that record; the Brief
runs it again on the record the Sweep wrote. It replaces the run's own judgement of whether it finished
with a mechanical check. A failing check means the run is INCOMPLETE: the run record status must be
"incomplete" and the report and push notification must open with "Sweep incomplete:".

usage:
    python tracker/check_run.py --run RUN.json --obligations obligations.json
                                [--part rows_pN.json] [--store DIR] [--json]

    --part   this run's rows part (omit only if the run wrote none; then steps 8.5 needs no rows check)
    --store  folder holding tariff_terms_p*.json deltas (store_live in the Sweep and the Brief)
exit 0 = complete; 1 = incomplete (problems printed); 2 = could not read an input.

What it fails:
  1. STEPS    the run record has no "steps" block, a required step is missing, or a status is not
              DONE / BLOCKED / NOT_APPLICABLE.
  2. REASONS  BLOCKED or NOT_APPLICABLE without evidence. Evidence is an error, an HTTP status, a refused
              or missing URL or file, a robots/certificate/CAPTCHA refusal — or elapsed time, but only when
              the run actually took over 30 minutes. "deferred", "queued", "skipped", "later", "not started"
              or "time" are choices, not evidence.
  3. OBLIGATIONS  an obligation due on or before the run date that is not done (or blocked with
              evidence); a min_per_run item whose progress for this run is below its quota.
  4. TARIFFS  a row in this run's part that carries tariff or settlement terms whose event is neither in
              an upsert of this run's tariff_terms_pN.json delta nor listed in steps["8.5"]["no_terms"]
              with a reason; or an invalid delta.
  5. HONESTY  the record says "completed" while anything above fails; a report that does not open with
              "Sweep incomplete:" when it should.
"""
import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import subtables  # noqa

# Every step in sweep.md that a run must account for. Keep in step with sweep.md.
REQUIRED_STEPS = {
    "0": "preflight and lock",
    "1": "state and row store",
    "1.6": "obligations due or overdue (before new candidates)",
    "2": "health",
    "3": "collector candidates",
    "4": "mail",
    "5": "manual drops and manual_queue.json",
    "6": "web reader routes",
    "7": "grain, identity, supersession, dedupe",
    "8": "classify",
    "8.5": "metrics and tariff terms (delta)",
    "8.6": "corrections queue",
    "8.7": "C-07 docket-history backfill quota",
    "8.8": "C-08 new-source history quota",
    "9": "commit",
    "10": "collector repair proposals",
    "11": "run record and report",
}
STATUSES = ("DONE", "BLOCKED", "NOT_APPLICABLE")
TARGET_MINUTES = 30

CHOICE_RE = re.compile(r"\b(defer(red|ring)?|queued?|skip(ped|ping)?|postpon\w*|later|next (run|week)|"
                       r"not started|to save|for brevity|optional)\b", re.I)
HARD_RE = re.compile(r"(\b[45]\d\d\b|https?://|\berror\b|exception|refus|denied|\brobots\b|certificate|captcha|"
                     r"not found|no such|missing|does not exist|unreachable|timed? ?out|failed|not reachable|"
                     r"no (file|data|candidates|items|lines)|empty|\b0 (items|lines|candidates|files)\b|"
                     r"degraded|clone failed|not due|first run of (the )?month|none in window|nothing in window)", re.I)
TIME_RE = re.compile(r"\b(time|elapsed|minutes?|budget|deadline|ran long|overrun)\b", re.I)

TERMS_SUBJECTS = {"Large Load Customer Terms"}
TERMS_INSTRUMENTS = {"Tariff", "Settlement / Stipulation"}


def _dur(run):
    if isinstance(run.get("duration_minutes"), (int, float)):
        return float(run["duration_minutes"])
    try:
        f = "%Y-%m-%dT%H:%M:%SZ"
        return (datetime.strptime(run["finished"], f) - datetime.strptime(run["started"], f)).total_seconds() / 60
    except Exception:
        return None


def evidence_problem(text, duration, what):
    """None if `text` is acceptable evidence for BLOCKED / blocked, else the problem."""
    t = (text or "").strip()
    if len(t) < 12:
        return f"{what}: BLOCKED without evidence"
    hard = bool(HARD_RE.search(t))
    timed = bool(TIME_RE.search(t))
    if timed and not hard:
        if duration is None or duration <= TARGET_MINUTES:
            d = "unknown" if duration is None else f"{duration:.0f}"
            return f"{what}: cites time, but the run took {d} of its {TARGET_MINUTES} minutes"
        return None
    if not hard:
        if CHOICE_RE.search(t):
            return f"{what}: the reason is a choice, not evidence ({t[:80]!r})"
        return f"{what}: no evidence (an error, HTTP status, refused or missing URL/file, or time over {TARGET_MINUTES} min)"
    return None


def check_steps(run, duration, probs):
    steps = run.get("steps")
    if not isinstance(steps, dict) or not steps:
        probs.append("STEPS: the run record has no \"steps\" block")
        return {}
    for sid, name in REQUIRED_STEPS.items():
        s = steps.get(sid)
        if not isinstance(s, dict):
            probs.append(f"STEPS: step {sid} ({name}) has no entry")
            continue
        st = s.get("status")
        if st not in STATUSES:
            probs.append(f"STEPS: step {sid} status {st!r} is not one of {'/'.join(STATUSES)}")
            continue
        ev = s.get("evidence") or ""
        if st == "BLOCKED":
            p = evidence_problem(ev, duration, f"REASONS: step {sid}")
            if p:
                probs.append(p)
        elif st == "NOT_APPLICABLE":
            if len(ev.strip()) < 10:
                probs.append(f"REASONS: step {sid} NOT_APPLICABLE without a reason")
            elif CHOICE_RE.search(ev) and not HARD_RE.search(ev):
                probs.append(f"REASONS: step {sid} NOT_APPLICABLE for a reason that is a choice ({ev[:80]!r})")
        if st != "DONE" and sid in ("0", "1", "9", "11"):
            probs.append(f"STEPS: step {sid} ({name}) must be DONE for any run that writes")
    return steps


def check_obligations(obl, run_id, run_date, duration, probs):
    for it in obl.get("items") or []:
        iid, st = it.get("id", "?"), (it.get("status") or "open").lower()
        prog = (it.get("progress") or {}).get(run_id)
        if st == "done":
            continue
        if st == "blocked":
            p = evidence_problem(it.get("evidence"), duration, f"OBLIGATIONS: {iid}")
            if p:
                probs.append(p)
            continue
        due = it.get("due_by")
        if due and due <= run_date:
            probs.append(f"OBLIGATIONS: {iid} was due by {due} and is still {st}")
        q = it.get("min_per_run")
        if q:
            n = prog if isinstance(prog, (int, float)) else (prog or {}).get("n") if isinstance(prog, dict) else None
            if n is None:
                probs.append(f"OBLIGATIONS: {iid} has no progress recorded for {run_id} (quota {q})")
            elif n < q:
                probs.append(f"OBLIGATIONS: {iid} did {n} of its {q} this run")


def terms_events(part):
    cols = part.get("columns")
    if not cols:
        cols = ["Date", "Event ID", "Utility", "Jurisdiction", "Subject", "Venue", "Instrument"]
    ci = {c: i for i, c in enumerate(cols)}
    out = {}
    for r in part.get("data") or []:
        subj, inst = r[ci["Subject"]], r[ci["Instrument"]]
        if subj in TERMS_SUBJECTS or inst in TERMS_INSTRUMENTS:
            out.setdefault(r[ci["Event ID"]], f"{r[ci['Utility']]} {r[ci['Jurisdiction']]} — {subj} / {inst}")
    return out


def check_tariffs(part, store, run_id, steps, probs):
    if part is None:
        return
    need = terms_events(part)
    covered = set()
    if store:
        for p in subtables.delta_files(store):
            d = json.load(open(p, encoding="utf-8"))
            if d.get("run_id") != run_id:
                continue
            for x in subtables.check_delta(d):
                probs.append(f"TARIFFS: {os.path.basename(p)}: {x}")
            for u in d.get("upserts") or []:
                for e in [u.get("event")] + list(u.get("events") or []):
                    if e:
                        covered.add(e)
    no_terms = ((steps or {}).get("8.5") or {}).get("no_terms") or {}
    for eid, desc in sorted(need.items()):
        if eid in covered:
            continue
        why = no_terms.get(eid) if isinstance(no_terms, dict) else None
        if why and len(why.strip()) >= 10 and not (CHOICE_RE.search(why) and not HARD_RE.search(why)):
            continue
        probs.append(f"TARIFFS: {eid} ({desc}) carries tariff or settlement terms but is in no tariff_terms delta "
                     f"for {run_id} and has no reason in steps[\"8.5\"].no_terms")


def check(run, obl, part=None, store=None):
    probs = []
    run_id = run.get("run_id") or ""
    run_date = run_id[:10] or (run.get("started") or "")[:10]
    duration = _dur(run)
    if duration is None:
        probs.append("STEPS: duration unknown (no duration_minutes, started/finished)")
    steps = check_steps(run, duration, probs)
    check_obligations(obl, run_id, run_date, duration, probs)
    check_tariffs(part, store, run_id, steps, probs)
    # anything elsewhere in the record that calls a choice a constraint
    for k in ("corrections_processed",):
        for cid, txt in (run.get(k) or {}).items():
            if isinstance(txt, str) and TIME_RE.search(txt) and not HARD_RE.search(txt) \
                    and duration is not None and duration <= TARGET_MINUTES and re.search(r"not (started|done)", txt, re.I):
                probs.append(f"REASONS: {k}.{cid} blames time, but the run took {duration:.0f} of {TARGET_MINUTES} minutes")
    ok = not probs
    st = (run.get("status") or "").lower()
    if not ok and st == "completed":
        probs.append("HONESTY: the run record says \"completed\" but the run is incomplete")
    rep = run.get("report")
    if not ok and isinstance(rep, str) and not rep.lstrip().startswith("Sweep incomplete:"):
        probs.append("HONESTY: the report does not open with \"Sweep incomplete:\"")
    return {"ok": ok and not probs, "run_id": run_id, "duration_minutes": duration,
            "status_should_be": "completed" if not probs else "incomplete", "problems": probs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--obligations", required=True)
    ap.add_argument("--part")
    ap.add_argument("--store")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        run = json.load(open(a.run, encoding="utf-8"))
        obl = json.load(open(a.obligations, encoding="utf-8"))
        part = json.load(open(a.part, encoding="utf-8")) if a.part else None
    except Exception as e:
        print(f"cannot read input: {e}", file=sys.stderr)
        sys.exit(2)
    res = check(run, obl, part, a.store)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        if res["ok"]:
            print(f"COMPLETE: {res['run_id']}")
        else:
            print(f"Sweep incomplete: {res['run_id']} — {len(res['problems'])} problem(s)")
            for p in res["problems"]:
                print(" - " + p)
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
