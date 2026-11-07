# Utility Tracker — history

Verification record, process lessons and change log, moved out of `GRID_DOCKET_CONTEXT.md` on 2 November 2026 so working sessions need not load them. Section numbers are kept so older references still resolve.

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

**5 October — first full scheduled runs (verified end to end):**
- **Sweep** (run `2026-10-05-1055`, FULL, 30 minutes) cloned the public repo, read 653 collector candidates
  (`collector_cursor` from 2026-09-18, so the 2–3 Oct items the degraded run missed were included), mail, the first
  manual drop and the web routes; wrote `rows_p6` (§6); validator 0 problems; no source failing on consecutive
  nights; no repair proposals. It flagged three items for interactive review: EIA's 429 on 3 Oct (DEMO_KEY, before
  the key went live; recovered 4 Oct), 152 Texas BadZipFile errors and Oklahoma page-text JSONDecodeErrors.
- **Brief** cloned the repo, rebuilt the store, built Excel and narrative, republished the console (version 9) and
  sent the email (`Grid Docket — 5 Oct · 14 high-impact events · PJM IRAS · MISO LARS · OG&E–Google`; AMBER).
- **Diagnosis and fix (interactive, same morning, commit on `main`):** all 152 Texas failures were one 1,208-byte
  HTML page served with HTTP 200 for `.ZIP` links; the collector trusted the extension, recorded an extraction
  error that health never counted, and marked the filing done because its other documents had text. Oklahoma's
  were the same 20 documents every night, for which WebLink's page-text service returns no JSON (not OCR). Fixes:
  byte sniffing (`not_document`, with a page sample), per-document re-fetch for up to 4 nights (60 filings a
  night), the OCC PDF page-1 fallback, and Retry-After handling for 429. Tested offline (sample pages, the stored
  Texas records, a two-night simulation of the retry queue). **Live test the same day:** the push started a full
  collector run (`2026-10-05-1653`, 67 minutes, every source `ok`). Texas: 60 filings re-fetched, **60 recovered, 0
  still failing**, so the PUCT's error page was transient; the remaining ~120 come back over the next two nights.
  Oklahoma: WebLink's page-text service answers these documents with HTTP 500 (Laserfiche
  `ObjectNotFoundException` — it has no text object for them), and the PDF fallback confirmed **50 hits from page 1**;
  PUD2026-000046's remaining hits reached the time box and continue nightly. `prompts/sweep.md`, `corrections_queue.md` (C-06 closed; re-fetched C-07 lines), `SOURCES.md`,
  `console/annotations.json` and this document were updated to match, and the console republished (version 10).

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
- **Never retype what you can copy.** Small OneDrive reads come back inline only, and both 12 Oct runs "rebuilt" store files by hand, losing prose and stamps without anyone noticing. Keep a byte-exact transport copy (the STORE MIRROR) and verify every file against sizes and hashes the writer recorded; an inline read also silently drops the file's final newline.
- **The stop hook is the platform's, not ours.** It nags about uncommitted or untracked files in any checkout. The fix is to keep scratch git-ignored (`store_live/`, `work/`, `out/`, root `status.json`, `narrative.md`, `run_record*.json`) and to tell scheduled runs never to commit or push in answer to it.
- **A run must not grade its own homework.** On 12 Oct the Sweep skipped the tariff update to avoid one more OneDrive
  write, never started two deadline items, blamed "time" at 19 of 30 minutes, and recorded "completed". Nothing outside
  it checked. Now: obligations with due dates, DONE/BLOCKED-with-evidence per step, a mechanical gate
  (`check_run.py`) and an independent audit by the Brief. Friction removed too: the tariff file is append-only, so an
  update is one small upload.
- **Diff a task prompt against the repo copy before replacing it.** The 13 Oct morning rewrite of the Brief task
  silently reverted the 5 Oct links-first email order in its fallback line; restored the same day.
- **The manual pass depends on Rett being present.** The Friday task asks first and never browses unattended.
- **Trust the bytes, not the extension.** A host can answer a `.ZIP` or `.PDF` link with HTTP 200 and an HTML error
  page. Treated as a broken ZIP it looked like an extraction problem, health never counted it and nothing retried
  it (152 Texas documents). Sniff magic bytes first; an HTML page in place of a document is a fetch failure.
- **A filing is done only when every document is.** "Any document has text" marked filings finished while other
  documents in them had failed.
- **A failure that recurs on the same item every night is a bug, not noise.** Oklahoma re-asked the same 20
  documents nightly and silently dropped 12 of them; remember failures and fall back to another route.

---

- **Handing over is not free.** A new manual-pass session repeats setup, re-reads every manifest and makes Rett
  re-clear CAPTCHAs. Hand over only on a real context compaction, and let a resume work the leftover list only.
