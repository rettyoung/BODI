"""Byte-exact loading of the OneDrive row store into store_live/ (sweep.md 1.3, brief.md 0.3).

Why this exists. A scheduled run reaches OneDrive only through the Microsoft 365 connector. A file read
over ~50 KB is saved to disk by the harness (exact bytes); a smaller one comes back inline, and the only way
to put it on disk is to retype it — slow, costly, and on 12 Oct it silently dropped fields. So:

  * Every run that writes store files to OneDrive also writes /GridDocket/store_manifest.json (small: bytes
    and a 16-hex sha256 prefix per file) and publishes byte-exact copies of the same files to the private
    STORE MIRROR artifact (MIRROR_URL below). OneDrive stays the system of record; the mirror is transport.
  * A loader reads the OneDrive folder listings (exact sizes) and store_manifest.json, fetches the mirror
    (Artifact read saves every file to disk), and VERIFIES each file against both. Only files that fail
    are read from OneDrive — large ones via the saved tool result (`extract`), small ones retyped and then
    checked against the listing size (`check`). Nothing is ever parsed and re-dumped.

usage
  python tracker/store_sync.py listing LISTING.txt [--prefix runs/] [--out store_live/_listing.json]
        Parse a read_resource folder listing ("name (file, N bytes) file:///…" lines, or a saved tool
        result holding them) into {name: {bytes, uri}}; repeated calls merge into --out.
  python tracker/store_sync.py collect SRC_DIR DEST_DIR
        Copy the mirror files Artifact read saved under SRC_DIR (…/store/…) into DEST_DIR, preserving
        runs/ and manual/ subfolders.
  python tracker/store_sync.py verify DEST_DIR [--listing store_live/_listing.json]
                                     [--manifest store_live/_onedrive_manifest.json] [--json]
        Every store file OneDrive lists is checked: present, bytes == listing, and (when the OneDrive
        manifest has it at the same size) sha16 == manifest. Prints FETCH lines for every file to read
        from OneDrive. exit 0 = all verified; 1 = files to fetch; 2 = bad input.
  python tracker/store_sync.py extract SAVED_RESULT DEST_FILE [--bytes N]
        Write the exact text of a saved read_resource result (a JSON list of {"type":"text","text":…}
        blocks, or a plain file) to DEST_FILE. With --bytes, fail unless the size matches.
  python tracker/store_sync.py check FILE --bytes N
        For a retyped small file: exit 0 only if its size is exactly N bytes (the OneDrive listing size).
  python tracker/store_sync.py manifest DIR --by RUN_OR_BRIEF_ID [--out DIR/store_manifest.json]
        Write the manifest for every store file in DIR (top level, runs/, manual/ manifests).
  python tracker/store_sync.py files DIR
        Print the `files` map for an Artifact publish to the mirror: {"store/<rel>": "<DIR>/<rel>", …}.
  python tracker/store_sync.py sizes DIR
        Print "<name> <bytes>" per store file: the expectedBytes for each OneDrive upload.
"""
import argparse
import fnmatch
import glob
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone

MIRROR_URL = "https://claude.ai/artifact/GiAXCPsEF9zoeT5A8dQjVG"
SCHEMA = "grid-docket-store-manifest-v1"
MANIFEST = "store_manifest.json"

# Store files that are mirrored and verified. Anything else in /GridDocket/ (README, backfill_state,
# sweep_lock, manual_queue read as data) is not part of a build.
TOP = ["rows.json", "rows_p*.json", "state.json", "metrics.json", "tariff_terms.json",
       "tariff_terms_p*.json", "obligations.json", "seen_index.json", "manual_queue.json"]
SUB = {"runs/": ["*.json"],
       # only the manual-pass MANIFESTS (no state suffix); the per-state files are read as data by the Sweep
       "manual/": ["manual_*.json"]}
