"""Tests for tracker/manual_check.py.  Run: python tests/test_manual_check.py

The central case replays manual pass 2026-11-06-1945 as it recorded itself: Rett chose "Continue until
done", the run stopped with 26 items left without asking, minutes_used null, a "finished" time 77 minutes
after the moment it was written, no progress file, and four Ohio items labelled "captcha" in the state file
but "time" in pass_state.json. The checker must fail it for each of those. A clean run must pass.
"""
import copy
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tracker"))
import manual_check  # noqa
from manual_check import _ts  # noqa

OH = "26-0963-EL-BLN / 26-0914-EL-BTX / 26-0894-EL-BLN / 26-0922-EL-BLN"


def item(state, docket, reason, first="2026-10-09-1619"):
    return {"state": state, "docket": docket, "what": "x", "url": "https://example.invalid/", "reason": reason,
            "first_queued": first}


def morning():
    """2026-11-06-1945, reduced to what the checker reads (counts and reasons as recorded)."""
    run = "2026-11-06-1945"
    ps_items = [item("OH", OH, "time"), item("IL", "26-0364", "time"), item("VA", "PUR-2026-00044", "not_yet_filed")]
    ps = {"schema": "grid-docket-pass-state-v1", "updated_by_run": run, "carry_forward": ps_items}
    states = {
        f"manual_{run}_OH.json": {"schema": "grid-docket-manual-v1", "run_id": run, "state": "OH",
                                  "documents": [{"docket": "26-0959-EL-BLN"}],
                                  "carry_forward": [item("OH", OH, "captcha")]},
        f"manual_{run}_IL.json": {"schema": "grid-docket-manual-v1", "run_id": run, "state": "IL",
                                  "documents": [{"docket": "26-0364"}], "carry_forward": [item("IL", "26-0364", "time")]},
        f"manual_{run}_VA.json": {"schema": "grid-docket-manual-v1", "run_id": run, "state": "VA",
                                  "documents": [{"docket": "PUR-2026-00131"}],
                                  "carry_forward": [item("VA", "PUR-2026-00044", "not_yet_filed")]},
    }
    man = {"schema": "grid-docket-manual-v1", "run_id": run, "complete": True, "finished": "2026-11-06T22:30:00Z",
           "files": sorted(states), "documents": 22, "carried_forward": 26,
           "carried_forward_by_reason": {"not_yet_filed": 4, "partial_read": 3, "time": 9, "not_attempted": 8,
                                         "not_located": 1, "render_failure": 1},
           "budget": {"minutes_budget": 60, "minutes_extended": "Rett chose 'Continue until done'",
                      "minutes_used": None, "deferred_total": 26, "deferred_resolved_in_catchup": None,
                      "stopped_by": "claude_stopped_early_items_remain"}}
    return run, man, None, ps, states


def clean():
    run = "2026-11-13-1704"
    ps_items = [item("OH", OH, "captcha", run)]
    watch = [{"state": "VA", "docket": "PUR-2026-00044", "what": "final order", "url": "https://example.invalid/",
              "expected": "after briefs", "first_queued": "2026-11-06-1945"}]
    ps = {"schema": "grid-docket-pass-state-v1", "updated_by_run": run, "carry_forward": ps_items,
          "watching": watch}
    states = {
        f"manual_{run}_VA.json": {"run_id": run, "state": "VA", "documents": [{"docket": "a"}, {"docket": "b"}],
                                  "carry_forward": [], "watching": copy.deepcopy(watch)},
        f"manual_{run}_OH.json": {"run_id": run, "state": "OH", "documents": [{"docket": "c"}],
                                  "carry_forward": [item("OH", OH, "captcha", run)]},
    }
    prog = {"schema": "grid-docket-manual-progress-v1", "run_id": run, "started": "2026-11-13T17:04:00Z",
            "extensions": [{"at": "2026-11-13T18:04:00Z", "choice": "Continue until done"}],
            "rett_asks": [{"at": "2026-11-13T17:10:00Z", "items": ["OH 26-0963 View Document"],
                           "answer": "Rett away; not cleared"}],
            "stop": {"at": "2026-11-13T18:40:00Z", "reason": "list empty except waiting items", "asked": False}}
    man = {"schema": "grid-docket-manual-v1", "run_id": run, "complete": True, "finished": "2026-11-13T18:41:00Z",
           "files": sorted(states), "documents": 3, "carried_forward": 1,
           "carried_forward_by_reason": {"captcha": 1}, "watching": 1,
           "budget": {"minutes_budget": 60, "minutes_extended": "until done", "minutes_used": 97,
                      "deferred_total": 2, "deferred_resolved_in_catchup": 5, "stopped_by": "list_empty"}}
    return run, man, prog, ps, states


def write(case):
    run, man, prog, ps, states = case
    d = tempfile.mkdtemp(prefix="mc_")
    json.dump(man, open(os.path.join(d, f"manual_{run}.json"), "w"))
    if prog is not None:
        json.dump(prog, open(os.path.join(d, f"progress_{run}.json"), "w"))
    if ps is not None:
        json.dump(ps, open(os.path.join(d, "pass_state.json"), "w"))
    for name, doc in states.items():
        json.dump(doc, open(os.path.join(d, name), "w"))
    return d, run


def run_check(case, now):
    d, run = write(case)
    try:
        return manual_check.check(d, run, now=_ts(now))
    finally:
        shutil.rmtree(d)


def has(problems, prefix, text=""):
    return any(p.startswith(prefix) and text in p for p in problems)


