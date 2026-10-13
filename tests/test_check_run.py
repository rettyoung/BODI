"""Tests for tracker/check_run.py and tracker/subtables.py.  Run: python tests/test_check_run.py

The central case replays Sweep 2026-10-12-1056 as it ORIGINALLY recorded itself ("completed", C-08
"not started (time)" at 19 minutes, tariff update "queued", no steps block). The checker must fail it,
for each of the reasons Rett found by asking.
"""
import copy
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tracker"))
import check_run  # noqa
import subtables  # noqa

FIX = os.path.join(ROOT, "tests", "fixtures")
RUN_ID = "2026-10-12-1056"
COLS = ["Date", "Event ID", "Utility", "Jurisdiction", "Subject", "Venue", "Instrument", "Document", "Headline",
        "Takeaway", "Status", "Next Milestone", "Next Date", "Materiality", "Confidence", "Appeal", "Superseded",
        "Upfront Costs", "Rates", "Term", "Speed", "Curtailment", "Deliverability", "Supply/Demand",
        "Market Participation", "Source URL"]


def row(eid, util, jur, subj, inst):
    r = [None] * 26
    r[0], r[1], r[2], r[3], r[4], r[5], r[6] = "2026-10-06", eid, util, jur, subj, "State Commission", inst
    return r


PART = {"schema": "grid-docket-rows-part-v1", "run_id": RUN_ID, "columns": COLS, "data": [
    row("E-20261012-002", "Duke", "FERC", "Transmission & Delivery", "Final Order"),
    row("E-20261012-004", "OG&E", "OK", "Large Load Customer Terms", "Application / Petition"),
    row("E-20261012-009", "Dominion", "VA", "Large Load Customer Terms", "Tariff"),
    row("E-20261012-011", "Duke", "NC", "Large Load Customer Terms", "Settlement / Stipulation"),
    row("E-20261012-007", "PJM", "PA", "Commercial Activity", "Contract"),
]}

# Obligations as they stood when that run started (deadlines from corrections_queue.md).
OBL_BEFORE = {"schema": "grid-docket-obligations-v1", "items": [
    {"id": "C-08-triage", "due_by": "2026-10-12", "status": "open", "progress": {}},
    {"id": "C-08-reads", "due_by": "2027-03-31", "min_per_run": 20, "status": "open", "progress": {RUN_ID: 0}},
    {"id": "C-07-baseline-links", "due_by": "2026-10-12", "status": "open", "progress": {}},
    {"id": "C-07-quota", "due_by": "2027-03-31", "min_per_run": 15, "status": "open", "progress": {RUN_ID: 15}},
    {"id": "C-03", "due_by": "2026-10-26", "status": "blocked", "evidence":
        "ACC documents not reachable from the cloud: images.edocket.azcc.gov certificate mismatch; "
        "docket.images.azcc.gov robots-disallowed"},
]}

ORIGINAL_RECORD = {"run_id": RUN_ID, "mode": "FULL", "status": "completed",
                   "started": "2026-10-12T10:56:00Z", "finished": "2026-10-12T11:15:00Z", "duration_minutes": 19,
                   "tariff_terms_changed": "queued",
                   "corrections_processed": {"C-08": "not started (time)", "C-07": "15 items processed"},
                   "report": "Collected 16 events / 18 rows ..."}


def good_steps():
    s = {k: {"status": "DONE", "evidence": ""} for k in check_run.REQUIRED_STEPS}
    s["10"] = {"status": "NOT_APPLICABLE", "evidence": "no collector source failed on 2+ consecutive nights"}
    return s


def good_record():
    r = copy.deepcopy(ORIGINAL_RECORD)
    r.pop("corrections_processed")
    r["steps"] = good_steps()
    r["report"] = "Collected 16 events / 18 rows ..."
    return r


def good_obligations():
    o = copy.deepcopy(OBL_BEFORE)
    for it in o["items"]:
        if it["id"] in ("C-08-triage", "C-07-baseline-links"):
            it["status"] = "done"
        if it["id"] == "C-08-reads":
            it["progress"][RUN_ID] = 20
    return o