MANUAL_MANIFEST_RE = re.compile(r"^manual_[^_]+\.json$")
# Files a build cannot do without. A failure on one of these stops the run (sweep I1 / brief I1).
CRITICAL = ["rows.json", "rows_p*.json", "state.json", "obligations.json"]

# One entry per "name (file|folder, N bytes) file:///<driveId>/<itemId>". The connector sometimes prints the
# entries one per line and sometimes runs them together with no separator (seen 13 Oct), so entries are not
# anchored to line starts: a Graph item id is always "01" + 32 upper-case letters/digits, which is where the
# previous entry ends and the next name begins.
LIST_RE = re.compile(r"(?P<name>[^\n()]+?)\s+\((?P<kind>file|folder),\s*(?P<bytes>\d+)\s+bytes\)"
                     r"(?:[ \t]*(?P<uri>file:///[^/\s]+/01[0-9A-Z]{32}))?")


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def is_store(rel):
    for pre, pats in SUB.items():
        if rel.startswith(pre):
            base = rel[len(pre):]
            if "/" in base or not any(fnmatch.fnmatch(base, p) for p in pats):
                return False
            return pre != "manual/" or bool(MANUAL_MANIFEST_RE.match(base))
    return "/" not in rel and any(fnmatch.fnmatch(rel, p) for p in TOP)


def is_critical(rel):
    return "/" not in rel and any(fnmatch.fnmatch(rel, p) for p in CRITICAL)


def store_files(d):
    out = []
    for root, _, files in os.walk(d):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), d).replace(os.sep, "/")
            if is_store(rel):
                out.append(rel)
    return sorted(out)


def read_text_blocks(path):
    """Exact text of a saved tool result: a JSON list of content blocks, or the raw file."""
    raw = open(path, "rb").read()
    try:
        d = json.loads(raw.decode("utf-8"))
        if isinstance(d, list) and d and all(isinstance(x, dict) and "type" in x for x in d):
            return "".join(x.get("text", "") for x in d if x.get("type") == "text").encode("utf-8")
        if isinstance(d, dict) and isinstance(d.get("content"), list):
            return "".join(x.get("text", "") for x in d["content"] if x.get("type") == "text").encode("utf-8")
    except Exception:
        pass
    return raw


# ---------------------------------------------------------------- commands

def cmd_listing(a):
    text = read_text_blocks(a.listing).decode("utf-8", "replace")
    cur = {}
    if a.out and os.path.exists(a.out):
        cur = json.load(open(a.out, encoding="utf-8"))
    n = 0
    for m in LIST_RE.finditer(text):
        if m.group("kind") != "file":
            continue
        cur[a.prefix + m.group("name").strip()] = {"bytes": int(m.group("bytes")), "uri": m.group("uri")}
        n += 1
    if not n:
        print("no 'name (file, N bytes)' lines found", file=sys.stderr)
        sys.exit(2)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(cur, open(a.out, "w", encoding="utf-8"), indent=1, sort_keys=True)
    print(f"{n} files listed under '{a.prefix or '/'}'" + (f" -> {a.out}" if a.out else ""))


def cmd_collect(a):
    src = a.src
    # Artifact read saves published paths under its out_dir; the mirror publishes them under store/.
    if os.path.isdir(os.path.join(src, "store")):
        src = os.path.join(src, "store")
    n = 0
    for rel in store_files(src):
        dst = os.path.join(a.dest, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(src, rel), dst)
        n += 1
    if os.path.exists(os.path.join(src, MANIFEST)):
        shutil.copyfile(os.path.join(src, MANIFEST), os.path.join(a.dest, "_mirror_manifest.json"))
    print(f"collected {n} files from {src} into {a.dest}")


