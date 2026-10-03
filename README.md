# BODI — Grid Docket

Automated weekly tracker of regulatory and market activity for large-load (data-center) customers and large
generators: 25 utilities, 8 RTOs, 18 jurisdictions. Built for Blue Owl Digital Infrastructure.

**Start here:** [`docs/GRID_DOCKET_CONTEXT.md`](docs/GRID_DOCKET_CONTEXT.md) — the full context document
(constraints, architecture, schema, sources, access findings, open items). Source lists: [`SOURCES.md`](SOURCES.md).

| Path | What it is |
|---|---|
| `collector/` | Nightly GitHub Actions collector (`run.py`, adapters, backfill enrichment, probe and discovery tools) |
| `config/watchlist.yaml` | The one place to add or drop coverage |
| `data/` | Collector output: candidates, full-text filings, health, backfill |
| `prompts/` | Live instructions for the scheduled Sweep and Brief, their bootstrap prompts, the corrections queue |
| `tracker/` | Row-store validation, Excel and console builders, narrative PDF/DOCX |
| `console/` | The console page and its in-browser Excel builder |
| `manual/SKILL.md` | Copy of the manual-pass skill |
| `store/` | Frozen copy of the 2026-09-18 baseline for tests (the live store is in OneDrive) |

The collector honors robots.txt, identifies itself honestly, rate-limits per host, and never attempts to evade
bot defenses. This repository is public: nothing secret is ever committed; API keys live in repository secrets.
