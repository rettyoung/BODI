# Grid Docket — consolidated project context

**As of Friday 2 October 2026, 17:00 PT. For Rett Young, Blue Owl Digital Infrastructure (BODI).**
This replaces three earlier extracts: `GRID_DOCKET_HANDOFF.md`, `claude/session-handoff-2026-10-02.md` and
`claude/session-extract-2026-10-02-tracker-gaps.md`. Where those disagreed, this document states which view
won and why.

**Precedence when sources disagree:** the live OneDrive files (`/GridDocket/state.json`, the row store) win
over this document; this document wins over anything older. The three other project docs still hold useful
detail: `claude/architecture-v3.md` (how v3 runs), `claude/sources-v3.md` (full source lists),
`claude/reachability-findings-2026-10-02.md` (runner probe). `claude/cloud-native-architecture.md` and
`claude/implementation-scope-v2.md` are superseded for run design; their access findings still apply.

---

## 1. What this is

A fully automated weekly market and regulatory tracker for **large-load (data-center) customers and large
generators**. It covers **25 named utilities, 8 RTOs and 18 jurisdictions**, oriented to data-center siting and
power procurement.

**Jurisdictions (18):** AL, AZ, FERC, GA, IL, KS, LA, MO, NC, NM, NV, OH, OK, PA, SC, TX, VA, WV (plus
`US-Federal` for federal items with no state). Colorado (Xcel 26AL-0137E) and Oregon (PacifiCorp UE 463) are
an **open scope question**.

**What it tracks:** utility dockets and commission actions; FERC/NERC; executive, legislative and court
actions; earnings and investor presentations; major customer and market-participant activity.

**Deliverables, every Monday:**
1. **The Excel master tracker** (`Grid_Docket_Tracker_MASTER.xlsx`) — the **primary deliverable**. Rett: "I
   like the excel tracker template we built; don't discard that, it should be the primary deliverable."
2. **A narrative report** accompanying each delivery (PDF and Word, from markdown).
3. **The console** — an interactive filtering tool over all history (a published Artifact), with status,
   milestones, the narrative and the Excel download.
4. **An email brief** to rett.young@blueowl.com, written for the BODI deal team and forwardable unedited.

---

## 2. Rett's standing constraints (preserve all of these)

- **Fully cloud-based, no dependency on his computer.** "I want the scheduled task to be fully cloud based
  with no computer dependency." State lives in OneDrive; if it is unreachable a run **stops and reports**,
  never falls back to a local file.
- **Read primary filings directly.** "I don't want to manually subscribe to a bunch of additional email
  listservs. You need to be able to directly read and summarize primary filings." Feeds already arriving in
  the inbox may be used; **no new subscriptions or docket e-notifications** (an earlier recommendation to
  subscribe to every watched docket is therefore declined).
- **A second, manual process on his computer is acceptable** for gaps the cloud can't fill, run on whatever
  cadence he chooses, with results flowing into the scheduled outputs automatically and safely.
- **Web fetching is always permitted** for this project. "Stop asking. It is always allowed." (WebFetch and
  WebSearch are set to always-allow.)
- **Use the work email** in the SEC User-Agent: `BlueOwl-RegTracker/4.0 (rett.young@blueowl.com)`.
- **Mail is read-only.** "RTO Insider and NPM emails are in my 'Other' inbox. I don't want to change the rules
  for them. Scrape them from there without marking them read." Only `outlook_email_search` and
  `read_resource`. No label, move, delete, draft or send tools; never create or suggest an inbox rule.
- **Sending is permitted for exactly one thing:** the weekly brief, to rett.young@blueowl.com, once per run.
  No cc, bcc, other recipient, reply or forward.
- **Never create an account, enter a credential, or defeat a CAPTCHA or bot-check.** Never route around a
  robots.txt refusal. Record `ACCESS_REGRESSION` and move on. In the manual pass, Rett solves any CAPTCHA
  himself.
- **Never take credentials in conversation.** Keys live as GitHub repo secrets (or are typed by Rett into
  the place they belong). Never store secrets in an artifact database.
- **Licensed sources** (NPM, CapIQ, RTO Insider, DCC Bi-Weekly): facts may be extracted and cited; their
  sentences are never reproduced. Investor decks are public company disclosures and may be quoted.
- **Polling commission portals is approved** — recorded as accepted risk by Rett, 2026-09-17. The ToS review
  was **not** completed.
- **No same-day exception alerts**, by design. Compensated by a mandatory 30-day milestone calendar that is
  never omitted from the brief.
- **Cost-sensitive.** An earlier build used up a month of credits and did not work. Validate before building
  anything expensive. "Stop if usage hits 90%"; "avoid getting stalled and burning tokens."
- **Best-in-class professional deliverable.** The console must be a real tool. Rett's correction on an early
  version — "what is the point of the internet dashboard? I thought it was meant to be an interactive tool" —
  is the standard.

---

## 3. Where everything lives

### OneDrive — the system of record

```
driveId       b!2OnbGRjzpEKUL9fVRRC4Lv4LSN1Bpb1PmI1aJZgbWGvvNTw6Z-6ISI31RRmmeISO
/GridDocket/  01MLUCMYJFKKTYR6ENBFDZOOAQQOLD5QNX
  manual/     01MLUCMYLTL2DGJ4AHFBB2OJSZMLMPBRJU   (created 2026-10-02)
  runs/       01MLUCMYNQE5VMUQYLERCIPHUAB5IL4B4E   (created 2026-10-02)
  briefs/     01MLUCMYPB3OSQIZONA5FLUGQHMAZGKC3U   (created 2026-10-02)
webUrl        https://blueowlcap-my.sharepoint.com/personal/rett_young_blueowl_com/Documents/GridDocket
```

| File | What it is |
|---|---|
| `state.json` | **Read first.** `last_successful_sweep` (2026-09-18), `last_brief_date` (null), registry corrections, structural findings, access methods, explicit negatives, remaining gaps, watch signals, standing facts, pipeline baselines, milestone calendar. The Sweep owns it; the Brief changes only `last_brief_date`. |
| `rows.json` | **A manifest, not rows.** Lists the part files in order. |
| `rows_p1..p4.json` | The 229 baseline rows (58/58/58/55). Each row is a 26-element positional array; column names appear once, in `rows_p1.columns`. |
| `seen_index.json` | Dedupe index, time-bounded at 180 days. |
| `metrics.json` | Structured pipeline series (43 points, 11 issuers) — drives the conversion charts. **This OneDrive copy (11,385 bytes) is authoritative.** |
| `tariff_terms.json` | Structured tariff terms (10 tariffs) — drives the comparison matrix. |
| `backfill_state.json` | The original backfill queue. **Stale** — still says phases 2–3 pending (see §7). Corrected by the Sweep (corrections item C-05). |
| `README.md` | Folder guide. |
| `sweep_lock.json` | (created by the v3 Sweep) single-writer lock. |
| `manual_queue.json` | (created by the v3 Sweep) what the next manual pass should read. |

**Why parts:** a single Graph write is capped at 1,048,576 bytes. Each Sweep writes a **new** part
(`rows_p5.json`, then p6…) and appends it to the manifest. It never rewrites an existing part.