LIVE_DUKE_NC = "Duke large load tariff (DEC/DEP, identical) — decided inside E-7 Sub 1329 / E-2 Sub 1380"


def store_with_delta(tmp, delta=True):
    # The repo's store/ is the frozen 2026-09-18 baseline; OneDrive renamed Duke NC's entry on 2026-10-05.
    base = json.load(open(os.path.join(ROOT, "store", "tariff_terms.json"), encoding="utf-8"))
    for e in base["data"]:
        if e["utility"] == "Duke" and e["jurisdiction"] == "NC":
            e["tariff"] = LIVE_DUKE_NC
    json.dump(base, open(os.path.join(tmp, "tariff_terms.json"), "w", encoding="utf-8"), ensure_ascii=False)
    if delta:
        shutil.copy(os.path.join(FIX, "tariff_terms_p1.json"), tmp)
    return tmp


def has(probs, *needles):
    return any(all(n in p for n in needles) for p in probs)


def test_replay_of_12_oct_fails_for_every_reason():
    with tempfile.TemporaryDirectory() as tmp:
        res = check_run.check(ORIGINAL_RECORD, OBL_BEFORE, PART, store_with_delta(tmp, delta=False))
    p = res["problems"]
    assert not res["ok"] and res["status_should_be"] == "incomplete"
    assert has(p, "no \"steps\" block")
    assert has(p, "C-08-triage", "due by 2026-10-12")
    assert has(p, "C-07-baseline-links", "due by 2026-10-12")
    assert has(p, "C-08-reads", "0 of its 20")
    for eid in ("E-20261012-004", "E-20261012-009", "E-20261012-011"):
        assert has(p, "TARIFFS", eid), eid
    assert not has(p, "E-20261012-007") and not has(p, "TARIFFS", "E-20261012-002")
    assert has(p, "C-08", "blames time", "19")
    assert has(p, "HONESTY", "completed")
    assert has(p, "HONESTY", "Sweep incomplete:")
    assert not has(p, "C-03"), "C-03 is blocked with real evidence"


def test_complete_run_passes():
    with tempfile.TemporaryDirectory() as tmp:
        res = check_run.check(good_record(), good_obligations(), PART, store_with_delta(tmp))
    assert res["ok"], res["problems"]


def test_missing_tariff_delta_fails_unless_reason_per_event():
    rec = good_record()
    with tempfile.TemporaryDirectory() as tmp:
        st = store_with_delta(tmp, delta=False)
        assert has(check_run.check(rec, good_obligations(), PART, st)["problems"], "TARIFFS")
        rec["steps"]["8.5"]["no_terms"] = {"E-20261012-004": "queued for next run",
                                           "E-20261012-009": "terms already recorded in tariff_terms_p1, unchanged",
                                           "E-20261012-011": "terms already recorded in tariff_terms_p1, unchanged"}
        p = check_run.check(rec, good_obligations(), PART, st)["problems"]
    assert has(p, "E-20261012-004") and not has(p, "E-20261012-009")


def test_time_is_only_evidence_over_30_minutes():
    rec = good_record()
    rec["steps"]["8.8"] = {"status": "BLOCKED", "evidence": "ran out of time"}
    with tempfile.TemporaryDirectory() as tmp:
        st = store_with_delta(tmp)
        assert has(check_run.check(rec, good_obligations(), PART, st)["problems"], "8.8", "19 of its 30")
        rec["duration_minutes"] = 41
        assert check_run.check(rec, good_obligations(), PART, st)["ok"]


