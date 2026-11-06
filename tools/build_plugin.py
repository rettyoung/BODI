"""Build the utility-tracker-tools plugin from this repo, for Rett to upload to his own plugins.

The scheduled Sweep and Brief may not run code cloned from GitHub, so they run packaged copies of tracker/,
console/ and config/ from Rett's personal plugin (docs/OPERATING_CARD.md). Rebuild it whenever those change.

usage (from the repo root, standard library only):
    python tools/build_plugin.py [--out dist]

It writes dist/utility-tracker-tools/ (the plugin folder) and dist/utility-tracker-tools-<version>.zip
(the same folder, zipped with the folder at its root). The manifest and the plugin's SKILL.md come from
plugin/utility-tracker-tools/ — bump "version" in its plugin.json before building a new release. BODI_COMMIT
is the repo's current commit; CODE_SHA256.txt lists every packaged file, as the plugin's SKILL.md checks it.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "plugin", "utility-tracker-tools")
PACKAGED = ("tracker", "console", "config")


def files_under(base, top):
    out = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(base, top)):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for f in sorted(filenames):
            if f.endswith(".pyc"):
                continue
            out.append(os.path.relpath(os.path.join(dirpath, f), base).replace(os.sep, "/"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    a = ap.parse_args(argv)
    manifest = json.load(open(os.path.join(SRC, ".claude-plugin", "plugin.json"), encoding="utf-8"))
    version = manifest["version"]
    try:
        commit = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        # a copy of the repo without .git (e.g. unpacked on a computer with no GitHub access) carries COMMIT
        cf = os.path.join(ROOT, "COMMIT")
        commit = open(cf).read().strip() if os.path.exists(cf) else "unknown"
    dest = os.path.join(a.out, "utility-tracker-tools")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(SRC, dest)
    bodi = os.path.join(dest, "skills", "utility-tracker-tools", "bodi")
    os.makedirs(bodi)
    for top in PACKAGED:
        shutil.copytree(os.path.join(ROOT, top), os.path.join(bodi, top),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    with open(os.path.join(bodi, "BODI_COMMIT"), "w", newline="\n") as f:
        f.write(commit + "\n")
    lines = []
    for top in PACKAGED:
        for rel in files_under(bodi, top):
            h = hashlib.sha256(open(os.path.join(bodi, rel), "rb").read()).hexdigest()
            lines.append(f"{h}  {rel}")
    with open(os.path.join(bodi, "CODE_SHA256.txt"), "w", newline="\n") as f:
        f.write("\n".join(sorted(lines, key=lambda l: l[66:])) + "\n")
    zpath = os.path.join(a.out, f"utility-tracker-tools-{version}.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, _, filenames in os.walk(dest):
            for fn in sorted(filenames):
                full = os.path.join(dirpath, fn)
                z.write(full, os.path.relpath(full, a.out).replace(os.sep, "/"))
    print(f"built utility-tracker-tools {version} from commit {commit}: {len(lines)} packaged files")
    print(f"  folder {dest}")
    print(f"  zip    {zpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