### GitHub — `rettyoung/BODI` (private)

| Path | What it is |
|---|---|
| `collector/` | Nightly collector: `common.py` (HTTP layer, robots, extraction, AIA chain completion), `adapters.py` (per-source adapters), `run.py` (orchestrator, budgets, checkpoints, backfill mode), `discover.py` and `probe_adapter.py` (repair tools) |
| `config/watchlist.yaml` | **The single place to add or drop coverage**: keywords, jurisdictions and routes, watched dockets, entity aliases, party watch list, EDGAR issuers, Federal Register terms, watch pages, RSS, IR pages, mirrors |
| `data/` | Collector output: `candidates/<date>.jsonl`, `filings/<jur>/<source>/<id>.json` (full text), `health/`, `state/`, `backfill/`, `debug/`, `tests/` |
| `store/` | Mirror of the OneDrive row-store parts (verified against OneDrive each run) |
| `tracker/` | `vocab.py`, `rowstore.py` (load, overlays, validation CLI), `build_tracker.py` (canonical Excel), `build_console.py` (console package), `narrative.py` (PDF/DOCX) |
| `console/` | `index.html` (console page), `tracker_xlsx.js` (in-browser Excel builder) |
| `prompts/` | `sweep.md`, `brief.md` (reference copies of the scheduled-task prompts), `corrections_queue.md` |
| `manual/SKILL.md` | Copy of the manual-pass skill |
| `deliverables/` | Weekly Excel master and narrative, committed by the Brief |
| `SOURCES.md`, `docs/` | Source lists; architecture note; this document |
| `.github/workflows/` | `collect.yml` (nightly), `xlsx-parity.yml`, `adapter-probe.yml`, `discover.yml`, `probe.yml` |

### Console

Published Artifact **https://claude.ai/artifact/JJ8FYdvfZ2WPg6r4UpFXbW** (version 6, published 2026-10-02).
Private to Rett until shared. Declares the `downloads` capability (lets readers save the Excel, the narrative
PDF and a filtered CSV). Supporting files: `data.json` (events + the full 26-column row table), `metrics.json`,
`tariff_terms.json`, `status.json`, and weekly `narrative.md` plus the narrative PDF. Republish to the same
URL; never pass `icon` or `capabilities` (they carry forward).

Older artifacts from v1: protocol spec `https://claude.ai/artifact/Sqwj1xLtBTRPS9skXjbzKe`; tracker config DB
`https://claude.ai/artifact/68T91ssmaVqRQWQfbjw9TT`. Not used by v3.

### Scheduled tasks (cloud)

| Task | ID | Schedule | State |
|---|---|---|---|
| Utility Tracker Sweep (v3) | `trig_01DA4N9G8Qv1zeggHuN9eQ3g` | Mon 04:55 PT (`CRON_TZ=America/Los_Angeles 55 4 * * 1`) | Enabled, auto-approve, M365 + Box attached. First v3 run 2026-10-05. |
| Weekly Utility Tracker — Brief (v3) | `trig_01X19jgn9aMSPL5ov1TQ7bvj` | Mon 07:54 PT (`CRON_TZ=America/Los_Angeles 54 7 * * 1`) | Enabled, auto-approve, M365 + Box attached. First v3 run 2026-10-05. |
| Current Events Digest (unrelated) | `trig_01Q57Hm8Enb4TFRrhTZRbpc7` | weekdays 07:28 PT | Enabled; not part of this project |

Both tracker tasks were the paused v1/v2 tasks, **updated in place** (history kept) with the v3 prompts.

**Possible local duplicates.** One earlier extract says desktop-local copies (`utility-tracker-sweep`
Mon 05:11 and `weekly-utility-brief` Mon 08:00, prompts at `C:\Users\ryoung\Claude\Scheduled\<taskId>\SKILL.md`)
were enabled; another found both tracker tasks disabled. Local desktop tasks are not visible from the cloud.
**If they exist, disable them**: the v3 lock and conflict-fail write prevent double rows, but a local Brief
would still send a second email.

### Collector (GitHub Actions)

Nightly at **06:17 UTC** (~23:17 PT). Writes only to the repo. Never classifies, never writes the row store.

---

## 4. Architecture v3 (current)

```
Nightly  GitHub Actions collector ──► repo data/ (candidates + full-text filings + health)
Mon 4:55 Sweep (Claude, cloud)    ──► reads collector data + Outlook (read-only) + manual drops + web reader
                                      ──► NEW immutable part in OneDrive (+ mirror in repo store/)
Mon 7:54 Brief (Claude, cloud)    ──► Excel + narrative to repo deliverables/ ──► console republished ──► email
Any time Manual pass (desktop app) ──► OneDrive /GridDocket/manual/ only ──► picked up by the next Sweep
```

**Design rules:**
- **Single writer.** Only the Sweep writes the row store. It takes `sweep_lock.json` (stops if another run
  holds a lock under 3 hours old, or a run record already exists for today) and uploads each new part with
  conflict-fail.
- **Commit order:** new part → manifest → seen index → metrics/tariffs → run record → `state.json` last. A
  run that dies repeats its window safely (identity + seen index + `manual_ingested` make it idempotent).
- **Immutable parts with overlays.** A later change to an earlier event travels inside the new part:
  `supersedes` [{old_event_id, new_event_id, reason}] marks all old rows Superseded = Yes; `overlays`
  [{event_id, column, value, reason}] may change only Status, Next Milestone, Next Date, Appeal, Superseded.
  `tracker/rowstore.py` applies them at load. Substantive change = a new event.
- **Validation before any write:** `python tracker/rowstore.py --part <file>` checks vocabulary, 26 cells,
  Event ID format and reuse, one date per event, overlay targets.
- **Manual-pass integration:** the Sweep ingests a manual run only when its manifest `manual_<run_id>.json`
  exists with `"complete": true` and the run_id is not in `state.manual_ingested`. Partial or abandoned runs
  are invisible. Each Sweep writes `manual_queue.json` for the next pass.
- **Mirror check:** each run verifies repo `store/` against the OneDrive manifest; OneDrive wins.
- **Collector repair:** for a source failing 2+ consecutive nights, the Sweep may open a pull request with a
  fix (REST API; never merges, never pushes collector changes to main). Fixes that would need to defeat a
  block, ignore robots.txt or use a credential are not fixes.
- **Excel parity:** `build_tracker.py` (canonical, Python) and `console/tracker_xlsx.js` (ExcelJS, in the
  console) build the same workbook; CI compares them cell by cell — values, formulas, fonts, fills, borders,
  alignment, widths, heights, freeze panes, autofilter. **0 differences** on 2026-10-02.

### The Sweep (v3 prompt; reference copy `prompts/sweep.md`)

