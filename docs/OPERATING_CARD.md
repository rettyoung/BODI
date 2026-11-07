# Utility Tracker — operating card

**Read this first; open the full reference only for the section you need.** Owner: Rett Young
(rett.young@blueowl.com). Card written 2 November 2026. Reference: `docs/GRID_DOCKET_CONTEXT.md` (§ numbers below).
History (verification record, process lessons, change log): `docs/HISTORY.md`. When the docs and the repo disagree
on mechanics, `prompts/sweep.md` and `prompts/brief.md` are what actually runs.

## What it is (§1)
Weekly large-load and generation regulatory tracker for Blue Owl Digital Infrastructure: 25 utilities, 8 RTOs,
18 jurisdictions (AL AZ FERC GA IL KS LA MO NC NM NV OH OK PA SC TX VA WV, plus `US-Federal`). Every Monday: the
Excel master tracker (primary deliverable), a narrative (PDF/DOCX), the console artifact, and one email to Rett.
Reader-facing name "Utility Tracker"; "Grid Docket" only internally.

## Rules that never bend (§2)
- Fully cloud; OneDrive is the record. OneDrive unreachable → stop and report, never a local fallback.
- Read primary filings directly; no new subscriptions or docket e-notifications.
- Mail read-only (`outlook_email_search`, `read_resource` only). One send per week: the brief, to Rett only.
- Never create an account, enter a credential, solve a CAPTCHA or route around robots.txt.
- Keys only as repo secrets, added by Rett. The repo is public: nothing secret is ever committed.
- Licensed sources (NPM, CapIQ, RTO Insider, DCC): facts only, never their sentences.
- Cost-sensitive: validate before building anything expensive; stop at 90% usage.
- Schema is fixed (§5): 26 columns, one row per event × entity × jurisdiction, Event ID = discovery date,
  never delete a row (supersede/overlay), levers `1` or blank, Materiality High/Medium only.

## Where things are (§3)
| Thing | Where |
|---|---|
| Store (system of record) | OneDrive `/GridDocket/` — driveId `b!2OnbGRjzpEKUL9fVRRC4Lv4LSN1Bpb1PmI1aJZgbWGvvNTw6Z-6ISI31RRmmeISO`, folder `01MLUCMYJFKKTYR6ENBFDZOOAQQOLD5QNX`; manual `01MLUCMYLTL2DGJ4AHFBB2OJSZMLMPBRJU`, runs `01MLUCMYNQE5VMUQYLERCIPHUAB5IL4B4E`, briefs `01MLUCMYPB3OSQIZONA5FLUGQHMAZGKC3U` |
| Store mirror (transport only) | https://claude.ai/artifact/GiAXCPsEF9zoeT5A8dQjVG |
| Console | https://claude.ai/artifact/JJ8FYdvfZ2WPg6r4UpFXbW (`#dl.xlsx`, `#dl.pdf`) |
| Repo | `rettyoung/BODI` (public): `collector/`, `config/watchlist.yaml`, `data/`, `tracker/`, `prompts/`, `console/` |
| Scheduled tasks | Sweep `trig_01DA4N9G8Qv1zeggHuN9eQ3g` Mon 03:54 PT (Opus) · Brief `trig_01X19jgn9aMSPL5ov1TQ7bvj` Mon 08:54 PT (Sonnet) · manual pass `trig_015r1jt1qtx7CEYiyehWzSV2` Fri 09:04 PT on Rett's computer (Sonnet from 2 Nov; its model is changed only in the desktop app). Live prompts = `prompts/trigger_*.txt` |
| Tracker tools for scheduled runs | Rett's personal plugin `utility-tracker-tools` (v0.3.1, 7 Nov 2026 — `BODI_COMMIT` in the package names its commit): packaged copies of `tracker/`, `console/`, `config/watchlist.yaml`. Scheduled sessions may not run code cloned from GitHub, so they run these copies from `bodi_run/`. **Rebuild and re-upload it whenever `tracker/`, `console/` or the watch list change** (bump the version in `plugin/utility-tracker-tools/.claude-plugin/plugin.json`, then `python tools/build_plugin.py` writes the folder and zip to `dist/`, with `BODI_COMMIT` and `CODE_SHA256.txt`) |
| Store audit | The Friday manual pass runs the real scripts on Rett's computer and writes `/GridDocket/manual/audit_<run_id>.json`; the Sweep turns its failures into `AUDIT-…` obligations, the Brief reports it |
| Collector | GitHub Actions nightly, triggers 04:43/06:17/08:41 UTC, first one runs |

## Keeping things in step
Four copies must agree; change them together: the repo (`prompts/`, `tracker/`), the live task prompts (= `prompts/trigger_*.txt`), the `utility-tracker-tools` plugin (= `tracker/`, `console/`, watch list at `BODI_COMMIT`), and the saved `grid-docket-manual-pass` skill (= `manual/SKILL.md`). The project docs mirror `docs/`.

## How a week runs (§4)
Nightly collector → `data/` (candidates, full-text filings, health, backfill). Monday Sweep: lock → clone →
`store_sync.py load` (one call) → obligations first → health → `shortlist.py candidates` (scored table +
excerpts) → mail (incremental, haiku) → manual drops → web routes → classify → tariff delta, corrections, C-07
and C-08 batches (`shortlist.py backfill` / `c08`) → commit new part → `check_run.py` gate → run record → state →
mirror. Monday Brief: load → `brief_input.py` → audit the Sweep (`check_run.py`) → status → milestones →
opus writer (only `brief_input.json`) → build → publish console → email → brief record.

## Tools in `tracker/`
| Script | Use |
|---|---|
| `store_sync.py load` / `--recheck` | Byte-exact store load in one call; prints one line + FETCH lines |
| `shortlist.py candidates / backfill / c08 / excerpt` | Deterministic triage, dedupe and ≤8k-char excerpts |
| `brief_input.py` | Everything the Brief's writer needs, in one file |
| `rowstore.py` | Load, overlays, validation |
| `check_run.py` | Sweep completeness gate (also notes a missing `usage` block) |
| `usage.py` | Per-step context cost from run/brief records |
| `subtables.py`, `build_tracker.py`, `build_console.py`, `narrative.py` | Tariff deltas, Excel, console, narrative |

## Token discipline (sweep.md I11, brief.md I13)
Raw material (candidates, filings, store parts, mail bodies) never enters the main session; scripts and subagents
hand back compact results. haiku: mail, health, title triage · sonnet: extraction from excerpts · opus: judgment
(Sweep main) and the Brief's writing. Commands that print more than ~40 lines write to `work/`. Each run records
`usage` per step — `python tracker/usage.py <record>` shows where it went.

**Interactive sessions:** start from this card and the newest run record (`/GridDocket/runs/`). Open a reference
section only when the task needs it. Send broad repo searches to an Explore subagent. Don't paste the full
reference into a session.

## Open items (§18)
Arizona XHLF (C-03, manual pass); Virginia CIAC docket number; C-07 backfill draining 25 a run in strict mode (since 2026-01-01; 355 passing of 1,886 on 7 Nov, ~14 Sweeps; C-08 done);
seven blocked commissions via the Friday manual pass; NYISO ICAP monthly via manual pass. Optional decisions:
recipients after burn-in, S&P RRA licence, Blue Owl branding, the Brief's main model.