def verify(dest, listing, manifest, keep_runs=4):
    """-> (results, fetch) where results: {rel: (state, detail)}. Only the newest `keep_runs` run records
    are required (the Brief's status check reads the last four; the checker reads the newest)."""
    files = (manifest or {}).get("files") or {}
    res, fetch = {}, []
    names = sorted(set(listing) if listing else set(files))
    runs = sorted(r for r in names if r.startswith("runs/"))
    skip = set(runs[:-keep_runs]) if keep_runs and len(runs) > keep_runs else set()
    for rel in names:
        if not is_store(rel) or rel in skip:
            continue
        p = os.path.join(dest, rel)
        want = (listing or {}).get(rel, {}).get("bytes")
        if want is None:
            want = files.get(rel, {}).get("bytes")
        if not os.path.exists(p):
            res[rel] = ("MISSING", "not in the mirror copy")
            fetch.append(rel)
            continue
        got = os.path.getsize(p)
        if want is not None and got != want:
            res[rel] = ("SIZE", f"{got} bytes here, {want} on OneDrive")
            fetch.append(rel)
            continue
        m = files.get(rel)
        if m and m.get("bytes") == got:
            s = sha16(p)
            if s != m.get("sha16"):
                res[rel] = ("HASH", f"sha16 {s} here, {m.get('sha16')} in the OneDrive manifest")
                fetch.append(rel)
                continue
            res[rel] = ("OK", "bytes and hash")
        elif m:
            # OneDrive file changed after the manifest was written (e.g. a run that died before writing it)
            res[rel] = ("SIZE", f"manifest says {m.get('bytes')} bytes, OneDrive lists {want}")
            fetch.append(rel)
        else:
            res[rel] = ("OK_SIZE", "bytes match the listing; not in the manifest")
    # every part the manifest of rows names must be present
    rj = os.path.join(dest, "rows.json")
    if os.path.exists(rj) and res.get("rows.json", ("",))[0] in ("OK", "OK_SIZE"):
        try:
            for part in json.load(open(rj, encoding="utf-8")).get("parts") or []:
                f = part.get("file")
                if f and f not in res:
                    res[f] = ("MISSING", "named in rows.json but not listed or copied")
                    fetch.append(f)
        except Exception as e:  # noqa
            res["rows.json"] = ("BAD", f"does not parse: {e}")
            fetch.append("rows.json")
    return res, sorted(set(fetch))


def cmd_verify(a):
    try:
        listing = json.load(open(a.listing, encoding="utf-8")) if a.listing else None
        manifest = json.load(open(a.manifest, encoding="utf-8")) if a.manifest and os.path.exists(a.manifest) else None
    except Exception as e:
        print(f"cannot read input: {e}", file=sys.stderr)
        sys.exit(2)
    if listing is None and manifest is None:
        print("give --listing and/or --manifest", file=sys.stderr)
        sys.exit(2)
    if manifest and manifest.get("schema") != SCHEMA:
        print(f"warning: manifest schema {manifest.get('schema')!r}", file=sys.stderr)
    res, fetch = verify(a.dest, listing, manifest)
    if a.json:
        print(json.dumps({"ok": not fetch, "fetch": fetch, "critical": [f for f in fetch if is_critical(f)],
                          "files": {k: {"state": v[0], "detail": v[1]} for k, v in res.items()}},
                         indent=1, ensure_ascii=False))
    else:
        ok = sum(1 for v in res.values() if v[0].startswith("OK"))
        print(f"{ok} of {len(res)} store files verified" + (" — all good" if not fetch else ""))
        for rel in fetch:
            st, det = res.get(rel, ("MISSING", ""))
            print(f"FETCH {rel}  [{st}] {det}" + ("  (CRITICAL)" if is_critical(rel) else ""))
    sys.exit(0 if not fetch else 1)


def cmd_extract(a):
    b = read_text_blocks(a.src)
    if a.bytes is not None and len(b) != a.bytes:
        print(f"MISMATCH: extracted {len(b)} bytes, OneDrive lists {a.bytes} — not written", file=sys.stderr)
        sys.exit(1)
    os.makedirs(os.path.dirname(os.path.abspath(a.dest)) or ".", exist_ok=True)
    open(a.dest, "wb").write(b)
    print(f"wrote {a.dest}: {len(b)} bytes, sha16 {hashlib.sha256(b).hexdigest()[:16]}")