Steps: preflight and lock → attach repo (`add_repo rettyoung/BODI`, push) → load state and store, verify
mirror → health (consecutive failures, SUSPECT_ZERO after checking explicit negatives and renamed entities)
→ collector candidates (metadata triage; **party watch**; read up to **25 documents × 40,000 characters**;
backlog the rest) → mail (FERC/ERCOT folders; RTO Insider, NPM, CapIQ, NCUC, DCC Bi-Weekly; **newsletter
canary**: any newsletter event with no row is either sourced and added or recorded `CANARY_MISS`) → manual
drops → web reader routes (PA; AZ PDFs; fallbacks for manual-route states, else `DEFERRED_NEEDS_MANUAL`) →
grain/identity/supersession/dedupe → classify → corrections queue (up to 6 items/run) → commit → collector
repair → run record and three-paragraph report. Target 30 minutes. Degraded mode (mail + manual + web only)
if the repo can't be attached.

### The Brief (v3 prompt; reference copy `prompts/brief.md`)

Setup and mirror check → preconditions (freshness: >3 days stale = short `[No sweep]` failure notice only;
zero new events and green = three-line "nothing moved" brief) → status check (GREEN/AMBER/RED; RED at the
top) → **30-day milestones, never omitted** (URGENT inside 7 days; past-dated without outcome = "outcome
needed") → synthesis by Subject with cross-source synthesis → `narrative.md` (700–1,200 words) → build
(`build_console.py … --deliverables deliverables/<date>`; copy master to `deliverables/`) → commit → publish
console → email → record `/GridDocket/briefs/<date>.json`, update only `state.last_brief_date`.

**Email:** subject `Grid Docket — <D Mon> · <N> high-impact · <three shortest descriptors>` (prefix `[Status] `
when RED, `[No sweep] ` for the failure notice). HTML, 400 words target, 600 ceiling. Sections: STATUS CHECK
(amber/red only) · UPCOMING MILESTONES (always) · THIS WEEK (3–5 high items) · ALSO MOVING (≤6 medium) · LINKS
(console; repo deliverables) · one-line footer. Fewer than three high items never licenses promoting medium
ones.

**Excel delivery mechanics:** the workbook cannot be served as an artifact file, and binary files can't
round-trip through the Graph text/base64 tool path (~4 tokens per base64 character; a 71 KB workbook ≈ 385k
tokens, silently truncated). So the console builds it in the browser from the full row table, and the Brief
commits the canonical Python build to the repo. The workbook is a rendering; the JSON is the source of truth.

### Manual pass (skill `grid-docket-manual-pass`, saved by Rett 2026-10-02)

Run in the Claude desktop app whenever wanted. Reads `manual_queue.json`, uses the built-in browser (or Claude
in Chrome) on the watched dockets of VA, NC, SC, IL, OH, WV, NV plus specific requests (e.g. Arizona PDFs the
cloud can't open). Extracts text (agency text layer first — WV `ViewText.cfm`; then PDF text via pdf.js; OCR
only if no text layer, flagged `"ocr": true`). Saves one file per state as it goes, then the manifest last.
Never writes the row store. Rett solves any CAPTCHA; otherwise the state is skipped as `blocked_captcha`.

---

## 5. The schema (decided deliberately — do not "improve" back)

26 columns, in this order:

```
Date | Event ID | Utility | Jurisdiction | Subject | Venue | Instrument | Document | Headline | Takeaway |
Status | Next Milestone | Next Date | Materiality | Confidence | Appeal | Superseded | Upfront Costs | Rates |
Term | Speed | Curtailment | Deliverability | Supply/Demand | Market Participation | Source URL
```

- **Grain: one row per (event × entity × jurisdiction).** Utility and Jurisdiction are single-valued. Explode
  combined items (SWEPCO TX/LA, Entergy LA/TX, EPE TX/NM, SPS TX/NM, ApCo VA/WV, Evergy KS/MO, Duke NC/SC) and
  keep them adjacent. Combined cells break sorting and filtering, the primary way the workbook is used.
- **Count distinct Event IDs for "how many things happened"; count rows only for entity exposure.** 161 events
  ≠ 229 rows.
- **Event ID = `E-YYYYMMDD-NNN`, the DISCOVERY date**, not the event date. No separate date-added column.
  Baseline rows all carry `E-20260918-`.
- **RTOs are first-class entities**, one row each, RTO name alone in Utility. Track all 8 (PJM, MISO, SPP,
  ERCOT, CAISO, NYISO, ISO-NE, Western Power Pool / WRAP). **ERCOT rows carry Jurisdiction `TX`**, never
  `PUCT`; ERCOT is not FERC-jurisdictional.
- **Levers:** eight columns, integer `1` or blank, never free text, Y/N or colour; fixed order as above.
- **Vocabularies:**
  - Subject: Large Load Customer Terms · Generation Supply · Rates & Cost Allocation · Law & Governance ·
    Interconnection Queue · Commercial Activity · Transmission & Delivery · Self-Supply & Colocation · Market
    Structure · Technology
  - Venue: State Commission · Utility · Legislature · Market Operator · Court · Other State/Federal Agency ·
    FERC · Executive · Company / Industry Group · Misc
  - Instrument (by what was created, not the caption): Statute · Rule · Directive · Final Order · Procedural
    Order · Tariff · Contract · Settlement / Stipulation · Application / Petition · Auction Result · Study /
    Report · Disclosure
  - Materiality floor: **High / near-term** and **Medium / long-term** only; Context is discarded (keeps
    week-over-week volume meaningful).
  - Confidence: **Verified** (primary document's text layer read) · **Reported** (secondary, licensed, snippet,
    paywalled, OCR, or a re-read figure from a corrupt source) · **Unverified** (extraction failed — event row
    only, no numbers). Nothing is Verified on OCR alone or on a search snippet.
- **Document** is descriptive and contains "Docket" when it is one.
- **Never delete a row.** Supersede by adding a row and flagging the old (now via overlays, §4).
- **Workbook formatting:** Tracker sheet Arial 9; header bold white on `1F3243`, height 34; data rows height
  76, every cell centred and middle-aligned, wrap on; thin `D9D9D9` borders; alternating band `F7F5F1` per
  Event ID (first block unbanded); Materiality by font (High `9A2F2F` bold, Medium `8A6414`); Confidence by
  fill (Verified `E3F0E8`, Reported `F8EED6`, Unverified `F6E2E0`); fixed widths; **freeze C2**; autofilter
  across all columns; sorted by (Date, Event ID) descending. Summary sheet: rows vs distinct events vs
  average; counts by materiality, confidence, subject, venue, lever, jurisdiction, appeal, superseded — **all
  live formulas**. Distinct events:
  `=SUMPRODUCT((Tracker!$B$2:$B$n<>"")/COUNTIF(Tracker!$B$2:$B$n,Tracker!$B$2:$B$n&""))`. Sanity check:
  materiality, confidence, subject and jurisdiction totals each equal the row count, else the build fails
  loudly.
- **Naming:** email sections are "STATUS CHECK" and "UPCOMING MILESTONES". "So What" became "Takeaway". The
  "lens" taxonomy and the "Schema" column were dropped.
- A proposed v2 store redesign (`matters.json`, `kpis.json`, monthly event logs, an expanded jurisdiction enum
  such as `FED-FERC`, `US-CONG`, `COURT-FED`, `RTO-*`) was **not adopted**. v3 keeps the 26-column row store
  and adds overlays. Federal items with no state use `US-Federal`. (H.R. 9340 previously had no valid slot;
  it now goes under `US-Federal`.)

---

## 6. Current state of the data

**Baseline v2, loaded 2026-09-18: 161 events / 229 rows**, 2025-11-07 to 2026-09-18, 18 jurisdictions,
33 entities. Confidence 185 Verified / 42 Reported / 2 Unverified. Materiality 149 High / 80 Medium.
On appeal: 4 rows. **Superseded: 3 rows across 2 events** (E-20260918-035 ×2 Duke NC+SC; E-20260918-110 APS)
— `state.json` says 1, which is stale; the Sweep recomputes flags from the data each run.

**Nothing has been collected into the row store since 2026-09-18.** The Mondays of 21 and 28 September passed
in silence because the tasks were disabled. The first v3 Sweep (5 October) covers 18 Sept onward.

**Repo mirror:** `store/rows_p1..p4` were reconstructed on 2026-10-02 from the master workbook plus the final
console data (14 cells refreshed from the console) and verified against OneDrive (part boundaries: p1 ends
E-015 SPS TX; p2 starts E-015 SPS NM; p3 starts E-079 TEP AZ; p4 starts E-120 ComEd; 11 field spot-checks).

---

## 7. Coverage history and known gaps (the honest backfill picture)

- **Phase 1 (investor disclosure), done 2026-09-18:** 39 events / 71 rows, 16 issuers, Q4 2025–Q2 2026.
  Dominion Q4/Q1 and Ameren Q4/Q1 filenames unresolved (data recovered from later decks); EEI Nov 2025 only
  Oncor; Entergy 2026 Investor Day deck not located.
- **Phases 2–3 (federal/RTO and state dockets)** were done as a single pass on 2026-09-18, then a **gap-closing
  second pass covered only VA, AZ, NM, SC, GRDA, KS and WV**. TX, ERCOT and the remaining states had one pass.
  **Docket activity was never enumerated filing-by-filing anywhere** — collection followed known docket
  numbers and documents. `backfill_state.json` was never updated and still says phases 2–3 are pending.
- **Two confirmed misses (found 2026-10-02 by a diagnostic session):**
  1. **Texas — Governor's audit directive and ERCOT Batch Zero pause.** 2026-08-03 Gov. Abbott directed PUCT
     and ERCOT to verify/audit data centers in the large-load interconnection process. 2026-08-10 ERCOT filed a
     good-cause exception in **PUCT Project 58317** pausing Batch Zero classification and studies; no data
     center or crypto load energized until verification completes; PUCT took it up 2026-08-20.
     2026-09-03 conditional classifications to TDSPs; 2026-09-09 Batch Zero Verification RFI; 2026-09-14
     Community Impact RFI (computational loads ≥25 MW not yet energized), **due 2026-10-12, 5 pm CT**. Two
     workstreams: Batch Zero audit (≥75 MW) and community-impact audit (≥25 MW). Reported 2026-09-23 (Sidley,
     headline only): the governor's environmental-permitting freeze extends the pause to all Texas data
     centers pending a statewide audit. Related PUCT projects 58481 (16 TAC §25.194 large-load rule; adoption
     expected at the 2026-09-18 open meeting), 59142 (ERCOT batch study), 58000 (4CP→12CP), 58482 (large-load
     demand-reduction service). **Baseline row for Batch Zero is wrong** ("Effective 2026-07-11", next
     "Batch 1 applications open 2027-06-30"). TX has zero rows dated August 2026.
  2. **Arizona — Microsoft's Closing Brief in the APS rate case.** ACC image **E000054018**, docket
     **E-01345A-25-0105**, docketed **2026-08-27**, 50 pp. (brief pp. 1–24; exhibits MSFT-6, -7, -9, -16).
     Asks: AG-XHLF rider expanding AG-X (capped at 200 MW) to all uncommitted large load with third-party
     generation and WRAP resource adequacy; tri-party PPAs under XHLF revisions; reject or cap the formula
     rate (FRAM) at 3–4%/inflation with bring-your-own-generation; reject "class pays for growth" and annual
     cost-of-service reallocation; reject the XHLF applicability change; Load Commitment Agreement stakeholder
     review (challenges minimum demand at 80% of full buildout from day one, and minimum energy charges);
     CIAC/AIAC for generation only at customer election; large-load queue reform; Fair Value Return increment
     (~$121.8M) to zero; AED-4CP instead of A&P. On the record (MSFT-15): **APS has not committed to serve
     any new large load since 2024-01-01.** KJZZ 2026-09-02: Microsoft opposes APS's ~45% data-center
     increase; APS reports ~4,000 MW committed to data centers and a 9,100+ MW peak in early Aug 2026.
  - **Why they were missed:** collection followed docket numbers (58317 and ERCOT notices weren't watched; a
    governor's directive has no docket; "Abbott" appears nowhere in the data); the backfill never read the
    inbox (RTO Insider 9/15, CapIQ 9/14–15, NPM 9/15 all carried it); the tracker is keyed by utility, so
    customer/intervenor filings had no slot; ACC docket listing needed the eDocket POST API, which v1 cloud
    runs couldn't call.
- **v3 remedies now in place:** collector enumerates full docket activity (AZ verified), watches PUCT 58317,
  governors' newsrooms (TX, VA, GA, AZ, PA, OH, LA, NC) and PUCT news, tags filings by **watched parties**
  (Microsoft, Google, Amazon/AWS, Meta, Oracle, OpenAI, CoreWeave, Data Center Coalition, developers, IPPs,
  industrial and intervenor groups); the Sweep runs a **newsletter canary**; the **corrections queue**
  (`prompts/corrections_queue.md`) has the Sweep verify and write both misses; a **one-off docket-activity
  backfill from 2025-11-07** for the 10 collector states was dispatched on 2026-10-02 (`data/backfill/`,
  processed ~10 documents per Sweep until exhausted); manual-route states get history via the manual pass.

**Corrections queue (verified at source by the Sweep before writing; up to 6 per run):**
C-01 Texas directive / Batch Zero pause and overlay of the stale Batch Zero row · C-02 Microsoft APS brief ·
C-03 Arizona XHLF eligibility (≥5,000 kW, ≥92% load factor in 9 of prior 12 months; 15,000 kW for
econ-dev/sustainability features; 50 MW/customer/yr and 500 MW aggregate caps; A.C.C. No. 6067 Rev. 3, eff.
2024-03-08, Decision 79293) — closes the XHLF gap; exhibit APS-54 no longer needed · C-04 Louisiana U-37882
milestone (see §9) · C-05 store housekeeping (flags; truthful `backfill_state.json`) · C-06 Texas text quality
(see §8) · C-07 docket-activity backfill (ongoing).

---

## 8. How to reach each source (access findings)

**Collector conduct (non-negotiable):** honest UA `BlueOwl-RegTracker/4.0 (rett.young@blueowl.com)`;
robots.txt per RFC 9309 (2xx parse; 4xx no rules; 5xx/unreachable = disallow; firewall page served as
robots.txt = disallow; HTML app shell = no robots file; strip BOM); ≥3 s between requests per host; fetch only
watched items; block pages recorded as BLOCKED, never parsed; no CAPTCHA solving, stealth, IP rotation,
logins or third-party proxies; **never disable TLS verification** — incomplete chains are completed via the
leaf's AIA intermediate, with verification still on.

| Jur./source | Route | Working method and status (2026-10-02) |
|---|---|---|
| FERC | collector | eLibrary JSON API: `POST elibrary.ferc.gov/eLibraryWebAPI/api/Search/AdvancedSearch` (date + docket searches), downloads via `File/DownloadP8File`, docket sheets via `Docket/GetSingleDocketSheet`. Works (199 items first run). |
| Federal Register | collector | API, agency + term filters. Works. |
| SEC EDGAR | collector | Declared UA opens it (Akamai 403'd an undeclared tool). Works. Forms 8-K (2.02, 7.01, 8.01, 1.01, 2.01), 10-Q, 10-K, 40-F, 6-K. CIKs: Fortis 0001666175 (40-F), TXNM 0001108426, Oncor 0001193311, Nevada Power 0000071180. Quarterly 8-Ks from Duke, AEP, Southern, Entergy carry the release only; Pinnacle West, Dominion attach decks. |
| AZ | collector | `POST efiling.azcc.gov/api/edocket/searchByDocketDetailRequest` with **exactly** the documented fields (extras silently return nothing); `GET /api/edocket/docket/{docketID}` returns the full document list with imageNumber (2.2 MB JSON for the APS case). PDFs at `images.edocket.azcc.gov/docketpdf/{img}.pdf` (incomplete TLS chain → AIA). `docket.images.azcc.gov` is robots-disallowed — never use it. Consumer-comment letters skipped. **Working** (243 filings since June in test). |
| GA | collector | `psc.ga.gov/search/service-facts-docket/?docketId=…`; documents via `services.psc.ga.gov/api/v1/External/Public/Get/Document/DownloadFile/{doc}/{file}`. Works. |
| TX | collector | Interchange filing lists; `interchange.puc.texas.gov/Documents/{ctrl}_{item}_{id}.PDF/ZIP`. ~1 in 3 files returned 402 through WebFetch; spreadsheets sit in ZIPs (collector handles). **Text quality:** a later session found a clean text layer except the letterhead seal, contradicting v1's "all OCR, capped at Reported" — judge per document by the collector's quality flag (C-06 confirms). Works (65 items). |
| LA | collector | Valence portal: `POST …/portal/PSC/DocketSearch` → MatterId; `Docket_Documents`; `RecentOrders`; `ViewFile?fileId=`. Ligature-corrupted text: summarize, never quote. Works (U-37921 not found by number). |
| MO | collector | EFIS: anti-forgery token from `Case/NewSearch`, `POST /Case`; case numbers paired with nearest `Case/Display/{id}`; filings via `Case/FilingDisplay/{id}`. **Fixed 2026-10-02** (600 cases in test). |
| NM | collector + manual | e360: `POST /core/api/apiflow/v1/prc/nm/intake/casedetails/getAll` with the CaseX envelope works. Documents via `casepublicdocument/getAll` (queryParams ['caseId']) **returns empty** with the recorded envelope — open; then `downloadToken` → `previewDocument` (1-hour TTL). Old `edocket` retired. |
| KS | collector | Commission meeting-minutes PDFs at `kcc.ks.gov/commission_meetings_files/minutes_YYYYMMDD.pdf` (cheap, citable). `kcc-connect` is Salesforce with shadow DOM; detail pages need the 15-char Salesforce id, not the docket number; old `estar` dead. |
| OK | collector | OCC Laserfiche WebLink (`public.occ.ok.gov`) **recovered 2026-10-02** after HTTP 500s from 18 Sept. Search form `ImagedCaseDocumentsfiledafter3212022`; the case-number field matches the bare number (`2026-000031`), which also hits other OCC case types, and the listing carries no metadata. The page-text service (`DocumentService.aspx/GetTextHtmlForPage`) returned `ObjectNotFoundException` for these entries, so the collector now keeps the 8 newest hits unconfirmed and the Sweep confirms from the PDF text. Applicant field is exact-match in CAPS (`OKLAHOMA GAS AND ELECTRIC COMPANY`); electric tariffs file under Document Type "Application". Never `ecf.public.occ.ok.gov`. |
| GRDA (OK) | collector | No commission docket. Monthly board agendas/minutes at `grda.com/leadership/board-meeting-agenda-minutes/`. |
| AL | collector + web | PSC RSS endpoints returned **HTTP 500 (server fault)** on 2026-10-02; docket pages are server-rendered and readable by WebFetch (`pscpublicaccess.alabama.gov/pscpublicaccess/ViewFile.aspx?Id=<GUID>`; Act 610 docket 33709). |
| PA | Sweep web reader | GitHub runners get a TLS failure and a 5xx robots.txt; Claude's WebFetch works (`puc.pa.gov/docket/<n>`, `puc.pa.gov/pcdocs/<id>.pdf`). Large-load docket M-2025-3054271. |
| VA | manual (+fallbacks) | SCC robots.txt admits only named search engines. Browser method: Durandal/Breeze SPA — `GET /DocketSearchAPI/breeze/CASES_ESTABDATE/GetCasesEstDate?$filter=startswith(Case_Number,'PUR-2026')`; documents `/DocketSearchAPI/breeze/CaseDetails/GetDocuments?$filter=MATTER_NO eq N`; PDFs `/docketsearch/DOCS/<FileName>`; `Home/Document/12/<id>` 404s; pdf.js loads only after unsetting `window.define`. |
| WV | manual (+fallbacks) | PSC returns 403 to automated clients. Browser: **http:// not https**, `/scripts/WebDocket/` not `/WebDocket/`; in-page fetch of `viewCaseForWebList.cfm`, `tblCaseActivitiesList.cfm`, `ViewText.cfm` (same-site referrer) — the Commission's own OCR text layer, the best document source in the set. |
| SC | manual (+fallbacks) | DMS `Disallow: /`. Browser: `dms.psc.sc.gov/Web/Dockets/Detail/<internal id>` (2026-138-E = 119719; 2026-186-EG = 119767). Cloud fallback: PSC latest publications, ORS electric page. |
| IL | manual (+fallbacks) | ICC `Disallow: /` + CAPTCHA. Browser: BROWSE route `POST …/browse/docket_detail.asp` with `no=<docket>&go=Go`; never Search.aspx. Fallback: CUB. (A probe BOM bug once fetched one ICC page despite the disallow; fixed and disclosed.) |
| OH | manual (+fallbacks) | PUCO DIS firewall rejects automated clients, even on robots.txt (F5 "Request Rejected" served as 200 — parsers guard against it). Fallback: Ohio Consumers' Counsel filings. |
| NC | manual (+fallbacks) | NCUC `starw1` behind a Cloudflare challenge. Documents open via `ViewFile.aspx` once a GUID is known; WebSearch restricted to `starw1.ncuc.gov` harvests GUIDs (lags days–weeks); NCUC subscription mail if already arriving. NCUC main-site PDFs as fallback. |
| NV | manual | `puc.nv.gov` disallows all bots; `pucweb1.state.nv.us` holds pre-Oct-2023 dockets; no text layer on any document; metadata-only ceiling. |
| RTOs | collector | Watch pages for CAISO, ERCOT (market notices, news), SPP, NYISO, ISO-NE, MISO, WPP; NERC news; FERC news. **PJM Inside Lines RSS now serves a CAPTCHA** — PJM content comes via FERC dockets and RTO Insider. |
| Investor decks | collector | Events-and-presentations pages rendered and PDF links harvested (never guessed; filenames change between quarters; `sNN.q4cdn.com` CDN is not bot-protected; patterns `/doc_financials/<year>/<q>/<file>.pdf`, `/doc_presentations/<year>/<Mon>/<DD>/`). Working for 10 of 16. **Blocked:** Southern (Incapsula), Evergy, Exelon, OGE, Oncor (robots.txt), BHE (CAPTCHA) → decks from EDGAR exhibits or search for the q4cdn PDF; the refusing pages are never fetched. Traps: Ameren is amereninvestors.com; Pinnacle West is www.pinnaclewest.com; PPL not on Q4; Evergy/Exelon decks are GUIDs; TEP has no deck (use Fortis); NV Energy none (use BHE, twice yearly). |
| Mail | Sweep | Folders "FERC", "ERCOT"; senders `today@rtoinsider.com`, `alerts@newprojectmedia.com`, `alerts@capitaliq.spglobal.com`, NCUC; DCC Bi-Weekly State Regulatory Update (PDF attachment forwarded by hadams@bealeinfra.com to BODIpower@blueowl.com; read via `read_resource`). RTO Insider RSS holds ~10 items / ~7 hours — cross-check only, never a primary source. Internal deal threads (Crusoe, STACK, Beale, Bobcat, etc.) are confidential and **never** sources. |
| Keyed data | collector (wired) | EIA v2, congress.gov, Open States — activate by adding free keys as repo secrets `EIA_API_KEY`, `CONGRESS_API_KEY`, `OPENSTATES_API_KEY`. LegiScan blocks by IP. CapIQ API is POST-only with token auth (a collector could call it); state docket content lives in S&P RRA, a separate entitlement. |

**General browser techniques (manual pass):** navigate the tab to the PDF and inject pdf.js (the document
response usually has no CSP); `window.open` interception to capture JS-driven document URLs (KS, NV, OK);
in-browser OCR via pdf.js → Tesseract.js (prose ~93%, numerals ~85% — never write an OCR number as fact).

**Entity aliases are mandatory** (querying the tracked short name returns nothing): Dominion = Virginia
Electric and Power Company; AEP Ohio = Ohio Power Company; PPL = PPL Electric Utilities Corporation; Evergy =
Evergy Kansas Central, Inc. / Evergy Metro, Inc. / Evergy Missouri West; Duke SC = Duke Energy Carolinas, LLC /
Duke Energy Progress, LLC; Ameren = Union Electric Company; ComEd = Commonwealth Edison Company; PNM = Public
Service Company of New Mexico / TXNM Energy; full list in `config/watchlist.yaml`. Renamed filers: Westar →
Evergy; PNM Resources → TXNM.

---

## 9. Registry corrections — facts that were wrong (do not resurrect)

| Claim | Reality |
|---|---|
| `WV 26-0130-E-CN` is large-load | ApCo/Wheeling Power **cooling-tower CPCN at Mitchell Plant**. Not large-load. |
| `VA PUR-2026-00114` does not exist | **It does** (MATTER_NO 147082): **NOVEC**, revisions to LP-1/DPS/HV-1/HV-2, interim-effective 2026-09-01, hearing 2027-04-21. First mis-attributed to Dominion, then wrongly struck — a correction to a prior correction. |
| `NM 25-00082-UT` is PNM's rate case | **El Paso Electric's.** PNM had filed no rate case as of 2026-09-18. |
| Kansas LLPS is `26-EKCE-0258/0259/0480/0540` | None of them (Transmission Delivery Charge; Annual Energy Cost Adjustment; KEEIA DSM; Renewable Energy Program Rider). The LLPS docket is **`25-EKME-315-TAR`**. |
| WV "Tin Branch" competing proposal | No such docket; the phrase appears only inside the 2026-08-21 final order in `25-0637-E-CN` (Becco Area Improvement Project). |
| NM EPE Advice Notices 318/319 are large-load | AN 318 = RPS Cost Rider (26-0000092); AN 319 = bill forms (26-0000161). Only **AN 317** (`26-0000062`) carries large-load Rate No. 50. No "Rate No. 51" exists. |
| There is a 2026 Dominion biennial review | There is not. The live docket is the 2025 review, `PUR-2025-00058`, reopened 2026-09-03. |
| Duke Q1 2026 ESA step was +2.7 GW | **+3.1 GW** (Q4 2025 verified 4.5; Q1 7.6). Duke states no late-stage figure for Q4 2025 — leave null. |
| Duke Q4 2025 was one event | Recorded twice — `E-20260918-035` (wrong date, Reported; now superseded) and `E-20260918-132` (Verified). |
| AZ XHLF threshold "not established" | Established in the record: ≥5,000 kW, ≥92% LF in 9 of 12 months (C-03 writes it). |
| Batch Zero "effective 2026-07-11, next Batch 1 2027-06-30" | Stale — paused since 2026-08-10 pending verification (C-01). |

**Louisiana U-37882 — unresolved conflict, queued as C-04.** One session read the LPSC order as decided at
the 2026-04-15 B&E session, order issued 2026-05-14. Another established that the LPSC took original
jurisdiction on 2026-05-14 and set a **2026-12-16** vote on certifying ~5,200 MW for Entergy/Meta. The Sweep
reads the docket's newest orders and keeps or corrects the 2026-12-16 milestone. Background: filed 2026-03-25
for Evest LLC, Richland Parish, adjacent to the Laidley facility (U-37425), under the LPSC "Lightning
Directive" of 2025-12-17; claims ~$2.67bn of benefits to other ELL customers.

---

## 10. Structural findings, explicit negatives, watch signals

**Structural findings (change what to look for):**
- **Kansas ESAs are never docketed.** Evergy executes large-load ESAs under the approved LLPS tariff with no
  KCC filing; an enumeration of all 337 Evergy Kansas Central and Metro dockets found nothing for the reported
  ~600 MW Digital Realty ESA. Only special contracts outside the tariff are docketed (Panasonic,
  `26-EKCE-110-CON`). A Kansas zero on ESAs is correct; use Evergy investor disclosure.
- **GRDA has no commission docket**; board agendas name counterparties (Google is a named Large General
  Service–Industrial customer) but never MW, price or term.
- **Entergy never states an absolute signed-ESA GW figure** — only a percentage backlog change and a pipeline
  range above base case.
- **Ameren's construction-agreement total includes ESAs**; the without-ESA figure is never stated and must
  never be derived.
- **Exelon changed disclosure methodology at Q2 2026** (~11 GW not comparable to prior ~18–19 GW).
- **TXNM/PNM has published nothing since 2025-05-19** pending the Blackstone acquisition — a market fact.

**Explicit negatives (real zeros — never flag as failures):** Arizona TEP (no large-load tariff, rate case or
data-center contract in the window); Kansas (no generic large-load proceeding); West Virginia (no docket
mentions Google, "data center" or "large load"; best unverified candidate 24-0611-E-T-PW, not registered);
South Carolina (no "data center" docket — large load runs through generic 2026-138-E); GRDA Feb and Mar 2026
agendas (immaterial).

**Watch signals:** GRDA confidential "economic development" executive sessions rose from 1 (Feb) to 5 (Aug
2026), plus a September session on PPAs; capital work orders shown 100% reimbursed with zero net GRDA cost
(e.g. Rocky Point substation $10.9m, July) signal a single large customer funding its own interconnection.

---

## 11. Benchmarks and standing facts

**Conversion series (verified at source; the brief reports quarter-over-quarter deltas, not levels):**

| Issuer | Series | Note |
|---|---|---|
| AEP | contracted 56 → 63 → **69 GW** | |
| PPL | advanced-stage 20.5 → 25.2 → 28.3 → **31.8 GW**; ESA 11.0 | |
| Dominion | SELOA/CLOA/ESA — Dec 25: 27.4/11.0/10.2 · Mar 26: 29.5/11.1/10.4 · Jul 26: **32.4/9.4/12.0** | CLOA falling while ESA rises — conversion, not growth. Only series consistent across all three stages. |
| Duke | ESA 4.5 → 7.6 → **7.8 GW**; late-stage 15.4 (Q2) | +3.1 then +0.2 — sharp deceleration |
| Ameren | ESA 2.2 → 2.2 → **2.8 GW**; construction agreements 3.4 GW MO (inclusive) | whole step in Q2 |
| Southern | **17 GW** contracted / 75+ GW prospective | 31 projects; Georgia Power 12.5 |
| Oncor | **38 GW** RTP-qualifying / 226 GW queue | |
| APS | **4.5 GW** committed | flat for several quarters |
| Evergy | Tier-1 expansion 2.0–2.5 GW (prior 1.0–1.5) | |
| Exelon | ~11 GW advanced/TSA (ComEd ~9) | new methodology Q2 2026 |
| Entergy | ESA backlog +85% vs 2024; pipeline 10–17 GW above base case | no absolute figure |

**Tariff template (tight convergence — a deviation is the story):**

| Utility | Threshold | Term | Min take | Notice |
|---|---|---|---|---|
| EPE (NM) Rate No. 50 | 30 MW, 85% LF | 20 yr | 80% | — |
| Evergy (KS) LLPS | 75 MW | 12 + 5 ramp | 80% | 36 mo |
| Ameren (MO) | 75 MW | 12 yr | 80% | 24 mo |
| ApCo (VA) Schedule L.P.S. | 100 MW / 150 aggregated | 14 yr incl. 4 ramp | 80% | 42 mo |
| Dominion (VA) GS-5 | 25 MW | 14 yr | 85% T&D / 60% gen | — |
| APS (AZ) XHLF | 5,000 kW, 92% LF | — | — | — |

Collateral clusters around two years of minimum bills. Legislative template: 50–150 MW thresholds, 75–85%
minimum take, 10–15 year terms, exit fees, collateral, cost-shift bars; West Virginia HB4983 is the outlier
(qualifying loads may exit via microgrids).

**Standing facts:**
- FERC §206 large-load dockets EL26-67 (PJM), -68 (SPP), -69 (NYISO), -70 (MISO), -71 (CAISO), -72 (ISO-NE),
  instituted 2026-06-18, in abeyance; five end ~**2026-11-12**, SPP's fixed **2026-11-20**. Check for
  extension or expiry — it would be the biggest item of the week.
- **EL25-49 co-location** is live: PJM compliance tariff language 2026-08-17; Constellation protest 2026-09-08;
  PJM TOs filed only partial compliance.
- ERCOT: >438,000 MW of large-load requests (~89% data centers); long-term forecast ~367,790 MW by 2032 vs an
  85,508 MW peak.
- PJM: second consecutive shortfall auction — 138,318 MW cleared at the $325/MW-day cap, 6,831 MW short.
- **Virginia Rider T1** (`PUR-2026-00056`, final 2026-07-31) is where transmission cost moved onto large load
  (amended 12-CP factor folding in the GS-5 minimum demand charge). **Microsoft has appealed.** GS-5 takes
  effect 2027-01-01 with six customers opted out to GS-4. Dominion's line-extension/CIAC docket ordered there
  has no case number yet (filing was due within 90 days of 2026-07-31).
- Four baseline rows on appeal, including Virginia Rider T1 (Microsoft) and ApCo Schedule L.P.S. (Retail
  Energy Advancement League).

**Milestone calendar (from `state.json`, with status notes):**

| Date | Item | Note |
|---|---|---|
| 2026-09-30 | Duke NC large-load tariff filing due; Ameren Missouri triennial IRP (~3 GW requested) | past — outcome needed |
| 2026-10-01 | Alabama Act 610 effective (review at 150 MW+); MISO BPM-032 v1.0 due | past — outcome needed |
| 2026-10-12 | ERCOT Community Impact RFI responses due (5 pm CT) | add once C-01 verifies |
| 2026-10-14 | GRDA board (Google LGS-Industrial schedule; WP-SS rider) | |
| 2026-10-20 | ApCo Virginia rate case hearing, PUR-2026-00044 | |
| 2026-10-26 | SC large-load workshop 2026-138-E (26–27 Oct); WV MARL 500 kV hearing 26-0075-E-CN (to 2 Nov) | |
| 2026-10-31 | WRAP Forward Showing deadline (first binding season, Summer 2027) | |
| 2026-11-12 | FERC §206 abeyance ends — PJM, NYISO, MISO, CAISO, ISO-NE | |
| 2026-11-17 | Dominion GS-5 compliance filing due | |
| 2026-11-20 | FERC §206 abeyance ends — SPP | |
| 2026-11-30 | OG&E Extra Large Power & Light hearing | reported; docket and name unverified |
| 2026-12-16 | LPSC vote on ~5,200 MW Entergy/Meta, U-37882 | under review (C-04) |
| 2026-12-31 | PJM Connect-and-Manage load-shed allocation rules due; NYISO board approval and FERC filing targeted | |
| 2027-01-01 | Dominion GS-5 takes effect | |
| 2027-03-06 | WV MARL decision due | |
| 2027-04-21 | NOVEC tariff hearing, PUR-2026-00114 | |

**Remaining gaps (as carried in `state.json`, with v3 status):** Oklahoma's two Unverified rows
(PUD2026-000031, reported OG&E special contract, counterparty reported as Google; PUD2026-000046, reported
"Extra Large Power & Light" tariff) — portal now reachable, confirmation in progress; Arizona XHLF — closable
(C-03); Virginia CIAC docket number — watch; Kansas `26-EKCE-148-STG` (133-mile Buffalo Flats–Delaware 345 kV)
— excluded on materiality; Texas "capped at Reported" — under review (C-06).

---

## 12. What happened on 2 October 2026 (this session)

1. **Reachability probe** from GitHub Actions: open hosts confirmed; six commissions closed by their owners
   (VA, SC, IL, OH, NC, WV); PA open only to Claude's reader; EDGAR opened by the declared UA.
2. **Decisions by Rett:** use the work email in the UA; pursue (1) agency allowlist letters and (2) automatic
   fallback to permitted-host copies; Excel tracker is the primary deliverable with a narrative alongside; set
   up a second, manual process for gaps; web fetching always permitted.
3. **Built the v3 system** described in §4: collector (15 adapters plus governor/party watching, health,
   circuit breakers, 70-minute run deadline with rotating start and per-source checkpoints, per-list
   baselining, backfill mode, AIA chain completion); row-store overlays and validation; exact Excel replica in
   Python and in the browser with CI parity; narrative PDF/DOCX; console v6 (in-page Excel download, narrative
   section, status) — also fixed a script error that had stopped the earlier console from loading; Sweep and
   Brief v3 prompts; corrections queue; manual-pass skill (saved); `SOURCES.md`.
4. **Allowlist drafts** created in Outlook (not sent): VA `sccinfo@scc.virginia.gov`; NC
   `clerkhelpdesk@ncuc.gov`; SC `contact@psc.sc.gov`; IL `ICC.FOIARequests@Illinois.gov` (asks to route to the
   Chief Clerk); OH (no address — PUCO web form or 614-466-6843); WV (no address — Executive Secretary form or
   304-340-0426).
5. **First collector run:** 334 new items, 160 documents extracted, ~20 minutes. Afterwards fixed Arizona,
   Missouri, Oklahoma (partly), TLS chains; added PUCT 58317, party watch, governor and PUCT news pages.
6. **Scheduled** the Sweep and Brief (§3) and **dispatched** the docket-activity backfill.

**Status at 17:00 PT:**
- Excel parity: passing (0 differences).
- A collector run at ~16:24 PT finished but its data push failed silently; the health-issue step also
  failed. Both steps rewritten (rebase keeps the newer data file; push failure now fails the job; issue lookup
  via REST). The fixes take effect from the next run.
- A collector run started ~16:39 PT on the older commit step; the backfill run is queued behind it.
- Oklahoma: confirmation via page text failed; now keeps 8 newest hits unconfirmed for the Sweep to check.
- Open source issues: NM documents endpoint; AL RSS (server 500); PJM Inside Lines CAPTCHA; six blocked IR
  pages (covered by EDGAR/q4cdn).

---

## 13. Sources

Full lists in `claude/sources-v3.md` (repo `SOURCES.md`).

**In scope:** FERC eLibrary, FERC news, Federal Register, NERC; SEC EDGAR for 18 utility issuers (AEP,
Southern, Duke, Dominion, Entergy, Evergy, Exelon, Ameren, PPL, Pinnacle West, Xcel, OGE, TXNM, Oncor, Fortis,
Nevada Power, NiSource, FirstEnergy) and 17 market participants (Constellation, Vistra, NRG, Talen, NextEra,
Microsoft, Alphabet, Amazon, Meta, Oracle, Digital Realty, Equinix, CoreWeave, Applied Digital, IREN, Core
Scientific, GE Vernova); all 8 RTOs; all 18 state commissions (routes in §8); 16 IR pages; governors'
newsrooms; party watch; Utility Dive, Canary Media, RTO Insider and PJM Inside Lines feeds; licensed mail.

**Candidates, ranked:** (1) agency allowlisting for the six closed states; (2) free EIA, congress.gov and
Open States keys (already wired); (3) RTO interconnection queue files; (4) ERCOT large-load interconnection
status report; (5) capacity auction results and parameters; (6) CourtListener/PACER; (7) state appellate
courts; (8) governor EO pages for the remaining states; (9) county zoning/planning agendas; (10) direct
state bill trackers; (11) utility IRP/RFP portals; (12) DOE GDO/LPO and 202(c) orders; (13) NRC ADAMS for
restarts/uprates/SMRs; (14) hyperscaler newsrooms; (15) earnings call transcripts; (16) S&P RRA / Halcyon /
Energy Strategies / DELTa as cross-checks; (17) LBNL / Grid Strategies studies; (18) Colorado and Oregon;
(19) FERC Form 1 / EQR (defer).

---

## 14. Outstanding actions

**Rett:**
1. Disable any desktop-local copies of the old tracker tasks.
2. Send the six allowlist drafts (OH and WV through their web forms).
3. Optional: add the EIA, congress.gov and Open States keys as repo secrets.
4. Optional: run the manual pass before Monday 5 October so the first report covers the blocked states.

**Decisions still open:** Colorado and Oregon in scope?; recipients after burn-in (only Rett now; possibly
BODIpower@blueowl.com later); whether a personal GitHub repo is acceptable under Blue Owl policy long-term (an
Azure Container Apps job is the fallback, which needs IT); a Blue Owl branding template for the narrative;
send mode stays auto-send unless changed.

**Next session should first:** check the Monday 5 October Sweep run record (`/GridDocket/runs/`) and Brief
record (`/GridDocket/briefs/`); confirm the backfill completed (`data/backfill/`); read the collector health
issue on GitHub; confirm both scheduled tasks are still enabled (a disabled task emits no failure notice).

---

## 15. Process lessons (do not repeat)

- **Test every access method in the exact runtime it will run in.** v1 validated methods in a session with a
  browser; the scheduled task ran without one, deferred every source, and wrote nothing.
- **Connectors attach per scheduled task**; confirm M365 is attached (both v3 tasks have M365 and Box).
- **Cron is UTC unless `CRON_TZ` is set.** Both v3 tasks use `CRON_TZ=America/Los_Angeles`.
- **A disabled task emits no failure notice** — two Mondays passed silently. Verify tasks are enabled after
  any change.
- **Never set `last_successful_sweep` to the baseline date without intent** — v1's first run had a
  zero-length window.
- **Subagent budgets overran on 6 of 8 attempts** (worst 205 calls against 60). Scope narrowly (≤3
  jurisdictions), set hard call budgets, hand back partial results.
- **Dedupe on specific document URL, not just docket number**; a shared search-landing URL is not a duplicate
  signal.
- **Check arithmetic between a stated level and a stated change** (the Duke +2.7/+3.1 error).
- **Binary files can't round-trip through the Graph text/base64 path**; artifacts can't serve .xlsx/.docx —
  build the workbook in the browser and commit the canonical copy to the repo.
- **LibreOffice recalc times out on styled workbooks** — verify formulas on a stripped copy.
- **ExcelJS treats column width 9 as default and omits it** (write 9.001); `<col>` spans group equal widths
  (expand before comparing).
- **From Claude sessions:** GitHub GraphQL is unavailable (use `gh api` REST); GitHub Actions log downloads
  are blocked (have jobs commit diagnostics to `data/debug/`); the workspace shell can't reach most target
  hosts or npm (test in Actions).
- **Workflow concurrency:** one pending run per group — a new push replaces a queued run. Use `[skip ci]` when
  pushing collector changes while a dispatched run (e.g. a backfill) is queued.
- **A robots.txt BOM can hide `Disallow: /`** — decode with utf-8-sig. Distinguish firewall block pages from
  app shells when a site serves HTML as robots.txt.
- **Claude-side failures worth remembering:** turns closed silently without answering; a scheduled task bound
  to a local folder while its own rule said "nothing local"; a dashboard that was a prettier email; a console
  shipped with a script syntax error. Check the page loads after every publish.
