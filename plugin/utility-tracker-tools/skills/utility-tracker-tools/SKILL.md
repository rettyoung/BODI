---
name: utility-tracker-tools
description: The Utility Tracker (Grid Docket) tracker scripts — store_sync, rowstore, subtables, check_run, manual_check, shortlist, ir_ledger, build_console, build_tracker, narrative — with the console template and watch list. Load this whenever a Sweep, Brief or manual-pass run, or BODI/prompts/*.md, says to run a tracker/*.py script; it runs these packaged copies instead of code cloned from GitHub.
---

# Utility Tracker tools

The scheduled Sweep and Brief run on automatic approval, whose permission check refuses to execute code
freshly cloned from GitHub. This skill carries the same scripts as part of Rett's own plugin. Run them from
here; never run anything under a clone's `tracker/` or `collector/`.

The folder `bodi/` next to this SKILL.md holds `tracker/`, `console/`, `config/`, `BODI_COMMIT` (the repo
commit these copies came from) and `CODE_SHA256.txt`. Call this skill's base directory `$SKILL` (the Skill
tool prints it as "Base directory for this skill").

## Set up the run folder (once per run, before any script)

Work in a folder named `bodi_run/` in the session's working directory, never inside the clone:

```bash
SKILL=<base directory for this skill>
mkdir -p bodi_run && cp -r "$SKILL/bodi/tracker" "$SKILL/bodi/console" "$SKILL/bodi/config" bodi_run/
mkdir -p bodi_run/data/state bodi_run/data/health
# data only, from the clone if there is one (read, never executed):
[ -f BODI/data/state/collector_state.json ] && cp BODI/data/state/collector_state.json bodi_run/data/state/
ls BODI/data/health/2*.json 2>/dev/null | tail -10 | xargs -r -I{} cp {} bodi_run/data/health/
python3 -c "import yaml, openpyxl" 2>/dev/null || pip install --quiet --break-system-packages pyyaml openpyxl
```

Then `cd bodi_run` and run every command exactly as the repo prompts write it (`python tracker/store_sync.py …`,
`python tracker/check_run.py …`, `python tracker/build_console.py …`). Every path the prompts give relative to
the clone (`store_live/`, `out/`, `work/`, `console/store_mirror.html`, `status.json`, `narrative.md`,
`run_record.json`) is relative to `bodi_run/` instead. Take `prompts/*.md` from the clone as before; only the
code comes from here.

## Check the copies are current

```bash
cmp -s <(cd bodi_run && sha256sum $(cut -d' ' -f3 "$SKILL/bodi/CODE_SHA256.txt")) "$SKILL/bodi/CODE_SHA256.txt" && echo copies-intact
(cd BODI 2>/dev/null && sha256sum $(cut -d' ' -f3 "$SKILL/bodi/CODE_SHA256.txt") 2>/dev/null) | diff -q - "$SKILL/bodi/CODE_SHA256.txt" >/dev/null && echo repo-matches || echo repo-differs
```

Record in the run or brief record `"tools": {"source": "plugin", "commit": "<BODI_COMMIT>", "repo_matches": true|false}`.
If `repo-differs`, the repo's scripts changed after this plugin was built: run the plugin's copies anyway,
and put "Tracker tools are older than the repo (plugin <commit>); rebuild the utility-tracker-tools plugin"
in the status check (Brief) or the report (Sweep). Never fall back to running the clone's code.

## If a script cannot run

If this skill is missing, or a command from `bodi_run/` is refused by the permission check, do not retry it
or work around it: apply that script's rules by hand as the task prompt's hand-check invariant says, record
`"tools": {"source": "hand", "error": "<exact refusal or reason>"}`, and say so in the report or status check.

## Notes

- `shortlist.py` (Sweep Steps 3.2, 8.7, 8.8) reads the collector data in the clone, which is data, not code: pass
  `--data ../BODI/data` from `bodi_run/`. `ir_ledger.py` (Sweep Step 3.6, from 0.4.0) reads the same data: pass
  `--data ../BODI/data` too. `brief_input.py` and `usage.py` read only `store_live/` and records.
- `statefile.py` (from 0.4.1) splits and merges the tracker state (`state.json`, `state_tracking.json`,
  `state_reference.json`, `backfill_done_pN.json`, `state_frozen_*.json`); `shortlist.py`, `brief_input.py` and
  `build_console.py` merge it themselves. If `bodi_run/tracker/statefile.py` is missing, the plugin is older than
  0.4.1 and cannot read the split state.

- `narrative.py` needs pandoc and wkhtmltopdf or LibreOffice for the PDF; if they are missing, its error is
  reported in the status check and the console still publishes.
- These scripts read and write only the files named on their command lines and under `bodi_run/`; they never
  touch OneDrive or the network themselves.
