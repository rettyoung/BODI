"""Tests for tracker/ir_ledger.py (added 2026-11-09).  Run: python tests/test_ir_ledger.py"""
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tracker"))
import ir_ledger  # noqa


def test_quarter_arithmetic():
    assert ir_ledger.current_quarter(dt.date(2026, 11, 9)) == "2026Q3"
    assert ir_ledger.current_quarter(dt.date(2027, 1, 10)) == "2026Q3"   # Q4 season not begun (ended < 20 days ago)
    assert ir_ledger.current_quarter(dt.date(2027, 2, 15)) == "2026Q4"
    assert ir_ledger.quarter_end("2026Q4") == dt.date(2026, 12, 31)


def test_watchlist_covers_the_six_with_the_right_expectations():
    spec = {s["issuer"]: s for s in ir_ledger.load_watch()}
    assert {"Southern", "Evergy", "Exelon", "OGE Energy", "Oncor", "BHE"} <= set(spec)
    assert spec["Oncor"]["expect"] == "release" and "Sempra" in spec["Oncor"]["edgar"]
    assert spec["BHE"]["expect"] == "10q" and spec["BHE"]["edgar"] == ["Nevada Power"]
    assert spec["Exelon"]["deck"] == "edgar"
    assert "investor.oge.com" in spec["OGE Energy"]["deck_url"]


def test_read_map_closes_an_issuer_and_the_obligation_carries_it():
    if not os.path.isdir(os.path.join(ROOT, "data", "candidates")):
        print("  (skipped: no candidate files)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        obl = os.path.join(tmp, "o.json")
        json.dump({"items": [{"id": "IR-2026Q3", "status": "open", "read": {"Oncor": {"acc": "0001193125-26-448721"}}}]},
                  open(obl, "w"))
        out = os.path.join(tmp, "l.json")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tracker", "ir_ledger.py"), "--quarter", "2026Q3",
                            "--today", "2026-11-09", "--obligations", obl, "--out", out],
                           capture_output=True, text=True, cwd=ROOT)
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip().splitlines()[-1].startswith("IR LEDGER 2026Q3")
        d = json.load(open(out))
        st = {x["issuer"]: x["status"] for x in d["issuers"]}
        assert st["Oncor"] == "READ"
        assert d["obligation"]["id"] == "IR-2026Q3" and d["obligation"]["due_by"] == "2026-12-14"
        assert d["obligation"]["read"]["Oncor"]["acc"] == "0001193125-26-448721"


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); n += 1; print("ok", name)
    print(f"{n} tests passed")
