"""Append-only sub-tables: tariff terms.

tariff_terms.json is the frozen base table (schema grid-docket-tariff-terms-v1). It is never rewritten.
Each Sweep that learns new or revised tariff terms uploads a small delta, tariff_terms_pN.json
(N = one past the highest existing), with conflictBehavior "fail":

    {"schema": "grid-docket-tariff-terms-delta-v1", "run_id": "...", "written": "YYYY-MM-DD",
     "upserts": [ {<full tariff entry, same fields as the base table's data[] entries>}, ... ]}

An upsert replaces the whole entry with the same key (utility, jurisdiction, tariff) — compared
case-insensitively with whitespace collapsed — or appends a new one. To RENAME a tariff (its name in the
table changes), the upsert carries "replaces": {"utility", "jurisdiction", "tariff"} naming the old entry;
without it a renamed tariff would appear twice. Deltas apply in numeric order,
so a later run always wins. A null in an upsert means "not stated in what was read"; the delta must
therefore carry every field it knows, not only the changed ones.

usage:
    python tracker/subtables.py merge STORE_DIR [--out FILE]      # print or write the merged table
    python tracker/subtables.py next STORE_DIR                    # next delta file name
    python tracker/subtables.py check DELTA_FILE                  # validate one delta
"""
import argparse
import glob
import json
import os
import re
import sys

BASE = "tariff_terms.json"
DELTA_RE = re.compile(r"^tariff_terms_p(\d+)\.json$")
DELTA_SCHEMA = "grid-docket-tariff-terms-delta-v1"
REQUIRED = ("utility", "jurisdiction", "tariff", "status", "conf")
CONF = ("Verified", "Reported", "Unverified")


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def key(entry):
    return (_norm(entry.get("utility")), _norm(entry.get("jurisdiction")), _norm(entry.get("tariff")))


def delta_files(store):
    """Delta paths in numeric order (p2 before p10)."""
    found = []
    for p in glob.glob(os.path.join(store, "tariff_terms_p*.json")):
        m = DELTA_RE.match(os.path.basename(p))
        if m:
            found.append((int(m.group(1)), p))
    return [p for _, p in sorted(found)]


def next_delta_name(store):
    files = delta_files(store)
    n = max((int(DELTA_RE.match(os.path.basename(p)).group(1)) for p in files), default=0)
    return f"tariff_terms_p{n + 1}.json"


def check_delta(delta):
    """Problems with one delta object (empty list = valid)."""
    probs = []
    if delta.get("schema") != DELTA_SCHEMA:
        probs.append(f"schema is {delta.get('schema')!r}, expected {DELTA_SCHEMA!r}")
    if not delta.get("run_id"):
        probs.append("run_id missing")
    ups = delta.get("upserts")
    if not isinstance(ups, list) or not ups:
        probs.append("upserts missing or empty")
        return probs
    seen = set()
    for i, u in enumerate(ups):
        for f in REQUIRED:
            if u.get(f) in (None, ""):
                probs.append(f"upserts[{i}] lacks {f}")
        if u.get("conf") not in CONF:
            probs.append(f"upserts[{i}] conf {u.get('conf')!r} not in {CONF}")
        if not u.get("source_url") and not u.get("event"):
            probs.append(f"upserts[{i}] needs source_url or event")
        if u.get("replaces") is not None and not all(u["replaces"].get(f) for f in ("utility", "jurisdiction", "tariff")):
            probs.append(f"upserts[{i}] replaces needs utility, jurisdiction and tariff")
        k = key(u)
        if k in seen:
            probs.append(f"upserts[{i}] repeats key {k}")
        seen.add(k)
    return probs


def merge(store):
    """Base table with every delta applied. Returns the merged object (base schema)."""
    base = json.load(open(os.path.join(store, BASE), encoding="utf-8"))
    data = list(base.get("data") or [])
    index = {key(e): i for i, e in enumerate(data)}
    applied = []
    for path in delta_files(store):
        d = json.load(open(path, encoding="utf-8"))
        probs = check_delta(d)
        if probs:
            raise ValueError(f"{os.path.basename(path)}: " + "; ".join(probs))
        for u in d["upserts"]:
            entry = dict(u)
            entry.setdefault("updated_by", d["run_id"])
            old = entry.pop("replaces", None)
            k = key(entry)
            if old and key(old) in index and k not in index:
                index[k] = index.pop(key(old))
            if k in index:
                data[index[k]] = entry
            else:
                index[k] = len(data)
                data.append(entry)
        applied.append({"file": os.path.basename(path), "run_id": d["run_id"], "upserts": len(d["upserts"])})
    out = dict(base)
    out["data"] = data
    out["deltas_applied"] = applied
    if applied:
        out["generated"] = max([base.get("generated") or ""] +
                               [json.load(open(p, encoding="utf-8")).get("written") or "" for p in delta_files(store)])
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge"); m.add_argument("store"); m.add_argument("--out")
    n = sub.add_parser("next"); n.add_argument("store")
    c = sub.add_parser("check"); c.add_argument("delta")
    a = ap.parse_args()
    if a.cmd == "merge":
        merged = merge(a.store)
        txt = json.dumps(merged, ensure_ascii=False, indent=1)
        if a.out:
            open(a.out, "w", encoding="utf-8").write(txt)
            print(json.dumps({"tariffs": len(merged["data"]), "deltas_applied": merged["deltas_applied"]}))
        else:
            print(txt)
    elif a.cmd == "next":
        print(next_delta_name(a.store))
    else:
        probs = check_delta(json.load(open(a.delta, encoding="utf-8")))
        print(json.dumps({"ok": not probs, "problems": probs}))
        sys.exit(1 if probs else 0)


if __name__ == "__main__":
    main()
