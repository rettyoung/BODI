"""Tests for tracker/shortlist.py, tracker/brief_input.py and tracker/usage.py (added 2026-11-02).
Run: python tests/test_shortlist.py   (needs pyyaml; uses the repo's own data/ and store/)"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tracker"))
import shortlist  # noqa


def run(*args):
    return subprocess.run([sys.executable] + list(args), capture_output=True, text=True, cwd=ROOT)


def test_excerpt_keeps_cover_and_beat_passages_under_cap():
    long = ("Lorem ipsum filler text. " * 2000)
    text = ("BEFORE THE PUBLIC UTILITY COMMISSION — APPLICATION OF EXAMPLE POWER. " + long +
            " The large load customer shall pay a minimum bill equal to 80% of contract demand of 300 MW. " + long +
            " IT IS THEREFORE ORDERED that the tariff take effect on 2027-01-01. " + long)
    f = {"_path": "x.json", "documents": [{"name": "d1", "quality": "text_layer", "ocr": False, "text": text}]}
    kws, parties, _ = shortlist.load_watch()
    ex = shortlist.excerpt(f, shortlist.word_re(kws), shortlist.word_re(parties), cap=8000)
    assert len(ex) <= 8600, len(ex)
    assert "APPLICATION OF EXAMPLE POWER" in ex, "cover page kept"
    assert "300 MW" in ex and "minimum bill" in ex, "beat passage kept"
    assert "IT IS THEREFORE ORDERED" in ex, "ordering language kept"
    assert "chars ...]" in ex, "gaps are marked"
    assert len(ex) < len(text) / 5


def test_scoring_ranks_watched_order_above_individual_comment():
    kws, parties, dockets = shortlist.load_watch()
    kw_re, party_re = shortlist.word_re(kws), shortlist.word_re(parties)
    d = sorted(dockets)[0]
    order = {"title": "Order approving large load tariff", "docket": d, "source": "x", "kind": "filing", "keywords": ["large load"]}
    comment = {"title": "Comment of Jane Smith in Docket P-1", "docket": "P-1", "source": "ferc", "kind": "keyword_hit",
               "keywords": ["data center"], "entity": "Individual No Affiliation"}
    gov = {"title": "Governor declares flooding disaster", "source": "page:gov_tx", "kind": "news", "keywords": ["emergency"]}
    so, go, _ = shortlist.score(order, kw_re, party_re, dockets)
    sc, _, why = shortlist.score(comment, kw_re, party_re, dockets)
    sg, _, _ = shortlist.score(gov, kw_re, party_re, dockets)
    assert go == "order" and so >= 45
    assert sc < 45 and "individual comment" in why
    assert sg < 45, "a weak keyword alone does not carry a governor's page"


def test_candidates_command_writes_shortlist_and_summary():
    files = sorted(glob.glob(os.path.join(ROOT, "data", "candidates", "*.jsonl")))
    if len(files) < 2:
        print("  (skipped: no candidate files)")
        return
    since = os.path.basename(files[-2])[:10]
    with tempfile.TemporaryDirectory() as tmp:
        out, xd = os.path.join(tmp, "s.json"), os.path.join(tmp, "x")
        r = run("tracker/shortlist.py", "candidates", "--since", since, "--top", "5", "--out", out, "--excerpts", xd)
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip().splitlines()[-1].startswith("SHORTLIST "), r.stdout
        d = json.load(open(out))
        assert len(d["kept"]) <= 5
        assert d["candidates"] == len(d["kept"]) + len(d.get("earnings", [])) + len(d["backlog"]) + len(d["dropped"])
        for k in d["kept"] + d.get("earnings", []):
            assert k.get("excerpt") is None or os.path.exists(k["excerpt"])


def test_backfill_screened_items_never_in_batch():
    if not os.path.exists(os.path.join(ROOT, "data", "backfill", "enriched.jsonl")):
        print("  (skipped: no enriched.jsonl)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        st = os.path.join(tmp, "state.json")
        json.dump({"backfill_cursor": {"done": []}}, open(st, "w"))
        out = os.path.join(tmp, "b.json")
        r = run("tracker/shortlist.py", "backfill", "--state", st, "--n", "10", "--out", out, "--excerpts", os.path.join(tmp, "x"))
        assert r.returncode == 0, r.stderr
        d = json.load(open(out))
        ids = {b["id"] for b in d["batch"]}
        assert not ids & {x["id"] for x in d["screened_out"]}
        assert d["mode"] == "strict" and d["since"] == "2026-01-01"
        assert all((b["filed"] or "") >= "2026-01-01" for b in d["batch"]), "strict mode keeps the 2026 window"
        assert d["remaining_passing"] + len(d["screened_out"]) == d["unprocessed"]
        # done ids are excluded on the next call
        json.dump({"backfill_cursor": {"done": sorted(ids)}}, open(st, "w"))
        r = run("tracker/shortlist.py", "backfill", "--state", st, "--n", "10", "--out", out, "--excerpts", os.path.join(tmp, "x"))
        d2 = json.load(open(out))
        assert not ids & {b["id"] for b in d2["batch"] if not b["refetched"]}


def test_backfill_strict_cuts():
    kws, parties, dockets = shortlist.load_watch()
    kw_re, party_re = shortlist.word_re(kws), shortlist.word_re(parties)
    doc = [{"chars": 1000}]

    def cls(title, filed="2026-05-01", tier=1, party_hits=(), docket="58481", docs=doc):
        c = {"id": "TX:58481-1", "title": title, "filed": filed, "tier": tier, "party_hits": list(party_hits),
             "docket": docket, "docs": docs, "keywords": ["large load"]}
        return shortlist.classify_backfill(c, kw_re, party_re, dockets, "2026-01-01", None), c

    (ok, why, _, _), _ = cls("5/1/2026 | PUC | PL | ORDER APPROVING LARGE LOAD TARIFF", filed="2025-12-01")
    assert not ok and why.startswith("window")
    (ok, why, _, _), _ = cls("SOAH ORDER NO. 5- ADOPTING PROCEDURAL SCHEDULE, SETTING HEARING ON THE MERITS")
    assert not ok and why == "procedural"
    (ok, why, _, _), _ = cls("OPUC'S PROTECTIVE ORDER CERTIFICATIONS", party_hits=["Office of Public Utility Counsel"])
    assert not ok and why == "procedural", "a watched party's procedural paper is still procedural"
    (ok, why, _, _), _ = cls("6/5/2026 | TRAVIS & JENNIFER REPPOND | PL | Direct Testimony", party_hits=["Google"])
    assert not ok and why.startswith("landowner"), "an individual's filing is screened even with a party hit"
    (ok, why, _, _), _ = cls("6/19/2026 | A2 Segment Affected Landowners Coalition | BR | Initial Brief")
    assert not ok and why.startswith("landowner")
    (ok, why, _, disp), c = cls("4/17/2026 | Data Center Coalition (DCC) | COM | Comments on Proposal for Publication",
                                tier=2, party_hits=["Data Center Coalition"])
    assert ok and disp and c["_instr"], "hyperscaler / DCC filings are never collapsed"
    (ok, why, _, disp), c = cls("9/2/2026 | Whitis Land Investments, LP | MISC | Exceptions to the Proposal for Decision", tier=3)
    assert not c.get("_instr"), "exceptions to a PFD are not the PFD"
    (ok, why, _, disp), c = cls("Brief", tier=3, docket="E-01345A-25-0105", party_hits=[],
                                docs=[{"chars": 0, "error": "blocked: robots.txt disallows https://images.edocket.azcc.gov"}])
    assert not ok and why.startswith("no document text")
    (ok, why, _, disp), c = cls("Recommended Opinion and Order", tier=1, docket="E-01345A-25-0105",
                                docs=[{"chars": 0, "error": "blocked: robots.txt"}])
    assert ok and c["_needs_manual"], "an unreadable instrument goes to the manual pass"
    assert shortlist.individual_filer("6/9/2026 | LAUREN PATTERSON | COM | PROTESTOR")
    assert not shortlist.individual_filer("6/8/2026 | ONCOR ELECTRIC DELIVERY COMPANY LLC | PL | Response")
    assert shortlist.individual_filer("Comments of Brian Handshy, JR. addressing proposals to use virtual power plants")


def test_brief_input_on_the_baseline_store():
    with tempfile.TemporaryDirectory() as tmp:
        st = os.path.join(tmp, "store")
        shutil.copytree(os.path.join(ROOT, "store"), st)
        json.dump({"last_brief_date": "2026-09-18", "near_term_milestones": [{"date": "2026-09-20", "item": "x"}]},
                  open(os.path.join(st, "state.json"), "w"))
        out = os.path.join(tmp, "bi.json")
        r = run("tracker/brief_input.py", "--store", st, "--asof", "2026-09-18", "--out", out)
        assert r.returncode == 0, r.stderr
        d = json.load(open(out))
        assert d["counts"]["new_events"] == 0 and d["quiet"] is True, "baseline rows are not this week's news"
        assert d["counts"]["store_rows"] == 229 and d["counts"]["store_events"] == 161
        assert d["milestones"][0]["flag"] == "URGENT"


def test_usage_check():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "r.json")
        json.dump({"run_id": "x"}, open(p, "w"))
        assert run("tracker/usage.py", "--check", p).returncode == 1
        json.dump({"run_id": "x", "usage": {"3": {"ctx_chars": 12000, "sub_chars": 90000, "calls": 4,
                                                   "agents": {"sonnet": 3}}}}, open(p, "w"))
        assert run("tracker/usage.py", "--check", p).returncode == 0
        assert "total" in run("tracker/usage.py", p).stdout


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("ok", name)
    print(f"{n} tests passed")


def test_earnings_lane_takes_tracked_utility_releases_outside_top():
    """2026-11-09: the six 'unreachable' IR issuers' Q3 filings sat behind the --top cut; they get their own lane."""
    iss = shortlist.load_issuers()
    assert {"Exelon", "Evergy", "Southern", "OGE Energy", "Oncor", "Nevada Power", "Sempra"} <= iss
    rel = {"source": "edgar", "entity": "Oncor", "meta": {"form": "8-K", "items": ["2.02", "7.01", "9.01"]}}
    q = {"source": "edgar", "entity": "Southern", "meta": {"form": "10-Q", "items": []}}
    other = {"source": "edgar", "entity": "Oncor", "meta": {"form": "8-K", "items": ["5.02"]}}
    mp = {"source": "edgar", "entity": "Microsoft", "meta": {"form": "8-K", "items": ["2.02"]}}
    assert shortlist.is_earnings(rel, iss) and shortlist.is_earnings(q, iss)
    assert not shortlist.is_earnings(other, iss) and not shortlist.is_earnings(mp, iss)


def test_earnings_excerpt_reaches_the_queue_sentence_past_dollar_figures():
    filler = "Net income was $1.2 billion, up 4% from $1.1 billion. " * 400
    f = {"documents": [{"url": "cover.htm", "text": "FORM 8-K cover page. " * 50},
                       {"url": "ex991.htm", "text": filler + "The queue included approximately 293 gigawatts from data "
                                                             "centers and 19 gigawatts of other load. " + filler}]}
    kw_re, party_re = shortlist.word_re(["large load"]), shortlist.word_re(["Microsoft"])
    plain = shortlist.excerpt(dict(f), kw_re, party_re, cap=8000)
    focused = shortlist.excerpt(dict(f), kw_re, party_re, cap=12000, win=500, focus=shortlist.LOAD_RE)
    assert "293 gigawatts" not in plain
    assert "293 gigawatts" in focused