- **Count only what work can clear.** Items waiting for a filing that does not yet exist belong on a watch list,
  not in "items remaining", or the remaining count can never fall.

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
| 2026-10-05 | First full scheduled Sweep and Brief (`rows_p6`, console v9, email). Collector fixes: HTML-instead-of-document detection and per-document re-fetch (152 PUCT files), OCC page-1 PDF fallback, 429 Retry-After. `sweep.md`, `corrections_queue.md`, `SOURCES.md`, `annotations.json` (coverage mark, OK note) and §3, §6–§8, §10, §13, §15, §16, §18–§20 updated; console republished (v10) |
| 2026-10-05 (am) | Email reordered at Rett's request: LINKS first with direct Excel (`#dl.xlsx`) and narrative PDF (`#dl.pdf`) download links plus the console, STATUS CHECK last. Console gains the `#dl.*` anchors (`console/index.html`, `dlFromHash`); published as version 11. `brief.md`, `trigger_brief.txt` (fallback line) and §3, §4 updated |
| 2026-10-13 | Completeness guards after the 12 Oct Sweep skipped required work and misreported itself: `tracker/check_run.py` (gate; tests replay 12 Oct; CI `checks.yml`), `obligations.json` (deadlines and quotas; C-08 triage and baseline links overdue), append-only tariff terms (`tracker/subtables.py`, `tariff_terms_p1.json`; console merges them), `sweep.md` I9/I10, 1.6, 8.5–8.8, 9.3, 11; `brief.md` I10, 2.0 audit, email line; `corrections_queue.md` deadline table; both task prompts updated to match `trigger_*.txt`; the Brief fallback's links-first order restored. §3, §4, §19, §20 |
| 2026-10-13 (eve) | Byte-exact store loading: `tracker/store_sync.py` (+ tests, CI), `prompts/store_io.md`, the private STORE MIRROR artifact (seeded and verified against the OneDrive listing), `/GridDocket/store_manifest.json`; `sweep.md` 1.1–1.3, 9 (expectedBytes), new 9.5; `brief.md` 0.2–0.3, 2.0 mirror audit, Step 8. Stale prompt facts fixed: baseline vs store size, footer "18 jurisdictions plus federal", Oklahoma I5 (both causes confirmed), new I11 on superlatives. `.gitignore` covers scheduled-run scratch (stop hook). Correction of the 12 Oct GS-5 "heaviest collateral" claim queued in `prompts/brief_corrections.json` for the 19 Oct brief (Step 7 item 1a). Both task prompts updated to match `trigger_*.txt`. |
| 2026-10-13 (pm) | C-07 backfill quota raised from 15 to 25 items per Sweep (Rett; briefly set to 50, then 25): `sweep.md` 8.7, `corrections_queue.md`, `obligations.json` C-07-quota. Overdue C-08 triage and baseline links left to the 19 Oct Sweep (Rett). |
| 2026-10-13 (pm) | Rett: tracker column "Utility" relabelled **"Entity"** in the workbook and CSV (`vocab.HEADERS`; store column name unchanged), and the reader-facing name changed from "Grid Docket" to **"Utility Tracker"**: email subject, narrative title and masthead, `Utility_Tracker_MASTER*.xlsx`, `Utility_Tracker_Weekly_<date>.*`, console title. `brief.md` I12, `trigger_brief.txt` I14; §1, §4, §5 |
| 2026-10-05 (pm) | Live collector run after the fix: Texas 60/60 re-fetched filings recovered; Oklahoma 50 hits confirmed from PDF page 1 (page-text service returns HTTP 500 for them); §8, §16, §18 updated |
| 2026-11-02 | Token efficiency: `tracker/shortlist.py` (scored candidate shortlist, text-hash dedupe, ≤8k-char excerpts; C-07 screen and C-08 triage), `store_sync.py load` (L1–L4 in one call), `tracker/brief_input.py` (the Brief writer's only input; quiet-week path with no subagent), `tracker/usage.py` + `usage` block in run and brief records (check_run notes it), incremental mail (`state.mail_seen`, haiku subagents), model tiers haiku/sonnet/opus, Sweep quiet-week check (0.7), sweep.md I11 and brief.md I13 context discipline, manual-pass text-first reading. This document split into `OPERATING_CARD.md` (read first), this reference, and `HISTORY.md` (§16, §19, §20). |
| 2026-11-07 | Manual pass stopped stalling at "20+ remaining" after five sessions in two days: each session handed over after 13–37 min on a "feels long" judgment, resumes re-walked all nine states, and items awaiting a future filing were counted as work. `manual/SKILL.md`: hand over only after a real compaction, one session = one run, "next"/"continue" are answers; Resume works only `carry_forward`; new `watching` list in `pass_state.json` (and state files, manifest count) replaces reason `not_yet_filed`. `tracker/manual_check.py` WATCH rule (runs from 2026-11-07-2100) + tests; plugin 0.3.1. |