def test_morning_run_fails_for_each_fault():
    # The manifest was written at about 21:13Z (its finish time claimed 22:30Z).
    problems, notes = run_check(morning(), "2026-11-06T21:13:00Z")
    assert has(problems, "CLOCK:", "minutes_used is None"), problems
    assert has(problems, "CLOCK:", "later than now"), problems
    assert has(problems, "STOP:", "not one of"), problems
    assert has(problems, "STOP:", "until done"), problems
    assert has(problems, "CAPTCHA:", "26-0963"), problems
    assert has(problems, "AGREEMENT:", "'captcha'"), problems
    assert has(problems, "COUNTS:", "carried_forward 26"), problems
    assert has(problems, "COUNTS:", "documents 22"), problems
    assert any("no progress_" in n for n in notes), notes  # before 2026-11-07: a note, not a failure


def test_clean_run_passes():
    problems, notes = run_check(clean(), "2026-11-13T19:00:00Z")
    assert problems == [], problems


def test_list_empty_with_skipped_items_fails():
    case = clean()
    case[3]["carry_forward"].append(item("IL", "26-0364", "time"))
    case[4][f"manual_{case[0]}_VA.json"]["carry_forward"].append(item("IL", "26-0364", "time"))
    case[1]["carried_forward"] = 3
    case[1]["carried_forward_by_reason"]["time"] = 1
    problems, _ = run_check(case, "2026-11-13T19:00:00Z")
    assert has(problems, "STOP:", "list_empty but 1"), problems
    assert has(problems, "STOP:", "continue until done"), problems


def test_session_limit_needs_a_stop_record_and_ask():
    case = clean()
    case[1]["budget"]["stopped_by"] = "session_limit"
    del case[2]["stop"]
    case[3]["carry_forward"].append(item("WV", "26-0075-E-CN", "time"))
    case[4][f"manual_{case[0]}_VA.json"]["carry_forward"].append(item("WV", "26-0075-E-CN", "time"))
    case[1]["carried_forward"] = 2
    case[1]["carried_forward_by_reason"]["time"] = 1
    problems, _ = run_check(case, "2026-11-13T19:00:00Z")
    assert has(problems, "STOP:", "no stop record"), problems
    case[2]["stop"] = {"at": "2026-11-13T18:40:00Z", "reason": "session nearly full", "asked": True,
                       "answer": "Finish and resume in a new session"}
    problems, _ = run_check(case, "2026-11-13T19:00:00Z")
    assert problems == [], problems


def test_progress_file_required_from_7_november():
    case = clean()
    problems, _ = run_check((case[0], case[1], None, case[3], case[4]), "2026-11-13T19:00:00Z")
    assert has(problems, "CLOCK:", "no progress_"), problems


def test_minutes_must_match_the_clock():
    case = clean()
    case[1]["budget"]["minutes_used"] = 40
    problems, _ = run_check(case, "2026-11-13T19:00:00Z")
    assert has(problems, "CLOCK:", "does not match"), problems


def test_unknown_reason_fails():
    case = clean()
    case[3]["carry_forward"].append(item("VA", "PUR-2026-00044", "later"))
    case[4][f"manual_{case[0]}_VA.json"]["carry_forward"].append(item("VA", "PUR-2026-00044", "later"))
    case[1]["carried_forward"] = 2
    case[1]["carried_forward_by_reason"] = {"later": 1, "captcha": 1}
    problems, _ = run_check(case, "2026-11-13T19:00:00Z")
    assert has(problems, "REASONS:", "'later'"), problems


def test_cli_exit_codes():
    d, run = write(clean())
    try:
        assert manual_check.main(["--dir", d, "--run", run, "--now", "2026-11-13T19:00:00Z"]) == 0
        assert manual_check.main(["--dir", d, "--run", "1999-01-01-0000"]) == 2
    finally:
        shutil.rmtree(d)
    d, run = write(morning())
    try:
        assert manual_check.main(["--dir", d, "--run", run, "--now", "2026-11-06T21:13:00Z", "--json"]) == 1
    finally:
        shutil.rmtree(d)


def test_watch_list_rules():
    """From 2026-11-07-2100: not_yet_filed lives in watching, never in carry_forward (7 Nov fix)."""
    run, man, prog, ps, states = copy.deepcopy(clean())
    ps["carry_forward"].append(item("NC", "E-7 Sub 1329", "not_yet_filed"))
    probs, _ = manual_check.check(*write((run, man, prog, ps, states)), now=_ts("2026-11-13T19:00:00Z"))
    assert has(probs, "WATCH", "E-7 Sub 1329"), probs
    run, man, prog, ps, states = copy.deepcopy(clean())
    man["watching"] = 4
    probs, _ = manual_check.check(*write((run, man, prog, ps, states)), now=_ts("2026-11-13T19:00:00Z"))
    assert has(probs, "COUNTS", "watching"), probs
    run, man, prog, ps, states = copy.deepcopy(clean())
    ps["watching"] = []
    man["watching"] = 0
    probs, _ = manual_check.check(*write((run, man, prog, ps, states)), now=_ts("2026-11-13T19:00:00Z"))
    assert has(probs, "WATCH", "PUR-2026-00044"), probs
    run, man, prog, ps, states = copy.deepcopy(clean())
    del man["watching"]
    probs, _ = manual_check.check(*write((run, man, prog, ps, states)), now=_ts("2026-11-13T19:00:00Z"))
    assert has(probs, "WATCH", "no watching"), probs


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except AssertionError as e:
                fails += 1
                print("FAIL", name, e)
    sys.exit(1 if fails else 0)
