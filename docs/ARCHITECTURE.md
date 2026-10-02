# Grid Docket v3 — how the system runs (2 October 2026)

Supersedes the run design in `implementation-scope-v2.md` and `cloud-native-architecture.md`. Their access findings still apply.

## Pipeline

| Stage | Where | When | Writes |
|---|---|---|---|
| Collector | GitHub Actions, `rettyoung/BODI` (`collector/`) | Nightly 06:17 UTC (Sun–Sat, ~23:17 PT) | `data/candidates/`, `data/filings/` (full document text), `data/health/` in the repo |
| Sweep | Claude scheduled task "Utility Tracker Sweep" (`trig_01DA4N9G8Qv1zeggHuN9eQ3g`) | Mon 04:55 PT | New immutable part `rows_pN.json` + manifest, seen index, run record, `state.json` (OneDrive); same part mirrored to repo `store/` |
| Brief | Claude scheduled task "Weekly Utility Tracker" (`trig_01X19jgn9aMSPL5ov1TQ7bvj`) | Mon 07:54 PT | Excel master + narrative (PDF/DOCX/MD) in repo `deliverables/`; console republished; email; `briefs/<date>.json` |
| Manual pass | Skill `grid-docket-manual-pass` in the Claude desktop app | Whenever Rett runs it | `/GridDocket/manual/manual_<run>_<STATE>.json` + manifest (`complete: true`) only |

**Single writer.** Only the Sweep writes the row store (lock file `sweep_lock.json`; part upload uses conflict-fail). The manual pass and the Brief never touch rows.

**Overlays.** Parts are immutable. Later changes to an earlier event travel in the new part as `supersedes` / `overlays` (Status, Next Milestone, Next Date, Appeal, Superseded only) and are applied at load by `tracker/rowstore.py`.

**Excel.** `tracker/build_tracker.py` (canonical) and `console/tracker_xlsx.js` (ExcelJS, in the console) produce the same workbook; the `xlsx-parity` CI job compares them cell by cell (0 differences on 2026-10-02).

**Manual pass integration.** The Sweep ingests a manual run only when its manifest exists with `complete: true` and its run_id is not in `state.manual_ingested`; partial or abandoned runs are invisible. Each Sweep writes `manual_queue.json` telling the next manual pass what to read.

**Corrections.** `prompts/corrections_queue.md` lists earlier-session findings (Texas audit directive / ERCOT Batch Zero pause; Microsoft's APS closing brief; XHLF threshold; U-37882 milestone; store housekeeping; TX text quality; docket-activity backfill). The Sweep verifies each at source before writing.

## First collector run (2026-10-02)
334 new items, 160 documents extracted in 20 minutes. Working: FERC, Federal Register, EDGAR, TX, GA, LA, KS, NM (cases), watch pages, RSS, IR decks (10 of 16). Repaired after the run: Arizona (full filing lists now), Oklahoma (cause-number confirmation), Missouri (case-id pairing), incomplete TLS chains (AIA). Open: NM documents endpoint, Alabama RSS (server 500), PJM Inside Lines (CAPTCHA), six IR pages that refuse automation (covered via EDGAR exhibits and q4cdn search).

## Outstanding user actions
- Disable any local Cowork copies of the old tasks (`utility-tracker-sweep`, `weekly-utility-brief` on the desktop) — the lock prevents double writes but a local Brief would still send a second email.
- Send the six agency allowlist drafts in Outlook (VA, NC, SC, IL; OH and WV via their web forms).
- Optional: free EIA, congress.gov and Open States API keys as repo secrets.
