# Grid Docket — context document

**Weekly large-load and generation regulatory tracker for Blue Owl Digital Infrastructure (BODI).**
Owner: Rett Young (rett.young@blueowl.com). Rewritten 3 October 2026; supersedes all earlier handoff, session and
context files.

This is the single reference for anyone (person or Claude session) picking up the project: what it is, the
rules Rett has set, where everything lives, how it runs, the state of the data, how each source is reached,
what's still open, and the lessons that cost time. Sections 5, 13, 14 and 15 are decisions and verified facts —
change them only on new evidence. When this document and the repo disagree on mechanics, the repo's
`prompts/sweep.md` and `prompts/brief.md` are what actually runs.

**Contents:** 1 What this is · 2 Standing constraints · 3 Where everything lives · 4 Architecture · 5 Schema ·
6 Current data · 7 Coverage history and catch-up · 8 Access by source · 9 API keys · 10 Refused sources and
alternatives · 11 ERCOT · 12 Manual pass · 13 Registry corrections · 14 Structural findings · 15 Benchmarks and
milestones · 16 Verification record · 17 Sources · 18 Outstanding actions · 19 Process lessons · 20 Change log

---

## 1. What this is

A fully automated weekly market and regulatory tracker for **large-load (data-center) customers and large
generators**. It covers **25 named utilities, 8 RTOs and 18 jurisdictions**, oriented to data-center siting and
power procurement.