def cmd_check(a):
    got = os.path.getsize(a.file)
    if got == a.bytes - 1:
        # The connector's inline result drops the file's final newline (seen on every inline read, 13 Oct).
        with open(a.file, "rb") as f:
            f.seek(-1, os.SEEK_END)
            last = f.read(1)
        if last != b"\n":
            with open(a.file, "ab") as f:
                f.write(b"\n")
            got += 1
            print(f"restored the trailing newline the inline read drops ({a.file})")
    if got != a.bytes:
        print(f"MISMATCH {a.file}: {got} bytes, OneDrive lists {a.bytes} — re-read it and write the text exactly "
              f"as returned (no reformatting, no added or dropped trailing newline)", file=sys.stderr)
        sys.exit(1)
    try:
        json.load(open(a.file, encoding="utf-8"))
    except Exception as e:
        print(f"MISMATCH {a.file}: right size but does not parse ({e})", file=sys.stderr)
        sys.exit(1)
    print(f"OK {a.file}: {got} bytes, sha16 {sha16(a.file)}")


def cmd_manifest(a):
    files = {rel: {"bytes": os.path.getsize(os.path.join(a.dir, rel)), "sha16": sha16(os.path.join(a.dir, rel))}
             for rel in store_files(a.dir)}
    if not any(fnmatch.fnmatch(r, "rows_p*.json") for r in files) or "rows.json" not in files:
        print("refusing: no rows.json / rows_p*.json in " + a.dir, file=sys.stderr)
        sys.exit(2)
    m = {"schema": SCHEMA, "written": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "by": a.by,
         "mirror": MIRROR_URL,
         "_doc": "Bytes and sha256 prefix of every store file as its writer uploaded it. Loaders verify the mirror "
                 "copy against this and the OneDrive listing (tracker/store_sync.py). Written last by every run "
                 "that writes store files.",
         "files": files}
    out = a.out or os.path.join(a.dir, MANIFEST)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=1, sort_keys=False)
        f.write("\n")
    print(f"{out}: {len(files)} files, {os.path.getsize(out)} bytes")


def cmd_files(a):
    m = {f"store/{rel}": os.path.join(a.dir, rel) for rel in store_files(a.dir)}
    if os.path.exists(os.path.join(a.dir, MANIFEST)):
        m[f"store/{MANIFEST}"] = os.path.join(a.dir, MANIFEST)
    print(json.dumps(m, indent=1))


def cmd_sizes(a):
    for rel in store_files(a.dir) + ([MANIFEST] if os.path.exists(os.path.join(a.dir, MANIFEST)) else []):
        print(rel, os.path.getsize(os.path.join(a.dir, rel)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("listing"); p.add_argument("listing"); p.add_argument("--prefix", default="")
    p.add_argument("--out"); p.set_defaults(fn=cmd_listing)
    p = sp.add_parser("collect"); p.add_argument("src"); p.add_argument("dest"); p.set_defaults(fn=cmd_collect)
    p = sp.add_parser("verify"); p.add_argument("dest"); p.add_argument("--listing"); p.add_argument("--manifest")
    p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_verify)
    p = sp.add_parser("extract"); p.add_argument("src"); p.add_argument("dest"); p.add_argument("--bytes", type=int)
    p.set_defaults(fn=cmd_extract)
    p = sp.add_parser("check"); p.add_argument("file"); p.add_argument("--bytes", type=int, required=True)
    p.set_defaults(fn=cmd_check)
    p = sp.add_parser("manifest"); p.add_argument("dir"); p.add_argument("--by", required=True); p.add_argument("--out")
    p.set_defaults(fn=cmd_manifest)
    p = sp.add_parser("files"); p.add_argument("dir"); p.set_defaults(fn=cmd_files)
    p = sp.add_parser("sizes"); p.add_argument("dir"); p.set_defaults(fn=cmd_sizes)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
