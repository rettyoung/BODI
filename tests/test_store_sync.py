"""Tests for tracker/store_sync.py (byte-exact store loading).  Run: python tests/test_store_sync.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tracker"))
import store_sync  # noqa

SS = [sys.executable, os.path.join(ROOT, "tracker", "store_sync.py")]
STORE = os.path.join(ROOT, "store")


def run(*args):
    return subprocess.run(SS + list(args), capture_output=True, text=True)


def make_store(tmp):
    """A store like OneDrive's: the frozen baseline parts plus a manifest, a run record and a manual manifest."""
    d = os.path.join(tmp, "src")
    os.makedirs(os.path.join(d, "runs"))
    os.makedirs(os.path.join(d, "manual"))
    for f in ("rows.json", "rows_p1.json", "rows_p2.json", "rows_p3.json", "rows_p4.json", "metrics.json",
              "tariff_terms.json"):
        shutil.copy(os.path.join(STORE, f), d)
    open(os.path.join(d, "state.json"), "w").write('{"last_brief_date": "2026-10-12"}\n')
    open(os.path.join(d, "obligations.json"), "w").write('{"items": []}\n')
    for i, rid in enumerate(["2026-10-03-0019", "2026-10-05-1055", "2026-10-12-1056", "2026-10-19-1056",
                             "2026-10-26-1056"]):
        open(os.path.join(d, "runs", rid + ".json"), "w").write(json.dumps({"run_id": rid}) + "\n")
    open(os.path.join(d, "manual", "manual_2026-10-09-1619.json"), "w").write('{"complete": true}\n')
    open(os.path.join(d, "manual", "manual_2026-10-09-1619_VA.json"), "w").write('{"x": 1}\n')
    return d


def listing_text(d, sub=""):
    base = os.path.join(d, sub) if sub else d
    lines = []
    for f in sorted(os.listdir(base)):
        p = os.path.join(base, f)
        kind = "folder" if os.path.isdir(p) else "file"
        size = 0 if kind == "folder" else os.path.getsize(p)
        lines.append(f"{f} ({kind}, {size} bytes) file:///drive/{f}")
    return "\n".join(lines)


def test_round_trip_verifies_and_flags_changes():
    with tempfile.TemporaryDirectory() as tmp:
        src = make_store(tmp)
        assert run("manifest", src, "--by", "test").returncode == 0
        man = json.load(open(os.path.join(src, "store_manifest.json")))
        assert "manual/manual_2026-10-09-1619.json" in man["files"]
        assert "manual/manual_2026-10-09-1619_VA.json" not in man["files"], "per-state manual files are not mirrored"
        # listing as the connector prints it (top level, runs/, manual/)
        lst = os.path.join(tmp, "listing.json")
        for sub, pre in (("", ""), ("runs", "runs/"), ("manual", "manual/")):
            t = os.path.join(tmp, f"l{sub}.txt")
            open(t, "w").write(listing_text(src, sub))
            r = run("listing", t, "--prefix", pre, "--out", lst)
            assert r.returncode == 0, r.stderr
        # the mirror as Artifact read saves it: <out_dir>/store/<rel>
        saved = os.path.join(tmp, "saved", "store")
        shutil.copytree(src, saved)
        dest = os.path.join(tmp, "store_live")
        assert run("collect", os.path.join(tmp, "saved"), dest).returncode == 0
        shutil.copy(os.path.join(src, "store_manifest.json"), os.path.join(dest, "_onedrive_manifest.json"))
        r = run("verify", dest, "--listing", lst, "--manifest", os.path.join(dest, "_onedrive_manifest.json"))
        assert r.returncode == 0, r.stdout + r.stderr

        # 1. same-size change on OneDrive (the Brief's last_brief_date edit) is caught by the hash
        open(os.path.join(dest, "state.json"), "w").write('{"last_brief_date": "2026-10-05"}\n')
        r = run("verify", dest, "--listing", lst, "--manifest", os.path.join(dest, "_onedrive_manifest.json"))
        assert r.returncode == 1 and "FETCH state.json" in r.stdout and "HASH" in r.stdout, r.stdout
        assert "CRITICAL" in r.stdout

        # 2. a missing part and an old run record: the part must be fetched, the oldest run record need not be
        os.remove(os.path.join(dest, "rows_p2.json"))
        os.remove(os.path.join(dest, "runs", "2026-10-03-0019.json"))
        r = run("verify", dest, "--listing", lst, "--manifest", os.path.join(dest, "_onedrive_manifest.json"),
                "--json")
        v = json.loads(r.stdout)
        assert "rows_p2.json" in v["fetch"] and "rows_p2.json" in v["critical"]
        assert "runs/2026-10-03-0019.json" not in v["fetch"], "only the newest four run records are required"


def test_extract_saved_result_is_exact():
    with tempfile.TemporaryDirectory() as tmp:
        body = '{"a": "§ — \\n é"}\n'
        saved = os.path.join(tmp, "toolu.json")
        json.dump([{"type": "text", "text": body}], open(saved, "w"))
        out = os.path.join(tmp, "x.json")
        n = len(body.encode("utf-8"))
        assert run("extract", saved, out, "--bytes", str(n)).returncode == 0
        assert open(out, "rb").read() == body.encode("utf-8")
        assert run("extract", saved, out, "--bytes", str(n + 1)).returncode == 1


def test_check_restores_the_dropped_newline_only():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "m.json")
        open(p, "w").write('{"k": 1}')                      # retyped from an inline read: newline lost
        assert run("check", p, "--bytes", "9").returncode == 0
        assert open(p).read() == '{"k": 1}\n'
        open(p, "w").write('{"k": 12}')                     # a real transcription difference is not papered over
        assert run("check", p, "--bytes", "8").returncode == 1


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("ok", name)
    print(f"{n} tests passed")