**Jurisdictions (18):** AL, AZ, FERC, GA, IL, KS, LA, MO, NC, NM, NV, OH, OK, PA, SC, TX, VA, WV (plus
`US-Federal` for federal items with no state). Colorado and Oregon are out of scope for now (Rett, 3 Oct 2026).

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
- **Keys go in repo secrets, added by Rett.** Claude cannot enter API keys, tokens or passwords itself — this
  is a fixed limit on Claude, not a judgement about the keys (Rett regards these keys as non-sensitive). Free
  keyless routes (public DEMO_KEY, keyless APIs) are used wherever they exist so this step is rare. Add secrets
  at https://github.com/rettyoung/BODI/settings/secrets/actions/new. Never store secrets in an artifact or the repo.
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
- **The repo is public (Rett's decision, 3 Oct 2026)** so the scheduled tasks can read it without credentials.
  Nothing secret may ever be committed to it; collected material is public filings plus code and the watch list.

---

## 3. Where everything lives

### OneDrive — the system of record

```
driveId       b!2OnbGRjzpEKUL9fVRRC4Lv4LSN1Bpb1PmI1aJZgbWGvvNTw6Z-6ISI31RRmmeISO
/GridDocket/  01MLUCMYJFKKTYR6ENBFDZOOAQQOLD5QNX
  manual/     01MLUCMYLTL2DGJ4AHFBB2OJSZMLMPBRJU   manual-pass drops
  runs/       01MLUCMYNQE5VMUQYLERCIPHUAB5IL4B4E   one record per Sweep run
  briefs/     01MLUCMYPB3OSQIZONA5FLUGQHMAZGKC3U   one record per Brief run
webUrl        https://blueowlcap-my.sharepoint.com/personal/rett_young_blueowl_com/Documents/GridDocket
```

| File | What it is |
|---|---|
| `state.json` | **Read first.** Window (`last_successful_sweep`), `last_brief_date`, registry corrections, structural findings, access methods, explicit negatives, remaining gaps, watch signals, standing facts, pipeline baselines, milestone calendar, `manual_ingested`, `corrections_done`, `backfill_cursor`. The Sweep owns it; the Brief changes only `last_brief_date`. |
| `rows.json` | **A manifest, not rows** (v2). Lists the part files in order: `rows_p1..p5`. |
| `rows_p1..p4.json` | The 229 baseline rows (58/58/58/55). 26-element positional arrays; column names once, in `rows_p1.columns`. |
| `rows_p5.json` | First v3 part (3 Oct, degraded run): 19 events / 24 rows plus 2 overlays on `E-20260918-098`. |
| `seen_index.json` | Dedupe index, time-bounded at 180 days. |
| `metrics.json` | Pipeline series (43 points, 11 issuers) — drives the conversion charts. This OneDrive copy is authoritative. |
| `tariff_terms.json` | Structured tariff terms (10 tariffs) — drives the comparison matrix. |
| `backfill_state.json` | The original v1 backfill queue. Stale; corrected by corrections item C-05. |
| `sweep_lock.json` | Single-writer lock. |
| `manual_queue.json` | What the next manual pass should read (written by each Sweep). |
| `runs/2026-10-03-0019.json`, `briefs/2026-10-03.json` | Records of the 3 Oct verification runs. |
| `README.md` | Folder guide. |

**Why parts:** a single Graph write is capped at 1,048,576 bytes. Each Sweep writes a **new** part (`rows_p6.json`
next) and appends it to the manifest. It never rewrites an existing part.

### GitHub — `rettyoung/BODI` (public since 3 Oct 2026)

Public so the scheduled tasks can clone it with no credentials. Nothing secret is ever committed; API keys live
in repo secrets, which stay private on a public repo.

| Path | What it is |
|---|---|
| `collector/` | `common.py` (HTTP, robots, extraction, AIA chain completion), `adapters.py` (commission, watch-page, RSS, IR, mirror, FERC, Federal Register, EDGAR adapters), `adapters2.py` (EIA, congress.gov, Open States, CourtListener, MISO/SPP/PJM queues, Legistar), `adapters3.py` (wave 3, 3 Oct: Supreme Court of Texas, local agendas, ERCOT large-load status, NYISO ICAP, NRC ADAMS, FERC Form 1/3-Q/714 and EQR, LBNL via OSTI), `run.py` (orchestrator, budgets, checkpoints, baselining, backfill), `backfill_text.py` (nightly enrichment of the docket-history backfill), `discover.py` and `probe_adapter.py` (repair tools; `urls:<list>` probes candidate URLs from the runners) |
| `config/watchlist.yaml` | **The single place to add or drop coverage**: 56 keywords, jurisdictions and routes, watched dockets, entity aliases, party watch list, EDGAR issuers, Federal Register terms, 45 watch pages, 13 RSS feeds, 16 IR pages, 5 mirrors, 4 queues (MISO, SPP, PJM serial, PJM cycle), 9 Legistar clients, 7 other agenda lists, court, OSTI and Open States queries, NRC dockets, FERC form filers, EQR counterparties |
| `data/` | Collector output: `candidates/<date>.jsonl`, `filings/<jur>/<source>/<id>.json` (full text), `health/`, `state/`, `backfill/`, `debug/`, `tests/` |
| `store/` | Frozen copy of the 2026-09-18 baseline (`rows_p1..p4`) for tests and CI. Not a mirror: scheduled runs download the live store from OneDrive into `store_live/` |
| `tracker/` | `vocab.py`, `rowstore.py` (load, overlays, validation CLI), `build_tracker.py` (canonical Excel), `build_console.py` (console package), `narrative.py` (PDF/DOCX) |
| `console/` | `index.html` (console page), `tracker_xlsx.js` (in-browser Excel builder), `annotations.json` (hand-maintained coverage marks, matter labels, party groups, per-state coverage notes, console URL) |
| `prompts/` | `sweep.md`, `brief.md` (**the live instructions** — the scheduled tasks read these at run time), `trigger_sweep.txt`, `trigger_brief.txt` (the bootstrap prompts loaded into the tasks), `corrections_queue.md` |
| `manual/SKILL.md` | Copy of the manual-pass skill |
| `deliverables/` | Weekly Excel master and narrative when built from a session that can push (scheduled runs cannot) |
| `SOURCES.md`, `docs/` | Source lists; this document (`.md` and `.docx`) |
| `.github/workflows/` | `collect.yml` (nightly + backfill dispatch), `xlsx-parity.yml`, `adapter-probe.yml`, `discover.yml` |

### Console

Published artifact **https://claude.ai/artifact/JJ8FYdvfZ2WPg6r4UpFXbW** — **version 8** (4 Oct 2026; repo commit
fbcce31). Private to Rett until shared. Declares the `downloads` capability so a reader can save the Excel tracker
(built in the page), the narrative PDF and the narrative markdown. Supporting files: `data.json` (events + full
26-column table + the store's change history, coverage, annotations and party list), `metrics.json`,
`tariff_terms.json`, `status.json`, `narrative.md`, narrative PDF. Republished to the same URL by each Brief; `icon`
and `capabilities` carry forward and are never re-passed.

Sections (v8): 01 Status · 02 **What changed** (new events, overlays before → after with reason, supersessions and
moved milestones since the previous brief or any earlier run, replayed from the parts by `build_console.py`) · 03 This
week (narrative) · 04 Decision calendar · 05 **Matters** (per-docket chronologies read from the Document column; labels
in `annotations.json`) · 06 **Load-scenario tariff tester** (MW, load factor, state, optional $/kW-month assumption →
applies?, minimum billed MW, MW-years, collateral estimate, notice, deviation from the median; the full terms matrix
beneath) · 07 Conversion (levels, **quarter-over-quarter deltas**, Dominion ladder and **CLOA → ESA ratio**) · 08
**Activity over time** (weekly, by subject or state, by event or discovery date, with numbered coverage marks) · 09
Where the pressure is · 10 **Parties** (watched parties found in row text — a mention is not necessarily a filing) ·
11 **Coverage** (tile map: route, days since last successful read, explicit negatives, open gaps, "quiet or blind
spot" verdict; nightly collector strip) · 12 Console (adds a period filter and **Copy link to this view** — filter
state in a plain `#v1.<base64url>` anchor, the only form an artifact link passes to the page). Every view degrades
gracefully on the repo-less path. When a source family starts, stops or is backfilled, add a dated line to
`annotations.json` → `coverage_marks` (needs a session that can push).

The four v1 artifacts (Grid Docket Protocol, Docket Watch Live, Docket Facet Schema, Grid Docket Watch) were deleted on 3 Oct 2026.

### Scheduled tasks

| Task | ID | Schedule | State |
|---|---|---|---|
| Utility Tracker Sweep | `trig_01DA4N9G8Qv1zeggHuN9eQ3g` | Mon 03:54 PT (`CRON_TZ=America/Los_Angeles 54 3 * * 1`) | Enabled, auto-approve, M365 + Box. Next run 2026-10-05. |
| Weekly Utility Tracker (Brief) | `trig_01X19jgn9aMSPL5ov1TQ7bvj` | Mon 08:54 PT (`CRON_TZ=America/Los_Angeles 54 8 * * 1`) | Enabled, auto-approve, M365 + Box. Next run 2026-10-05. |
| Grid Docket manual pass (reminder) | `trig_015r1jt1qtx7CEYiyehWzSV2` | Fri 09:04 PT (`CRON_TZ=America/Los_Angeles 4 9 * * 5`) | Runs **on Rett's computer** (desktop app must be open). Push notification; asks "Run now / Skip this week" and does nothing without "Run now". First fires 2026-10-09. |
| Current Events Digest (unrelated) | `trig_01Q57Hm8Enb4TFRrhTZRbpc7` | weekdays 07:28 PT | Not part of this project |

Each task's prompt is a **compact bootstrap** (`prompts/trigger_*.txt`): the invariants that must hold whatever
the repo says (OneDrive IDs, read-only mail, one email to Rett, no credentials/CAPTCHAs), then "clone the public
repo and follow `prompts/sweep.md` / `brief.md`", then a degraded fallback if the clone fails. So **changing
`prompts/*.md` in the repo changes next Monday's behaviour** without touching the tasks.

**Models (set 3 Oct, at Rett's request: Opus where judgment matters, Sonnet where it is enough).**
- **Sweep** runs on `claude-opus-5-5` (triage, classification, verification, corrections, commits) and hands bulk
  reading — per-document fact extraction, mail extraction, health tabulation — to subagents on `sonnet`.
- **Brief** runs on `claude-sonnet-5-5` (setup, status, milestones, build, publish, send, record) and hands the
  synthesis — narrative and email body — to one subagent on `opus`, then checks the email against the
  invariants before sending.
- **Manual pass** (Friday task) runs on `claude-opus-5-5`; Sonnet would do. A task bound to Rett's computer can
  only have its model changed in the desktop app's task settings.
- **Staying current.** Subagents use the aliases `opus` / `sonnet`, which always resolve to the newest model.
  A task's own model is a fixed ID (the platform rejects aliases there), so each run records the models in use
  and asks the alias subagents for their IDs; when a newer one appears, the Brief's STATUS CHECK says so and an
  interactive session updates the tasks (scheduled runs never change their own model).

**Why two cloud tasks, not one.** (1) The Brief is the watchdog: if the Sweep crashes, hangs or never fires, the
Brief still runs and sends the `[No sweep]` failure notice — one combined task would fail silently, the failure
that already cost two Mondays. (2) Single writer: the Sweep alone writes the store; the Brief only reads, so a
rendering or email problem can never damage data. (3) Context and time: the Sweep reads up to 25 long
documents; a separate Brief starts fresh with room for synthesis. The cost is one extra clone and store
download (a minute or two). Recommendation: keep two.

**Possible desktop-local duplicates** (`utility-tracker-sweep` Mon 05:11, `weekly-utility-brief` Mon 08:00) may
still exist on Rett's computer; they are invisible from the cloud. If present, disable them — the lock prevents
double rows, but a local Brief would send a second email.

### Collector (GitHub Actions)

Nightly, with **three scheduled triggers — 04:43, 06:17 and 08:41 UTC** (21:43, 23:17 and 01:41 PDT). GitHub runs scheduled
events best-effort (its docs: they "can be delayed during periods of high loads" and some "may be dropped"; the 06:17
run of 4 Oct started at 12:26 UTC). A guard step lets only the first trigger that starts do the work: later triggers
skip if a complete run finished within 6 hours, so agencies still see one collection a night. Each job checks out
the newest `main` at start (a queued event otherwise checks out an hours-old commit). Every complete run records
`last_full_run` in `data/state/collector_state.json` and `hours_since_previous_full_run` / `collector_gap` in its
health file; the Sweep reports a gap as COLLECTOR_GAP (amber). A missed night loses nothing: adapters re-read from
their last success minus three days. Writes only to the repo's `data/`. Never classifies, never writes the row
store. Manual dispatch accepts `backfill_since` (docket history from a date). Spare time at the end of each night
(up to the 70-minute deadline, ~150 documents) goes to **backfill enrichment**: fetching and extracting the
documents behind the docket-history backfill, tiered (1 commission-issued, 2 watched party — matched on the
cover page, 3 briefs/testimony/applications/tariffs, 4 other) into `data/backfill/enriched.jsonl`.

---

## 4. Architecture v3 (current)

```
Nightly    GitHub Actions collector ──► public repo data/ (candidates + full-text filings + health + backfill)
Mon 03:54  Sweep (Claude, cloud)    ──► git clone (read-only) + OneDrive store + Outlook (read-only)
                                        + manual drops + WebFetch routes
                                    ──► NEW immutable part in OneDrive + run record (+ repair proposals)
Mon 08:54  Brief (Claude, cloud)    ──► Excel + narrative built in the session ──► console republished
                                    ──► email to Rett ──► brief record
Any time   Manual pass (desktop app, Rett present) ──► OneDrive /GridDocket/manual/ ──► next Sweep ingests
```

**Design rules:**
- **Two cursors.** `state.last_successful_sweep` bounds mail, manual drops and WebFetch; `state.collector_cursor`
  (default 2026-09-18) bounds collector candidates, so a degraded run that read no collector data never skips
  them. (Found 3 Oct: the degraded run had advanced the window past the first 506 candidates.)
- **Scheduled runs never push to the repo.** Scheduled sessions have no `add_repo` tool; they `git clone --depth 1`
  the public repo, read collector data, prompts, watch list, corrections queue and validator, and build from a
  local `store_live/` copy downloaded from OneDrive.
- **Single writer.** Only the Sweep writes the row store. It takes `sweep_lock.json` (stops if another run holds
  a lock under 3 hours old, or a run record already exists for today) and uploads each new part with
  conflict-fail.
- **Commit order:** new part → manifest → seen index → metrics/tariffs → run record → `state.json` last. A run
  that dies repeats its window safely (identity + seen index + `manual_ingested` make it idempotent).
- **Immutable parts with overlays.** `supersedes` [{old_event_id, new_event_id, reason}] marks all old rows
  Superseded = Yes; `overlays` [{event_id, column, value, reason}] may change only Status, Next Milestone, Next
  Date, Appeal, Superseded. `tracker/rowstore.py` applies them at load. A substantive change is a new event.
- **Validation before any write:** `python tracker/rowstore.py --store store_live --part <file>` checks
  vocabulary, 26 cells, Event ID format and reuse, one date per event, overlay targets.
- **Manual-pass integration:** ingested only when `manual_<run_id>.json` exists with `"complete": true` and the
  run_id is not in `state.manual_ingested`. Partial or abandoned runs are invisible.
- **Collector repair:** for a source failing 2+ consecutive nights, the Sweep writes a **repair proposal** (diagnosis
  + patch) into its run record and the report; a session with push access applies it. Fixes that would defeat a
  block, ignore robots.txt or use a credential are not fixes.
- **Excel parity:** `build_tracker.py` (canonical) and `console/tracker_xlsx.js` (ExcelJS, in the console) build the
  same workbook; CI compares them cell by cell. **0 differences.**

### The Sweep (`prompts/sweep.md`)

Preflight and lock → clone repo → load state and store into `store_live/` → health (consecutive failures,
SUSPECT_ZERO after checking explicit negatives) → collector candidates (metadata triage; party watch; read up to
**25 documents × 40,000 characters**; backlog the rest) → mail (FERC/ERCOT folders; RTO Insider, NPM, CapIQ,
NCUC, DCC Bi-Weekly; **newsletter canary**: every newsletter event either gets a row or is recorded
`CANARY_MISS`) → manual drops → WebFetch routes (6.1 PA; 6.2 AZ PDFs; 6.3 manual-route fallbacks; 6.4 ERCOT
notices, large-load and planning pages; 6.5 PJM; 6.6 runner-refused pages that open to WebFetch) →
grain/identity/supersession/dedupe → classify → corrections queue (up to 6 items/run) and enriched backfill (15 items/run, tiers 1–2 first)
→ commit → repair proposals → run record and three-paragraph report. Target 30 minutes. Degraded mode (mail +
manual + web only) if the clone fails.

### The Brief (`prompts/brief.md`)

Setup (clone; download store) → preconditions (>3 days stale = short `[No sweep]` notice only; zero new events
and green = three-line "nothing moved") → STATUS CHECK (GREEN/AMBER/RED) → **30-day milestones, never omitted**
(URGENT inside 7 days; past-dated without outcome = "outcome needed") → synthesis by Subject → `narrative.md`
(700–1,200 words) → build into `out/deliverables/` (with `--state store_live/state.json --manual-dir store_live/manual`,
before `last_brief_date` changes) → publish console → email → `/GridDocket/briefs/<date>.json`;
update only `state.last_brief_date`. **REPO-LESS PATH** if the clone fails: build from OneDrive alone.

**Email:** subject `Grid Docket — <D Mon> · <N> high-impact · <three shortest descriptors>` (prefix `[Status] ` when
RED, `[No sweep] ` for the failure notice). HTML, 400-word target, 600 ceiling. Sections: STATUS CHECK (amber/red
only) · UPCOMING MILESTONES (always) · THIS WEEK (3–5 high items) · ALSO MOVING (≤6 medium) · LINKS (console
only) · one-line footer. Fewer than three high items never licenses promoting medium ones.

**Excel delivery mechanics:** binaries can't round-trip through the Graph text/base64 tool path (a 71 KB
workbook ≈ 385k tokens, silently truncated), and artifacts can't serve .xlsx as a static file. So the console
builds the workbook in the browser from the full row table and offers it through the `downloads` capability.
The JSON is the source of truth; the workbook is a rendering.

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
- **Never delete a row.** Supersede by adding a row and flagging the old (via `supersedes` / `overlays`, §4).
- **Appeal and Superseded** hold "Yes" or "No".
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

## 6. Current state of the data (3 Oct 2026)

**Store: 180 events / 253 rows** across `rows_p1..p5`.

- **Baseline v2 (loaded 2026-09-18): 161 events / 229 rows**, 2025-11-07 to 2026-09-18, 18 jurisdictions, 33
  entities. Confidence 185 Verified / 42 Reported / 2 Unverified. Materiality 149 High / 80 Medium. On appeal: 4
  rows. Superseded: 3 rows across 2 events (E-20260918-035 ×2 Duke NC+SC; E-20260918-110 APS).
- **`rows_p5` (3 Oct, degraded Sweep): 19 events / 24 rows, all Reported**, plus 2 overlays on E-20260918-098.
  Contents include PUCT adoption of 16 TAC §25.194 (Project 58481); the Governor's TCEQ permit halt
  (E-20261003-002); the ERCOT Batch Zero audit sequence (E-20261003-011 community-impact RFI, -012 verification
  RFI, -013 directive and delay notice, -014 provisional classifications); five FERC §206 rehearing dismissals;
  the PJM backstop order; a Senate permitting proposal; PUCT 58000 and 58482; ICC 26-0364 and the Illinois Joint
  IRP; two PA model-tariff reconsideration orders.
- **Gap:** the Mondays of 21 and 28 September passed silently (tasks were disabled). The 3 Oct run covered the
  window from mail and the web; the first full run (5 Oct) adds collector material and upgrades the Reported
  Texas rows to Verified where the primary documents confirm them (C-01).
- **Flags recounted 3 Oct:** superseded 3 rows (2 events), on appeal 4 rows; `state.json` and `rows.json` still carry
  older values until the Sweep applies C-05. The repo's `store/` is a frozen baseline copy, not a mirror.

---

## 7. Coverage history, catch-up and corrections

**How the baseline was built (and why it missed things):**
- Phase 1 (investor disclosure), 2026-09-18: 39 events / 71 rows, 16 issuers, Q4 2025–Q2 2026.
- Phases 2–3 (federal/RTO and state dockets) were one pass on 2026-09-18, with a gap-closing second pass only for
  VA, AZ, NM, SC, GRDA, KS and WV. **Docket activity was never enumerated filing by filing** — collection
  followed known docket numbers.
- Two confirmed misses: **Texas** (the 2026-08-03 Governor's audit directive and the 2026-08-10 ERCOT Batch Zero
  pause in PUCT Project 58317, then the September RFIs) and **Arizona** (Microsoft's 2026-08-27 closing brief in
  the APS rate case, image E000054018, docket E-01345A-25-0105). Causes: no docket for a directive; 58317 and
  ERCOT notices unwatched; the inbox never read in the backfill; customer/intervenor filings had no slot; ACC
  listing needed an API v1 couldn't call.

**v3 remedies:** full docket-activity enumeration per watched docket; PUCT 58317 watched; governors' newsrooms
(TX, VA, GA, AZ, PA, OH, LA, NC, AL, IL, MO, NM, NV, OK, SC, WV); **party watch** (Microsoft, Google, Amazon/AWS,
Meta, Oracle, OpenAI, CoreWeave, Data Center Coalition, developers, IPPs, industrial and intervenor groups);
newsletter canary; corrections queue.

**Catch-up mechanisms (will the next run see everything since the backfill? — yes, by these routes):**
1. **Window and cursor:** mail, manual drops and web routes are read from `last_successful_sweep` (3 Oct); collector
   candidates are read from `collector_cursor` (default 18 Sept), so the 506 candidates of 2 and 3 Oct that the
   degraded run never saw are in scope for 5 Oct. (Before this fix they would have been skipped.)
2. **Docket-history backfill:** completed 3 Oct — **5,210 filings** since 2025-11-07 (TX 2,583, FERC 1,019, MO 773,
   AZ 571, LA 135, NM 93, GA 27, KS 9), but its document budget ran out after FERC and Louisiana, so most items were
   metadata only — and party briefs are often filed under an attorney's name (the Microsoft brief reads "Albert H.
   Acken, Atty."). Fix: the collector now enriches ~1,800 substantive items with document text over the next
   ~2 weeks of nightly runs, matching watched parties on the cover page, into `data/backfill/enriched.jsonl`; the
   Sweep processes 15 per run, tiers 1–2 first (C-07).
3. **Baseline-links file** (`data/backfill/baseline_links_2026-10-03.jsonl`, 304 links): links that were already
   on watched pages when the collector first saw them (and were silently baselined). The Sweep triages by title
   and treats on-beat ones as candidates.
4. **Corrections queue** (`prompts/corrections_queue.md`, verified at source before writing, ≤6 per run):
   C-01 Texas directive / Batch Zero (partly done 3 Oct as Reported; upgrade and overlay the stale baseline row) ·
   C-02 Microsoft APS brief · C-03 Arizona XHLF eligibility · C-04 Louisiana U-37882 milestone · C-05 store
   housekeeping · C-06 Texas text quality · C-07 backfill (ongoing until exhausted).
5. **New-source history** (4 Oct): bills, court decisions, county actions, Regulations.gov items, ERCOT large-load
   materials and LBNL studies since 2025-11-07, pulled once the sources existed; the Sweep works through them 20 a run
   (C-08) and rebuilds the ERCOT large-load series from the monthly overviews.
6. **Manual pass** for the states the cloud can't read (§12).

---

## 8. How each source is reached (access findings, 3 Oct 2026)

**Collector conduct (non-negotiable):** honest UA `BlueOwl-RegTracker/4.0 (rett.young@blueowl.com)`; robots.txt
per RFC 9309 (2xx parse; 4xx no rules; 5xx/unreachable = disallow; a firewall page served as robots.txt =
disallow; HTML app shell = no robots file; strip BOM); ≥3 s between requests per host; fetch only watched items;
block pages recorded as BLOCKED, never parsed; robots.txt Crawl-delay / Request-rate honoured (since 3 Oct); no CAPTCHA solving, stealth, IP rotation, logins or third-party
proxies; **never disable TLS verification** — incomplete chains completed via the leaf's AIA intermediate with
verification on. Run deadline 70 min; per-source budgets (watch pages 1,500 s, agendas 1,200, queues 900,
ERCOT large-load 900, EQR 900, state courts 900, NM 900, Open States 600, Legistar 600).

**Routes:** C = collector (GitHub Actions) · W = Sweep's WebFetch · M = mail (read-only) · P = manual pass.

| Source | Route | Working method and status |
|---|---|---|
| FERC | C | eLibrary JSON API (`POST elibrary.ferc.gov/eLibraryWebAPI/api/Search/AdvancedSearch`; `File/DownloadP8File`; `Docket/GetSingleDocketSheet`). Working. |
| Federal Register | C | API with agency + term filters. Working. |
| SEC EDGAR | C | Declared UA opens it. 8-K (2.02, 7.01, 8.01, 1.01, 2.01), 10-Q, 10-K, 40-F, 6-K. CIKs: Fortis 0001666175, TXNM 0001108426, Oncor 0001193311, Nevada Power 0000071180. Working. |
| TX PUCT | C | Interchange filing lists; documents `interchange.puc.texas.gov/Documents/{ctrl}_{item}_{id}.PDF/ZIP`; watches 58317, 58481, 59142, 58000, 58482. **Document links were silently missed until 3 Oct** (the site switched to absolute links); fixed, and the nightly enrichment back-fills text for the candidates and backfill items that lacked it. (WebFetch gets 402 on ~1 in 3 files; the collector doesn't.) |
| AZ ACC | C (listings) + P (documents) | `POST efiling.azcc.gov/api/edocket/searchByDocketDetailRequest` (exactly the documented fields) and `GET /api/edocket/docket/{id}` list every filing. **Documents: not reachable from the cloud since at least 3 Oct** — `images.edocket.azcc.gov` presents a certificate for another hostname (collector and WebFetch both refuse; never work around a certificate error), and `docket.images.azcc.gov` is robots-disallowed. The Sweep queues the AZ documents it needs for the manual pass (item-detail URL `edocket.azcc.gov/search/document-search/item-detail/<id>`). |
| GA PSC | C | `psc.ga.gov/search/service-facts-docket/?docketId=…`; documents via `services.psc.ga.gov/api/v1/External/Public/Get/Document/DownloadFile/…`. Working. |
| LA LPSC | C | Valence portal (`DocketSearch` → MatterId; `Docket_Documents`; `RecentOrders`; `ViewFile`). Ligature-corrupted text: summarize, never quote. Working (U-37921 not found by number). |
| MO PSC | C | EFIS with anti-forgery token; `Case/Display/{id}`, `Case/FilingDisplay/{id}`. Working (one case id, ET-2025-0184, unresolved). |
| NM PRC | C | e360 CaseX API. **Documents repaired 3 Oct:** the list request now matches the portal's own (`casepublicdocument/getAll` with `searchTerm` alongside `caseId`, 100 a page, newest first), observed in the built-in browser; downloads use the portal's anonymous per-document ticket (`POST casex/cms/downloadToken {context: File, documentId, isPreview}` → `GET document/v1/previewDocument?token=`), the same calls a visitor's browser makes. Verified from the runners on 25-00079-UT, 25-00082-UT and 26-0000062 (text layers). Confidentiality agreements and non-public documents are skipped. |
| KS KCC | C | Commission minutes PDFs; `kcc-connect` is Salesforce (15-char id). Working. |
| OK OCC | C | Laserfiche WebLink search; 8 newest hits kept unconfirmed (page-text service errors); the Sweep confirms from PDF text. Never `ecf.public.occ.ok.gov`. |
| GRDA | C | Board agendas/minutes. Working. |
| AL PSC | C + W | RSS returns HTTP 500 (server fault); docket pages readable by WebFetch (`ViewFile.aspx?Id=<GUID>`; Act 610 docket 33709). |
| PA PUC | W | Runners get a TLS failure and 5xx robots; WebFetch works (`puc.pa.gov/docket/<n>`, `/pcdocs/<id>.pdf`). |
| VA, SC, IL, OH, NC, WV, NV | P (+W fallbacks) | Refuse automated access — see §10. |
| RTOs | C + W + M | CAISO, SPP, NYISO, ISO-NE, MISO, WPP pages; ERCOT news and **notice archive** (C); **ERCOT large-load status** — LLWG/TAC/ROS/Board meeting pages, the large-load page and the Monthly Operational Overview, with table extraction (C, adapter `ercot_large_load`, since 3 Oct; these pages now open to the runners); ERCOT planning page (W); PJM newsroom (W). See §11 for ERCOT. |
| Capacity markets | C (+P) | PJM RPM (119 links), MISO PRA, ISO-NE FCM, SPP RA working. **NYISO ICAP:** the page's documents come from `POST /o/documentlibrary/subitems` (observed 3 Oct), but NYISO answers automated clients with an empty HTTP 202 (bot-management challenge); adapter `nyiso_icap` records it as `refused_known` (a sub-source status, so it never trips the circuit breaker or the Brief's RED) and stops. The manual pass reads the ICAP page monthly (extra page). |
| Queues | C | MISO `misoenergy.org/api/giqueue/getprojects`; SPP `opsportal.spp.org/Studies/GenerateActiveCSV` (CSV preamble handled); **PJM (4 Oct, no key)** — serial/expedited queue from the static `www.pjm.com/pjmfiles/media/planning/queues-data/PlanningQueues.xml` (~23 MB, refreshed daily) and the cycle queue (TC1, TC2, Cycle 1+) from `POST www.pjm.com/m/ProjectTransition/GenerateXMLTransitionProjectsAll` with the form the Cycle Service Request Status page's "Full Export: XML" button sends (observed in the built-in browser). Serial entries "moved to" a transition cycle and Long-Term Firm Transmission Service requests are skipped. Verified from the runners 4 Oct: baseline 228 serial + 664 cycle active projects in VA, OH, PA, IL, WV, NC. Working. ERCOT's generator queue (GIS report) is not collected yet; the ERCOT Public API is live (§9) and the adapter can be pointed at its EMIL id. |
| Legistar | C | 9 clients: pwcgov, maricopa, phoenix, mesa, columbus, sanantonio, fortworthgov, kansascity, washoe-nv (added 3 Oct). Working. |
| Local agendas (non-Legistar) | C | Adapter `agendas` (3 Oct): Fairfax BOS meeting pages, Henrico agenda PDFs, Atlanta IQM2 calendar, Tulsa Council / TMAPC / Board of Adjustment, Storey County AgendaCenter. Items kept only when their text matches `agenda_filter`. Loudoun (lfportal robots unreadable; Granicus disallows), Reno (PrimeGov disallows) and Fulton (no static agenda links) are not collectable. |
| Governors | C (+W) | AL, IL, MO, NM, NV, OK, SC, WV, TX, VA, GA, PA, OH, LA, NC working in C; KS via W; AZ refuses both. |
| Courts | C | Virginia Supreme Court and Court of Appeals pages; **West Virginia Supreme Court** opinions page (3 Oct); **PA Commonwealth Court opinions RSS** (`pacourts.us/Rss/Opinions/Commonwealth/`, replaces the 0-link page); **Supreme Court of Texas** release-date pages and orders PDFs (adapter `courts_state`); CourtListener with a state-appellate-court query first (TX 3rd/15th COA, OH, PA, WV and the other tracked states). `search.txcourts.gov` (TAMES) disallows crawlers — the Texas courts of appeals arrive only through CourtListener. `COURTLISTENER_TOKEN` is now passed to the job (it was not before 3 Oct). |
| IRP / RFP pages | C (+W) | Dominion, Georgia Power, APS, Entergy RFPs, Evergy, Xcel/SPS working; Duke via W. |
| DOE / NRC | C | DOE news, 202(c), LPO working. **NRC news via RSS** (`nrc.gov/public-involve/rss?feed=news`, replaces the 0-link page; occasional 403 from NRC's CDN). **NRC ADAMS** Public Search API (`POST adams-api.nrc.gov/aps/api/search`) for ten named dockets — live 4 Oct (`NRC_APS_KEY`). The legacy `adams.nrc.gov/wba` host no longer resolves. |
| FERC Form 1 / 3-Q / 714 | C | eCollection XBRL feed (`ecollection.ferc.gov/api/rssfeed`, keyless, newest ~650 filings), matched to the tracked operating companies and the RTOs' Form 714s; metadata + link to FERC's HTML rendering. |
| FERC EQR | C | Catalyst Cooperative PUDL parquet (`s3.us-west-2.amazonaws.com/pudl.catalyst.coop/ferceqr/core_ferceqr__contracts/<yyyy>q<n>.parquet`, ~3 MB a quarter, keyless): new contracts with hyperscalers and data-center developers versus the previous quarter. |
| Studies | C (+W) | LBNL via DOE OSTI records API (emp.lbl.gov / eta.lbl.gov return 403 to the runners); LBNL "Queued Up" page monthly via WebFetch; Grid Strategies RSS. |
| Hyperscaler newsrooms | C | RSS: Microsoft On the Issues and Source, Google (all posts and Sustainability), Amazon, Meta Newsroom; fetched articles kept only if they name data centers, power, grid, nuclear, MW/GW, utilities or PPAs. Oracle's newsroom returns 403. |
| Investor decks | C | Events pages rendered, PDF links harvested (never guessed). 10 of 16 working; 6 refuse (§10). |
| Mail | M | Folders "FERC", "ERCOT"; senders `today@rtoinsider.com`, `alerts@newprojectmedia.com`, `alerts@capitaliq.spglobal.com`, NCUC; DCC Bi-Weekly PDF (forwarded to BODIpower@blueowl.com). Internal deal threads are confidential and never sources. |
| Keyed data | C | All keys live since 4 Oct (verified from the runners): EIA, congress.gov, Open States (paced 10/min), CourtListener (paced 5/min), Regulations.gov, NRC ADAMS, ERCOT Public API. Keys never reach the public repo: `common.scrub()` masks them in everything the collector writes. |

**Manual-pass browser methods:** VA SCC Breeze API (`/DocketSearchAPI/breeze/…`; PDFs `/docketsearch/DOCS/<FileName>`);
WV `http://` + `/scripts/WebDocket/` + `ViewText.cfm` (the Commission's own text layer); SC
`dms.psc.sc.gov/Web/Dockets/Detail/<internal id>` (2026-138-E = 119719; 2026-186-EG = 119767); IL BROWSE route
`POST …/browse/docket_detail.asp` (never Search.aspx); NC `ViewFile.aspx` by GUID; pdf.js injection for PDFs;
`window.open` interception for JS-driven links; OCR via Tesseract.js only when no text layer (never write an OCR
number as fact).

**Entity aliases are mandatory:** Dominion = Virginia Electric and Power Company; AEP Ohio = Ohio Power Company;
PPL = PPL Electric Utilities Corporation; Evergy = Evergy Kansas Central / Evergy Metro / Evergy Missouri West;
Duke = Duke Energy Carolinas / Duke Energy Progress; Ameren = Union Electric Company; ComEd = Commonwealth Edison
Company; PNM = Public Service Company of New Mexico / TXNM Energy. Full list in `config/watchlist.yaml`.

---

## 9. API keys

Claude cannot enter keys itself, so Rett creates each account and adds the key at **GitHub → rettyoung/BODI
→ Settings → Secrets and variables → Actions → New repository secret**. Secrets stay private on a public repo
and are masked in logs.

**Status 4 Oct 2026 — live:** Open States (bill titles filtered to the beat; paced to 10/min), EIA, CourtListener
(paced to 5/min), congress.gov, Regulations.gov and NRC ADAMS (ten dockets; the `DateAddedTimestamp ge` filter works),
all verified from the runners. ERCOT Public API: sign-in verified (all three secrets); the catalogue's 120 report products include none on large
loads yet, so the route checks nightly and starts collecting when ERCOT publishes one (e.g. the NPRR1267 status report). Secret names are checked by the probe (presence only). Because EIA and congress.gov carry the
key in the URL and the repo is public, every file the collector writes passes through `common.scrub()` (masks secret
values and `api_key=`/`token=`/`password=` parameters); the probe workflow receives the same secrets so keyed
adapters can be tested on demand.

**Secrets in use** (all free; each `ok` in health):

| Secret name | Where to get it | Cost | What it adds |
|---|---|---|---|
| `EIA_API_KEY` | eia.gov/opendata/register.php | Free | EIA-860M operating-generator capacity by state (large additions and retirements in tracked states) |
| `CONGRESS_API_KEY` | api.congress.gov/sign-up | Free | Federal bills and actions on data centers, permitting, transmission |
| `OPENSTATES_API_KEY` | open.pluralpolicy.com (account → API key) | Free | State bills matching data-center / large-load queries in the tracked states (replaces LegiScan, which blocks by IP) |
| `COURTLISTENER_TOKEN` | courtlistener.com (free account → API token) | Free | Every court query plus federal RECAP dockets; search paced to 5 requests a minute |
| `REGULATIONS_GOV_API_KEY` | api.data.gov/signup | Free | Adapter `regulations_gov` (4 Oct): DOE/EPA/NRC documents on the beat and comments by watched parties in those dockets |
| `NRC_APS_KEY` | adams-api-developer.nrc.gov → Sign up → Products → "ADAMS Public Search API" → Subscribe; the key is under "Your Subscriptions" | Free | ADAMS documents added to the ten named nuclear dockets (Palisades, Crane/TMI-1, Duane Arnold, Hermes 2, Kemmerer, Long Mott, Clinch River, Pioneer 1–2) |
| `ERCOT_API_USERNAME`, `ERCOT_API_PASSWORD`, `ERCOT_API_SUBSCRIPTION_KEY` | apiexplorer.ercot.com (free ERCOT account + Public API subscription) | Free | Sign-in verified 4 Oct; adapter `ercot_large_load` pages the 120-product catalogue nightly and collects any large-load product (none published yet) |

**Recommended — would need an adapter built once the credentials exist (can't be tested without them):**

| Secret name(s) | Where | What it adds |
|---|---|---|
| `PJM_API_KEY` | apiportal.pjm.com (free PJM account, Data Miner subscription) | PJM Data Miner 2 capacity and market data. **Not needed for the queue** (public exports since 4 Oct). On 4 Oct Account Manager offered no Data Miner access on Rett's account and apiportal sign-in looped to Tools home; PJM Member Relations (custsvc@pjm.com) can fix it. Data Miner terms bar redistribution, so any adapter must keep its output out of the public repo |
| CapIQ (optional, licensed) | Blue Owl's S&P entitlement | Already arriving as mail; an API call would add structure. S&P RRA (state docket content) is a separate entitlement |

**Not needed:** SEC EDGAR (UA only), Federal Register, FERC eLibrary, MISO, SPP and PJM queues, Legistar, GitHub (the
workflow uses its built-in token), Microsoft 365 and Box (connectors attached to the scheduled tasks).

---

## 10. Sources that refuse automated access, and the alternatives

"Refuse" means the owner's robots.txt, a bot wall, CAPTCHA or firewall turns away the collector. None of these is
bypassed. The six commissions gave verbal consent but said they cannot change their systems; a robots override
on verbal consent was refused by this environment's safety controls and is **not to be pursued again by any
route**.

| Source | How it refuses | Alternatives in place | Further options |
|---|---|---|---|
| **VA SCC** docket search | robots.txt admits only named search engines | Manual pass (Breeze API in the browser); Dominion/ApCo/NOVEC disclosures on EDGAR; DCC Bi-Weekly; RTO Insider and NPM mail | Written request that SCC add a robots allowance for the UA; S&P RRA |
| **SC PSC** DMS | `Disallow: /` | Manual pass; PSC latest publications and ORS electric page (C); Duke/Dominion EDGAR | As VA |
| **IL ICC** e-Docket | `Disallow: /` + CAPTCHA | Manual pass (Rett solves any CAPTCHA); ComEd/Exelon EDGAR; IPA site for IRP; mail | As VA |
| **OH PUCO** DIS | F5 firewall (even on robots.txt) | Manual pass; Ohio Consumers' Counsel filings (C); AEP Ohio EDGAR; Columbus Legistar | Agency allowlist (technical change they declined) |
| **NC NCUC** `starw1` | Cloudflare challenge | Manual pass; WebSearch `site:starw1.ncuc.gov` harvests GUIDs that open via `ViewFile.aspx`; NCUC mail; NCUC main-site PDFs; Duke EDGAR | As OH |
| **WV PSC** | HTTP 403 to automated clients | Manual pass (`ViewText.cfm`); ApCo/AEP EDGAR; WV governor page (C) | As OH |
| **NV PUCN** | robots disallows all; no text layer | Manual pass (metadata ceiling); NV Energy/BHE disclosures on EDGAR (Nevada Power 10-Q/10-K) | S&P RRA |
| PA PUC | Runners blocked (TLS + 5xx robots) | **WebFetch works** — Sweep route 6.1 | — |
| AZ document hosts | `docket.images.azcc.gov` robots; `images.edocket.azcc.gov` certificate hostname mismatch | Listings by the collector; documents via the manual pass (queued by the Sweep) | Recheck weekly — if the ACC fixes its certificate, the collector reads them again automatically |
| IR pages: Southern | Incapsula | EDGAR 8-K exhibits; WebSearch for the deck PDF on its CDN | — |
| IR pages: Evergy, Exelon, OGE, Oncor | robots | EDGAR 8-K/10-Q; WebSearch for the q4cdn/GUID PDF (the refusing page itself is never fetched) | — |
| IR pages: BHE | CAPTCHA | Nevada Power / PacifiCorp filings on EDGAR (twice-yearly BHE decks) | — |
| PJM Inside Lines | CAPTCHA on the RSS | FERC dockets (C); RTO Insider mail; **PJM newsroom via WebFetch** (6.6) | PJM API key (§9) |
| ERCOT rendered pages from runners | Incapsula (until 3 Oct) | Since 3 Oct the large-load page and the committee/board meeting pages open to the runners too (adapter `ercot_large_load`); planning page via WebFetch; `/files/docs/` from both; ERCOT mail folder | ERCOT Public API (§9) |
| Arizona governor | 403 (collector and WebFetch) | Mail; ACC dockets; news | — |
| Kansas governor | 403 to runners | **WebFetch works** (6.6) | — |
| Duke Carolinas IRP page | 403 to runners | **WebFetch works** (6.6); NCUC via manual pass; Duke EDGAR | — |
| IL Citizens Utility Board | 403 (mirror removed from the watchlist 4 Oct) | Manual pass for ICC |
| Texas courts of appeals — `search.txcourts.gov` (TAMES) | robots.txt disallows crawlers | CourtListener state-court query (C); Supreme Court of Texas pages on www.txcourts.gov (C) | — |
| NYISO ICAP document library | Empty HTTP 202 (bot-management challenge) | Manual pass extra page (monthly); NYISO FERC filings | Ask NYISO to admit the UA |
| LBNL `emp.lbl.gov`, `eta.lbl.gov` | HTTP 403 to runners | OSTI records API (C); "Queued Up" via WebFetch (monthly) | — |
| Oracle newsroom | HTTP 403 | EDGAR 8-Ks; party watch | — |
| Loudoun County agendas | `lfportal.loudoun.gov` robots.txt unreadable (= disallow); `loudoun.granicus.com` disallows | None in the cloud; Dominion filings, NPM, DCC | Manual pass; ask the county |
| City of Reno agendas | `reno.primegov.com` disallows crawlers | Washoe County (Legistar) and Storey County agendas | — |
| Fulton County GA agendas | Agenda list not in the page HTML | Atlanta City Council agendas | — |
| ERCOT MIS data-product servlets | robots.txt disallows `/misapp/` | Meeting materials + Monthly Operational Overview (C) | ERCOT Public API (§9) | — |

**Faults and limits, not refusals:** AL PSC RSS (HTTP 500 — docket pages via WebFetch); CourtListener keyless
(429 — add token); PUCT Interchange via WebFetch (402 on some files — collector unaffected); LegiScan (blocks by
IP — Open States instead); NM documents endpoint (empty until 3 Oct — repaired, see §8); OK page-text service (errors — Sweep
reads the PDF); Ohio Supreme Court opinion list (ASP.NET postback paging — CourtListener instead).

---

## 11. ERCOT — is there a reliable route to all notices and planning pages?

**Yes, for notices and published documents; partly, for data products.**

- **Market notices:** the public archive `https://www.ercot.com/services/comm/mkt_notices/archives` (three years,
  newest first) is read nightly by the collector (watch page `ercot_notice_archive`, 23 notice links on the
  2 Oct probe; links `mkt_notices/M-…`) **and** by the Sweep via WebFetch (step 6.4). Keywords include Batch Zero,
  NPRR, PGRR, verification RFI, community impact, load forecast, firm load shed and emergency, so notice titles
  pass the filter. The old notices URL 404s. The ERCOT mail folder is the cross-check.
- **Large-load status (adapter `ercot_large_load`, 3 Oct):** the large-load page (`services/rq/large-load-integration`)
  and the LLWG, TAC, ROS and Board meeting pages now open to the runners. Each night the collector reads them,
  fetches new `/files/docs/` materials that touch large loads plus the Board's Monthly Operational Overview, and
  extracts the status rows and headline figures with the sentence each came from (`meta.table_rows`,
  `meta.table_metrics`): MW approved to energize (9,012 → 9,062 → 8,926 MW, April–June 2026 overviews) and the
  observed non-simultaneous peak consumption of those loads (4,006 → 4,145 → 3,966 MW). The Sweep keeps the series
  in metrics.json. ERCOT's NPRR1267 Large Load Interconnection Status Report is an MIS data product; the MIS
  servlets are robots-disallowed; the ERCOT Public API (live 4 Oct) does not list it yet, and the adapter checks its
  catalogue nightly.
- **Planning page:** `gridinfo/planning` (RTP, LTSA, constraints report, GRRA) via WebFetch (Sweep 6.4).
- **Documents:** everything under `ercot.com/files/docs/` opens to both the collector and WebFetch. Board and TAC
  materials not linked from those pages: WebSearch `site:ercot.com/files/docs` by topic and month.
- **Data products** (`mp/data-products/…`, e.g. RTP `PG7-048-M`, GRRA `PG7-226-M`) are JS-rendered lists. The
  reliable route is the **ERCOT Public API** (§9, live 4 Oct), which lists report archives by EMIL id; the Sweep also
  uses the planning page's direct links.
- **Texas context outside ERCOT:** PUCT 58317 and related projects (collector); governor and PUCT news pages.

---

## 12. The manual pass — how to run it

**Friday reminder (set up 3 Oct).** Every Friday at 9:04 am PT a scheduled task fires **on Rett's computer**
(the Claude desktop app must be open and the computer awake) and sends a push notification. It asks "Run now" or
"Skip this week" — one click. It does nothing without "Run now", because the pass relies on Rett being present
(CAPTCHAs are his to solve, and the browsing is his). If the computer is off, that week's pass is simply missed;
the Brief names any blocked state that has gone more than 14 days without a manual drop.

**Any other time:** open the desktop app, start a task and type **`/grid-docket-manual-pass`**.

**It catches up by itself.** The pass reads `manual_queue.json` (written by each Sweep: watched dockets, the
newest document already held, requests, new-case terms, extra pages) and the records of every earlier complete
manual run in `/GridDocket/manual/`. For each docket it reads everything filed since the later of those two dates,
so skipping weeks loses nothing. Since 3 Oct it also **searches each portal for new cases** opened since the last
run (large-load tariffs, data-center contracts, generation certificates, cost-allocation cases, watched parties)
— the one thing the cloud fallbacks can never see — records the route it used so the next run reuses it, and
reads what the cloud can't: Arizona documents, the Arizona governor's newsroom, the NYISO ICAP page (monthly), and
IR events pages in earnings season. (New Mexico documents are collected by the cloud again since 3 Oct; the Sweep
queues NM only if that breaks.) For Nevada (no text layer) it looks for a text copy elsewhere first (filer's site, FERC, SEC,
intervenors), otherwise reads the pages visually — still Reported at most.

**What happens:** one file per state saved as it goes, then a manifest with `"complete": true`; the next Sweep
ingests it automatically (`state.manual_ingested`) and adds any new cases to the watch list. The pass never
writes the row store. Skill copy at `manual/SKILL.md`; the saved skill on Rett's account is authoritative
(updated 4 Oct: NYISO ICAP page monthly; New Mexico only when the queue asks).

---

## 13. Registry corrections — facts that were wrong (do not resurrect)

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

## 14. Structural findings, explicit negatives, watch signals

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

## 15. Benchmarks, standing facts and milestones

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
| 2026-09-30 | Duke NC large-load tariff filing due; Ameren Missouri triennial IRP (~3 GW requested); OG&E reported hearing (unconfirmed) | past — outcome needed |
| 2026-10-01 | Alabama Act 610 effective (review at 150 MW+); MISO BPM-032 v1.0 due | past — outcome needed |
| 2026-10-08 | Illinois Joint IRP workshop comments due | recorded 3 Oct |
| 2026-10-12 | ERCOT State and Community Impact RFI responses due (5 pm CT) | recorded 3 Oct (Reported) |
| 2026-10-14 | GRDA board (Google LGS-Industrial schedule; WP-SS rider) | |
| 2026-10-20 | ApCo Virginia rate case hearing, PUR-2026-00044 | |
| 2026-10-26 | SC large-load workshop 2026-138-E (26–27 Oct); WV MARL 500 kV hearing 26-0075-E-CN (to 2 Nov) | |
| 2026-10-31 | WRAP Forward Showing deadline (first binding season, Summer 2027) | |
| 2026-11-12 | FERC §206 abeyance ends — PJM, NYISO, MISO, CAISO, ISO-NE | |
| 2026-11-16 | Illinois Joint IRP issued (ICC/IPA) | recorded 3 Oct |
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

## 16. Verification record

**2 October 2026 (build day):**
- Reachability probe from GitHub Actions: open hosts confirmed; six commissions closed by their owners (VA, SC,
  IL, OH, NC, WV); PA open only to WebFetch; EDGAR opened by the declared UA.
- Built v3: collector (15 adapters plus governor/party watching, health, circuit breakers, 70-minute deadline,
  rotating start, checkpoints, per-list baselining, backfill mode, AIA completion); overlays and validation;
  Excel in Python and in the browser with CI parity (0 differences); narrative PDF/DOCX; console; Sweep and
  Brief prompts; corrections queue; manual-pass skill (saved by Rett); `SOURCES.md`.
- First collector run: 334 new items, 160 documents extracted, ~20 minutes. Fixed AZ, MO, OK (partly), TLS
  chains; added PUCT 58317, party watch, governor and PUCT news pages.
- Allowlist drafts created in Outlook (not sent): VA `sccinfo@scc.virginia.gov`; NC `clerkhelpdesk@ncuc.gov`;
  SC `contact@psc.sc.gov`; IL `ICC.FOIARequests@Illinois.gov`; OH (PUCO web form or 614-466-6843); WV (Executive
  Secretary form or 304-340-0426).

**2–3 October (verification runs):**
- **Sweep fired off-schedule (run 2026-10-03-0019): worked, degraded.** The repo was private then and scheduled
  sessions can't attach it; OneDrive read/write, read-only mail, DCC Bi-Weekly, PA web reader and the manual-folder
  check all worked. Wrote `rows_p5` (§6).
- **Brief fired off-schedule: worked via the repo-less path.** Email sent (`[Status] Grid Docket — 3 Oct · 9
  high-impact …`, RED because of the repo regression); console v7 published with narrative and PDF;
  `briefs/2026-10-03.json` written.
- **Fix:** Rett made the repo public; both prompts now clone it read-only and build from `store_live/`; the task
  prompts were replaced with compact bootstraps and the crons re-set explicitly.
- Second-wave sources probed and working: MISO/SPP queues, 8 Legistar clients, capacity pages, VA appellate
  courts, 8 more governors, 6 of 7 IRP/RFP pages, DOE pages, ERCOT notice archive (23 links).
- 3 Oct: WebFetch confirmed for ERCOT large-load, planning and board pages, PJM newsroom, Kansas governor and Duke
  IRP; added to Sweep steps 6.4 and 6.6. Arizona governor refuses both routes.

**3 October, afternoon — full review:**
- Found and fixed: the degraded run had advanced the Sweep window past all 506 collector candidates (now a separate
  `collector_cursor`); Texas document links had been silently missed since the first run (site moved to absolute
  links — fixed, text being back-filled); Arizona PDFs are unreachable from the cloud (certificate hostname
  mismatch — routed to the manual pass); the backfill had text for only 357 of 5,210 filings (now nightly enrichment); the manual
  pass never looked for new cases and restarted from fixed dates (now catches up from its last run and searches
  for new cases); stale state entries and gaps queued for the Sweep (C-05); EIA and congress.gov running on the
  public DEMO_KEY.
- Removed: v1 reachability probe and its workflow, discovery outputs, the superseded architecture note, four
  obsolete project docs and the duplicate context copy, four v1 artifacts.
- Added: the Friday manual-pass reminder task.
- Verified in two extra collector runs the same afternoon: Texas documents extracting again (80 PUCT filings with
  text after the first fixed run); 217 current candidates back-filled with text ahead of Monday; 125 backfill
  items enriched (tiers 1–2: commission-issued and watched-party filings) with ~1,880 queued; party matching made
  whole-word after "AWS" matched "Dawson's"; EIA's public DEMO_KEY is rate-limited on shared runners (congress.gov
  works) — an `EIA_API_KEY` secret would avoid it.

**3–4 October, evening — wave 3 sources (verified from the runners):**
- Probed ~80 candidate URLs from GitHub Actions (`probe_adapter.py urls:<list>`, results in `data/debug/`), then built
  `collector/adapters3.py` and tested every adapter from the runners before a full collector run (run
  2026-10-04-0022: 48 new items, 62 documents, all new sources `ok` except NYISO ICAP, recorded as refused).
- **New Mexico documents repaired.** The e360 page's own requests were read in the built-in browser on Rett's
  computer: the list call needs `searchTerm` beside `caseId`, and documents download through an anonymous
  per-document ticket. From the runners: 84 + 81 + 2 documents in the window on 25-00079-UT, 25-00082-UT and
  26-0000062, text layers extracted. A docket-history backfill for NM (since 2025-11-07, up to 450 documents) was
  dispatched on 4 Oct; its items land in `data/backfill/` for the Sweep's C-07 queue.
- **ERCOT large-load status:** the large-load page and the LLWG/TAC/ROS/Board meeting pages now open to the runners;
  approved-to-energize and observed-peak figures extracted from the April–August 2026 Monthly Operational Overviews
  (e.g. 9,456 MW approved to energize, observed peak 4,316 MW, August 2026). ERCOT's MIS servlets are
  robots-disallowed and were not called.
- Working: Supreme Court of Texas orders, PA Commonwealth Court RSS, WV Supreme Court page, CourtListener state-court
  query, 7 local agenda lists (Atlanta's data-center incentive resolution and Storey County's data-center
  correspondence surfaced on the first run), Washoe County Legistar, NRC news RSS, FERC eCollection feed (Form 1 /
  3-Q / 714), FERC EQR via PUDL (10 new hyperscaler contract lines in 2026 Q2 vs Q1), LBNL via OSTI, Grid
  Strategies and four hyperscaler newsrooms.
- Refused and recorded (never worked around): `search.txcourts.gov` (robots), NYISO document library (empty
  HTTP 202 challenge), `emp.lbl.gov` / `eta.lbl.gov` (403), Oracle newsroom (403), Loudoun `lfportal` (robots
  unreadable) and `loudoun.granicus.com` (robots), Reno PrimeGov (robots), Storey's CivicPlus host (robots — the
  county's own AgendaCenter is used), ERCOT `/misapp/` (robots).
- Fixed along the way: `COURTLISTENER_TOKEN` was never passed to the collector job; robots.txt Crawl-delay is now
  honoured; Fairfax pages carry a "Data Centers" menu item, so their filter requires a land-use action nearby.

**Not yet verified end to end:** a scheduled Sweep reading collector data through the public clone — first test
**Monday 5 Oct, 03:54 PT**.

---

## 17. Sources

Full lists in the repo's `SOURCES.md` (project copy `claude/sources-v3.md`), revised 4 Oct 2026 for wave 3.

**In scope and working:** FERC eLibrary, FERC news, Federal Register, NERC; FERC Form 1 / 3-Q / 714 filing feed;
FERC EQR contracts with hyperscalers and data-center developers (PUDL); SEC EDGAR for 18 utility issuers and 17
market participants; all 8 RTOs, with ERCOT large-load status tables; 11 state commissions by collector or WebFetch
(TX, AZ listings, GA, LA, MO, NM — documents repaired 3 Oct, KS, OK, AL, PA, plus GRDA) and 7 by manual pass (VA, SC,
IL, OH, NC, WV, NV) with AZ documents; 10 of 16 IR pages (the rest via EDGAR); hyperscaler newsrooms (Microsoft,
Google, Amazon, Meta); governors' newsrooms in 16 states; party watch; MISO, SPP and PJM queues (PJM from its public exports, 4 Oct); capacity markets (NYISO
ICAP via the manual pass); state bills (Open States), federal bills (congress.gov), Regulations.gov, EIA-860M, NRC ADAMS and
the ERCOT Public API (all keyed, live 4 Oct); courts — Supreme Court of Texas, Virginia, West Virginia, PA Commonwealth Court (RSS),
CourtListener for all tracked states' appellate courts; local agendas — 9 Legistar clients plus Fairfax, Henrico,
Atlanta, Tulsa (Council, TMAPC, BOA) and Storey County; utility IRP/RFP pages; DOE; NRC news (RSS); LBNL via OSTI and
Grid Strategies; Utility Dive, Canary Media, RTO Insider feeds; licensed mail (RTO Insider, NPM, CapIQ, DCC Bi-Weekly).

**Keys:** all live since 4 Oct (EIA, congress.gov, Open States, CourtListener, Regulations.gov, NRC ADAMS, ERCOT Public API).
History for the new sources since 2025-11-07 was pulled on 4 Oct and is worked through by the Sweep (C-08).

**Candidates still open, ranked:** (1) agency allowlisting (letters drafted); (2) PJM Data Miner 2 (market data; the PJM
queue is already collected from public exports); (3) CAISO and NYISO queues; (4) S&P RRA / Halcyon / Energy Strategies as
cross-checks; (5) earnings call transcripts (CapIQ); (6) Loudoun County through the manual pass; (7) PUDL Form 1 data
tables; (8) direct state bill trackers.

---

## 18. Outstanding actions, gaps and open decisions

**Nothing else is required from Rett for the system to run.** Optional or recurring:
1. **Fridays:** keep the desktop app open around 9:04 am PT and click "Run now" (or run `/grid-docket-manual-pass`
   whenever convenient).
2. **Keys:** all saved and verified 4 Oct, including the ERCOT Public API sign-in. PJM API account still optional; a session with push access builds that adapter.
3. **Check once:** disable any desktop-local copies of the old tracker tasks (`utility-tracker-sweep`,
   `weekly-utility-brief`) if they still exist — a local Brief would send a second email.
4. **Optional decisions:** recipients after burn-in (only Rett now; possibly BODIpower@blueowl.com); whether a
   personal public GitHub repo is acceptable under Blue Owl policy long term (fallback: an Azure job, needs IT);
   Blue Owl branding for the narrative; Sonnet instead of Opus for the Brief to save cost; whether to license
   S&P RRA (the only fully cloud route to the seven blocked commissions).

**Remaining gaps and how they are filled:**

| Gap | Filled by |
|---|---|
| Seven blocked commissions (VA, SC, IL, OH, NC, WV, NV) | Manual pass weekly (dockets + new cases), cloud fallbacks between passes; S&P RRA if licensed |
| Nevada document content (no text layer) | Manual pass: text copies from the filer, FERC, SEC or intervenors (can be Verified when it is the same document from the filer, FERC or SEC); otherwise visual reading (Reported). Options: a public-records request to the PUCN for the documents as filed (filers usually submit searchable PDFs); S&P RRA |
| Docket history before 3 Oct for collector states | Nightly enrichment (~2 weeks) + Sweep C-07 |
| Arizona documents (ACC PDF host certificate mismatch) | Manual pass requests queued by the Sweep; automatic again if the certificate is fixed |
| Arizona governor, IR pages for Southern/Evergy/Exelon/OGE/Oncor/BHE | EDGAR exhibits and deck search; manual pass extra pages |
| ERCOT large-load data products, PJM market data | ERCOT Public API live 4 Oct (no large-load product published yet; checked nightly); PJM Data Miner (low priority). PJM queue: collected since 4 Oct |
| History of the new sources before they were added (bills, court decisions, county actions, Regulations.gov, ERCOT large-load series) | Pulled 4 Oct from 2025-11-07; the Sweep works through it 20 items a run (C-08) |
| NYISO ICAP documents (bot-management challenge) | Manual pass monthly; NYISO FERC filings |
| Loudoun, Reno, Fulton agendas | Not collectable (§10); Loudoun could join the manual pass |
| Never published (Kansas ESAs, GRDA terms, Entergy absolute GW, confidential filings) | Company disclosure only, or recorded as known unknowns |

**Next session should first:** read the 5 Oct Sweep run record (`/GridDocket/runs/`) and Brief record
(`/GridDocket/briefs/`); confirm the Sweep ran FULL (not degraded) and read the 2–3 Oct candidates; apply any
repair proposals; check `data/health/latest.json` → `backfill_text` progress; confirm all three scheduled tasks
are enabled; open the console and confirm the Brief republished v8 (sections 01–12, "What changed" showing the
5 Oct run, Coverage filled from the full state.json); add a `coverage_marks` line for the first full Sweep.

---

## 19. Process lessons (do not repeat)

- **Test every access method in the exact runtime it will run in.** v1 validated methods in a session with a
  browser; the scheduled task had none and wrote nothing. v3's first scheduled run then found that scheduled
  sessions can't attach a private repo — fixed by making it public.
- **Scheduled sessions differ from interactive ones:** no `add_repo`, so no push; treat the repo as read-only
  there and put repair proposals in the run record.
- **Updating a task's prompt can alter its schedule** — re-set the cron explicitly and verify `next_run_at`.
- **Cron is UTC unless `CRON_TZ` is set.** Both tasks use `CRON_TZ=America/Los_Angeles`.
- **A disabled task emits no failure notice** — two Mondays passed silently. Verify tasks are enabled after any
  change.
- **Connectors attach per scheduled task**; both tasks have M365 and Box.
- **Pushes from Actions can fail silently** — the first rerun and first backfill lost their data. The push step
  now rebases with `-X theirs` and fails the job loudly.
- **Workflow concurrency:** one pending run per group; a new push replaces a queued run. Use `[skip ci]` when
  pushing while a dispatched run is queued; parity has its own group.
- **First-run baselining hides history:** links already on a page at first sight were marked seen. Now
  re-listed into `baseline_links_<date>.jsonl` for triage.
- **Never set `last_successful_sweep` to the baseline date without intent** (v1's zero-length window).
- **Robots and consent:** verbal consent does not change what robots.txt says. An override was refused by the
  environment's safety controls; don't re-attempt by any route.
- **A robots.txt BOM can hide `Disallow: /`** — decode with utf-8-sig. Distinguish firewall pages from app shells.
- **Runner-refused is not WebFetch-refused** — PA, ERCOT pages, KS governor and Duke IRP open to WebFetch. Test
  both before declaring a source closed.
- **Subagent budgets overran on 6 of 8 attempts** — scope narrowly, set hard call budgets.
- **Dedupe on specific document URL**, not docket number; a shared search-landing URL is not a duplicate signal.
- **Check arithmetic between a stated level and a stated change** (the Duke +2.7/+3.1 error).
- **Binary files can't round-trip through the Graph text/base64 path**; build the workbook in the browser.
- **LibreOffice recalc times out on styled workbooks** — verify formulas on a stripped copy.
- **ExcelJS omits column width 9** (write 9.001); `<col>` spans group equal widths (expand before comparing).
- **From Claude sessions:** GitHub GraphQL unavailable (use `gh api` REST); Actions log downloads blocked (jobs
  commit diagnostics to `data/debug/`); the workspace shell can't reach most target hosts (test in Actions).
- **Check the console loads after every publish** (a syntax error once stopped it rendering).
- **Never let one cursor serve two inputs.** A degraded run that read only mail advanced the shared window and
  would have skipped every collector candidate; each input now has its own cursor.
- **A shared document budget starves whoever runs last.** The backfill spent its whole budget on FERC and
  Louisiana; spare-time enrichment with a tiered queue replaced it.
- **Party filings hide behind attorneys' names.** Match watched parties on the document's cover page, not only the
  filer field.
- **"Working" means text extracted, not items listed.** Texas and Arizona listed filings for days with no document
  text behind them; health now has to be read per document, and enrichment retries failures.
- **GitHub's scheduler is best-effort.** A scheduled run can start hours late or never; one trigger is not a
  schedule. Use several off-the-hour triggers with a guard so only one does the work, and check out `main` at job
  start. (4 Oct: the 06:17 UTC run started at 12:26 and was first misreported here as skipped — check the run list
  again before calling a run missed.)
- **The manual pass depends on Rett being present.** The Friday task asks first and never browses unattended.

---

## 20. Change log

| Date | Change |
|---|---|
| 2026-09-17/18 | v1/v2 built; baseline 161 events / 229 rows loaded; tasks later found disabled |
| 2026-10-02 | v3 built (collector, overlays, Excel parity, console v6, prompts, manual skill); first collector run; backfill dispatched |
| 2026-10-03 (pm) | Full review: collector cursor fix, nightly backfill enrichment, manual pass catch-up and new-case discovery, Friday reminder task, DEMO_KEY for EIA/congress.gov, cleanup of obsolete files, docs and artifacts |
| 2026-10-03 | Colorado and Oregon ruled out of scope for now. Off-schedule verification runs (degraded Sweep → `rows_p5`; Brief → console v7 + email); repo made public; prompts clone read-only; compact task bootstraps; second-wave sources; ERCOT archive; WebFetch fallback pages; backfill re-dispatched; this document rewritten |
| 2026-10-03 (eve) | Schedules changed by Rett: Sweep Mon 03:54 PT, Brief Mon 08:54 PT, manual-pass reminder Fri 09:04 PT (all `CRON_TZ=America/Los_Angeles`); §3, §4, §12, §16, §18 and `SOURCES.md` updated to match |
| 2026-10-04 | Wave 3 sources: Supreme Court of Texas, PA Commonwealth Court RSS, WV Supreme Court, CourtListener state courts; local agendas (Fairfax, Henrico, Atlanta, Tulsa ×3, Storey, Washoe); ERCOT large-load status with table extraction; NYISO ICAP (refused → manual pass); NRC news RSS and ADAMS (key); FERC Form 1/3-Q/714 feed and EQR (PUDL); LBNL via OSTI, Grid Strategies; hyperscaler newsrooms. NM documents repaired. `SOURCES.md` rewritten; §8–§12, §16–§18 updated |
| 2026-10-04 (am) | Consistency pass: NYISO ICAP refusal recorded as `refused_known` (no false RED); refused IL CUB mirror dropped; corrections item C-05 brought up to date (Arizona documents, ERCOT, New Mexico, NYISO, Texas courts); §3 file and watch-list counts corrected |
| 2026-10-04 (pm) | Collector schedule hardened after GitHub started the 4 Oct run six hours late: three nightly triggers (04:43, 06:17, 08:41 UTC) with a skip guard, checkout of the newest `main`, `last_full_run` and gap tracking; Sweep reports COLLECTOR_GAP, Brief treats it as amber |
| 2026-10-04 (pm) | Keys obtained by Rett; Regulations.gov adapter built; secrets wired into the collector and probe workflows; `common.scrub()` keeps keys out of the public repo |
| 2026-10-04 (eve) | PJM interconnection queue added with no key: serial/expedited `PlanningQueues.xml` and the cycle-queue XML export (adapter `queues` now reads XML and page export forms); verified from the runners (228 + 664 active tracked-state projects, baseline). PJM API key no longer needed for queue data |
| 2026-10-04 (eve) | Keys live: Open States, EIA, CourtListener, congress.gov, Regulations.gov, NRC ADAMS (ERCOT awaits its password). Open States and CourtListener paced to their per-minute limits; Open States filtered by bill title; NRC per-docket cap 200 |
| 2026-10-04 (eve) | ERCOT password added; ERCOT Public API sign-in verified; the adapter pages the full 120-product catalogue (no large-load product published yet) |
| 2026-10-04 (eve) | Console v8 (commit fbcce31): What changed, Matters, load-scenario tariff tester, conversion deltas and CLOA → ESA ratio, activity over time with coverage marks, Parties, Coverage map, period filter and shareable view links. `build_console.py` emits parts/changes/since/coverage/annotations/parties (`--state`, `--manual-dir`, `--since`); `brief.md` downloads state.json and the manual manifests; parity CI installs pyyaml. Published as artifact version 8 |
| 2026-10-04 (late) | Consistency pass: stale key statements removed; scheduler guard narrowed to 6 h (an afternoon run no longer suppresses the night's collection); history pull for the new sources since 2025-11-07 with corrections item C-08; Open States pages deeper in history pulls |