def test_choice_words_are_not_evidence():
    rec = good_record()
    for word in ("deferred to next run", "queued", "skipped to save a write", "not started"):
        rec["steps"]["8.5"] = {"status": "BLOCKED", "evidence": word}
        with tempfile.TemporaryDirectory() as tmp:
            assert has(check_run.check(rec, good_obligations(), PART, store_with_delta(tmp))["problems"], "8.5"), word
    rec["steps"]["8.5"] = {"status": "BLOCKED", "evidence": "OneDrive upload failed: HTTP 503 from Graph"}
    with tempfile.TemporaryDirectory() as tmp:
        assert check_run.check(rec, good_obligations(), PART, store_with_delta(tmp))["ok"]


def test_missing_step_and_bad_status():
    rec = good_record()
    del rec["steps"]["8.6"]
    rec["steps"]["4"] = {"status": "PARTIAL"}
    with tempfile.TemporaryDirectory() as tmp:
        p = check_run.check(rec, good_obligations(), PART, store_with_delta(tmp))["problems"]
    assert has(p, "step 8.6") and has(p, "step 4", "PARTIAL")


def test_incomplete_report_must_say_so():
    rec = good_record()
    rec["status"] = "incomplete"
    rec["steps"]["6"] = {"status": "BLOCKED", "evidence": "nothing"}
    rec["report"] = "Sweep incomplete: step 6 web routes"
    with tempfile.TemporaryDirectory() as tmp:
        p = check_run.check(rec, good_obligations(), PART, store_with_delta(tmp))["problems"]
    assert not has(p, "HONESTY") and has(p, "step 6")


def test_subtables_merge_upserts_and_appends():
    with tempfile.TemporaryDirectory() as tmp:
        st = store_with_delta(tmp)
        base = json.load(open(os.path.join(st, "tariff_terms.json")))
        m = subtables.merge(st)
        assert len(m["data"]) == len(base["data"]) + 2  # OG&E XLPL and Duke FERC are new
        dom = [e for e in m["data"] if e["utility"] == "Dominion" and e["jurisdiction"] == "VA"]
        assert len(dom) == 1 and dom[0]["load_factor_pct"] == 75 and dom[0]["updated_by"] == RUN_ID
        assert m["deltas_applied"][0]["file"] == "tariff_terms_p1.json"
        assert subtables.next_delta_name(st) == "tariff_terms_p2.json"
        # numeric order: p10 applies after p2
        d = json.load(open(os.path.join(FIX, "tariff_terms_p1.json")))
        d2 = copy.deepcopy(d); d2["run_id"] = "r2"; d2["upserts"] = [dict(d["upserts"][1], min_take_pct=90)]
        d10 = copy.deepcopy(d); d10["run_id"] = "r10"; d10["upserts"] = [dict(d["upserts"][1], min_take_pct=70)]
        json.dump(d2, open(os.path.join(st, "tariff_terms_p2.json"), "w"))
        json.dump(d10, open(os.path.join(st, "tariff_terms_p10.json"), "w"))
        dom = [e for e in subtables.merge(st)["data"] if e["utility"] == "Dominion"][0]
        assert dom["min_take_pct"] == 70
        assert subtables.next_delta_name(st) == "tariff_terms_p11.json"


def test_subtables_rename_with_replaces():
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(os.path.join(ROOT, "store", "tariff_terms.json"), tmp)  # old Duke NC name
        d = json.load(open(os.path.join(FIX, "tariff_terms_p1.json")))
        d["upserts"] = [dict(d["upserts"][2], replaces={"utility": "Duke", "jurisdiction": "NC",
                                                        "tariff": "Customer Protection Plus (framework; tariff filing pending)"})]
        json.dump(d, open(os.path.join(tmp, "tariff_terms_p1.json"), "w"))
        m = subtables.merge(tmp)
        duke = [e for e in m["data"] if e["utility"] == "Duke" and e["jurisdiction"] == "NC"]
        assert len(duke) == 1 and duke[0]["tariff"] == LIVE_DUKE_NC and "replaces" not in duke[0]
        assert len(m["data"]) == 10


def test_subtables_rejects_bad_delta():
    assert subtables.check_delta({"schema": "x", "upserts": [{"utility": "A"}]})


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); n += 1; print("ok", name)
    print(f"{n} tests passed")
