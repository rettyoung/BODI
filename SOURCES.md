# Grid Docket — sources

Two lists: **scoped in** (collected today, by which process) and **candidates** (worth adding, ranked).
The watchlist (`config/watchlist.yaml`) is the operative list; this file explains it. Live health for every
collector source is in `data/health/latest.json`, refreshed nightly.

**Processes.**

| Code | Process | Where it runs | Cadence |
|---|---|---|---|
| **C** | Nightly collector (GitHub Actions, `collector/`) | Cloud | Daily 06:17 UTC (~23:17 PT) |
| **S** | Weekly Sweep (Claude scheduled task) | Cloud | Mon 03:54 PT |
| **B** | Weekly Brief (Claude scheduled task) | Cloud | Mon 08:54 PT |
| **M** | Manual browser pass (skill `grid-docket-manual-pass`) | Rett's computer, Claude desktop app | Reminder Fri 09:04 PT (runs only on "Run now"), or whenever run; picked up by the next Sweep |

**Retrieval depth.** *Full text* = the primary document is downloaded and its text extracted (OCR when it has no
text layer). *Metadata* = filing list only. *Mirror* = the same document from a permitted host other than the
agency's own docket system.

---

## 1. Scoped in

### 1a. Federal

| Source | What it gives | Process | Depth | Notes |
|---|---|---|---|---|
| Governors' newsrooms (TX, VA, GA, AZ, PA, OH, LA, NC) and PUCT news | Executive orders and directives — no docket exists for these | C | Full text | Added after the Aug 2026 Texas audit directive was missed. Keyword-filtered. |
| FERC eLibrary (JSON API) | Every filing in watched dockets + keyword search across all filings | C | Full text | 15 watched dockets incl. EL25-49, EL26-67…72, RM26-4, AD24-11. Downloads via `DownloadP8File`. |
| FERC news & Commission meeting pages | Orders, Commission actions, press | C | Full text | Page watcher. |
| Federal Register API | Rules, notices, executive orders from FERC, DOE, EPA, NRC, EOP | C | Full text | Term filter (large load, data center, 202(c), co-location…). |
| NERC news & announcements | Standards, reliability assessments, Level 2/3 alerts | C | Full text | Page watcher. |
| SEC EDGAR (submissions + full-text search) | 8-K (2.02, 7.01, 8.01, 1.01, 2.01), 10-Q, 10-K, 40-F, 6-K for 18 utility issuers and 17 market participants | C | Full text | Declared UA `BlueOwl-RegTracker/4.0 (rett.young@blueowl.com)` per SEC fair-access policy. Hyperscalers, IPPs, data-center REITs, miners, GE Vernova. |
| FERC/ERCOT mail (Outlook folders "FERC", "ERCOT") | eSubscription notices with accession numbers | S | Full text (PDF attachments via `read_resource`) | Read-only. |

### 1b. Market operators (all eight tracked as first-class entities)

| RTO | Source | Process | Depth | Notes |
|---|---|---|---|---|
| PJM | FERC dockets (EL25-49, EL26-67, ER26-*); Inside Lines RSS | C | Full text | Inside Lines now serves a CAPTCHA to automated clients — recorded, not bypassed; PJM content arrives via FERC and RTO Insider. |
| MISO | Media center (rendered); FERC dockets (EL26-70) | C | Full text | |
| SPP | Newsroom; FERC (EL26-68) | C | Full text | |
| ERCOT | Market notices; news releases; PUCT dockets (NPRR/PGRR approvals) | C | Full text | |
| CAISO | News releases (rendered); FERC (EL26-71) | C | Full text | |
| NYISO | Press releases; FERC (EL26-69) | C | Full text | |
| ISO-NE | Press releases; FERC (EL26-72) | C | Full text | |
| Western Power Pool / WRAP | News | C | Full text | |

### 1c. State commissions — 18 jurisdictions

| Jur. | Primary system | Process | Depth | Status / method |
|---|---|---|---|---|
| AZ | ACC eDocket JSON API (`efiling.azcc.gov/api/edocket`) | C, S | Full text | Docket search and full filing lists work (verified 2026-10-02); consumer-comment letters skipped. PDFs from `images.edocket.azcc.gov` (incomplete TLS chain completed via AIA; verification stays on). |
| GA | GA PSC docket facts + document download API | C | Full text | |
| TX | PUCT Interchange filing lists + `/Documents/*.PDF` | C | Full text (OCR on scanned filings) | TX figures from OCR stay *Reported* until re-read. |
| LA | LPSC Valence portal (DocketSearch, Docket_Documents, RecentOrders) | C | Full text | Ligature-corrupted text is summarized, never quoted. |
| MO | PSC EFIS (case search → filing display) | C | Full text | |
| NM | PRC e360 case API (CaseX envelope) | C, M | Case metadata (C); documents via manual pass | Case search works; the public-document endpoint returns empty with the documented envelope — being repaired from probe data. |
| KS | KCC meeting minutes PDFs + kcc.ks.gov documents | C | Full text | Evergy ESAs under the LLPS tariff are never docketed — investor disclosure covers them. |
| OK | OCC Laserfiche WebLink (case documents); GRDA board agendas/minutes | C | Full text | WebLink recovered 2026-10-02; each hit confirmed against the PUD cause number on page 1. GRDA has no commission docket; board pages are the record. |
| AL | PSC public-access RSS (documents, hearings) | C, S | Full text | The PSC's RSS endpoints returned HTTP 500 (server fault) on 2026-10-02; Claude's reader covers the docket pages until they recover. |
| PA | PUC docket pages | S | Full text | GitHub runners are refused at TLS; Claude's web reader works. |
| VA | SCC docket search (Breeze API) | M + S fallback | Full text (M) | robots.txt admits named search engines only. Cloud fallback: utility/intervenor copies, FERC/SEC attachments, search. Allowlist letter drafted. |
| NC | NCUC (`starw1`) | M + S fallback | Full text (M) | Cloudflare challenge. Fallback: NCUC main-site PDFs (C, mirror), NCUC subscription mail (S). Allowlist letter drafted. |
| SC | PSC DMS | M + S fallback | Full text (M) | `Disallow: /`. Fallback: PSC latest-publications and ORS electric pages (C, mirror). Letter drafted. |
| IL | ICC e-Docket | M + S fallback | Full text (M) | `Disallow: /` + CAPTCHA. Fallback: CUB filings (C, mirror). Letter drafted. |
| OH | PUCO DIS | M + S fallback | Full text (M) | Firewall rejects automated clients. Fallback: OCC (Consumers' Counsel) filings (C, mirror). |
| WV | PSC WebDocket | M + S fallback | Full text (M) | 403 to automated clients. WebDocket's own text layer (ViewText) is the best source when reached by M. |
| NV | PUCN (`puc.nv.gov`, `pucweb1`) | M + S fallback | Metadata (no text layer on any document) | robots.txt disallows all bots. |
| FERC | see 1a | C | Full text | |

### 1d. Companies — earnings and investor materials

| Source | Issuers | Process | Depth | Notes |
|---|---|---|---|---|
| Events-and-presentations pages (rendered; PDF links harvested, never guessed) | AEP, Duke, Dominion, Entergy, Ameren, PPL, Pinnacle West, Xcel, Fortis (for TEP), TXNM | C | Full text | Full pass in earnings windows; quarter-over-quarter deltas against `pipeline_baselines_for_delta`. |
| Same, where the IR page refuses automated clients | Southern (Incapsula), Evergy, Exelon, OGE, Oncor (robots.txt), BHE (CAPTCHA) | C (EDGAR exhibits) + S | Full text | Decks taken from 8-K exhibits, or found by search on the permitted q4cdn PDF host. The refusing pages are never fetched. |
| EDGAR 8-K Item 2.02 / 7.01 | same + market participants | C | Full text | Earnings trigger; the deck itself comes from the IR page. |

### 1d-bis. Party watch

Any filing in a watched docket **by** Microsoft, Google, Amazon/AWS, Meta, Oracle, OpenAI, CoreWeave, the Data Center
Coalition, major data-center developers, IPPs (Constellation, Vistra, NRG, Talen), industrial-customer groups or the
main intervenors is tagged by the collector and treated as material by the Sweep (`parties` in the watchlist).

### 1e. News and licensed mail (discovery and cross-check — never sole basis for *Verified*)

| Source | Process | Treatment |
|---|---|---|
| Utility Dive RSS | C | Keyword-filtered leads; confirmed against primary documents. |
| Canary Media RSS | C | Same. |
| RTO Insider RSS + daily mail (`today@rtoinsider.com`) | C, S | Licensed: facts cited, sentences never reproduced. RSS is cross-check only (~10 items). |
| New Project Media alerts (`alerts@newprojectmedia.com`) | S | Licensed. Load/generation projects; 16% haircut on announcement-stage MW. |
| S&P Capital IQ / RRA alerts | S | Licensed. Rate-case status, authorized ROE, transactions. |
| NCUC subscription mail | S | Only cloud discovery route for Duke NC. |
| Web search (Claude) | S | Leads and refutations for manual-route states; never *Verified* on a snippet. |

### 1f. Keyed public data (adapters built 2 Oct; each runs once its free key is added as a repo secret)

| Source | Secret | Use |
|---|---|---|
| EIA Open Data v2 (Form 860M planned additions/retirements) | `EIA_API_KEY` (recommended — the public DEMO_KEY is often rate-limited on shared runners) | Cross-check utility commission claims; only public window into GRDA, NOVEC, AEPCO. |
| congress.gov API | `CONGRESS_API_KEY` (optional — runs on DEMO_KEY) | Federal bills on data centers, permitting, grid reliability. |
| Open States API | `OPENSTATES_API_KEY` | State bills in all 18 jurisdictions (NV and TX legislate in odd years only). |

| CourtListener | `COURTLISTENER_TOKEN` (optional) | Opinions on large-load / tariff / co-location matters run keyless; the token adds federal docket (RECAP) search. |

### 1g. Added 2 October 2026 (second wave; first nightly run verifies each)

| Source | What it gives | Process |
|---|---|---|
| MISO and SPP interconnection queues | Monthly snapshot; new projects ≥100 MW and MW totals by tracked state | C |
| ERCOT load / board pages | Large-load interconnection updates, monthly operational overview | C |
| Capacity markets: PJM RPM, MISO PRA, NYISO ICAP, ISO-NE FCM, SPP resource adequacy | Auction results and planning parameters | C |
| Appellate courts: Virginia Supreme Court and Court of Appeals, Pennsylvania Commonwealth Court; CourtListener searches | Appeals of commission orders (e.g. Rider T1) | C |
| Governors' newsrooms / executive orders: AL, IL, KS, MO, NM, NV, OK, SC, WV (adds to TX, VA, GA, AZ, PA, OH, LA, NC) | Executive actions with no docket | C |
| County and city agendas via Legistar (Prince William, Loudoun, Fairfax, Henrico, Maricopa, Phoenix, Mesa, Columbus, Fulton, Atlanta, San Antonio, Fort Worth, Kansas City, Tulsa, Reno) | Rezonings, special exceptions, moratoria for data centers | C |
| Utility IRP / RFP pages: Dominion, Duke Carolinas, Georgia Power, APS, Entergy RFPs, Evergy, Xcel/SPS | Supply additions and procurement before they reach a docket | C |
| DOE newsroom, 202(c) orders, Loan Programs Office; NRC news; Federal Register terms for restarts, uprates, SMRs, loan guarantees | Federal financing, emergency orders, nuclear supply | C |

**Not yet possible:** PJM and ERCOT queue files (both require a registered key — PJM Planning API, ERCOT MIS);
commission e-docket systems in VA, SC and IL (consent received verbally, but the sites' robots.txt still refuses
automated clients — see §2 row 1); OH, NC and WV (technical blocks).

---

## 2. Candidates for addition

Ranked by value to the deliverable per unit of effort. **Effort**: S = config change, M = new adapter, L = new adapter + data model.

| # | Source | Why it matters | Access | Effort | Recommendation |
|---|---|---|---|---|---|
| 1 | **Agency allowlisting (VA, NC, SC, IL, OH, WV)** | Moves six states from manual to nightly full-text collection | Letters drafted in Outlook (not sent) | S once granted | Send the six drafts. Each grant flips that state's `route` to `collector`. |
| 2 | **EIA, congress.gov, Open States keys** | Legislative coverage in all 18 states + EIA cross-check, already coded | Free keys, 2 minutes each | S | Add as repo secrets. |
| 3 | **RTO interconnection queue files** (PJM, MISO, SPP, ERCOT GIS report, CAISO, NYISO) | Large-load and generator queue positions by county; earliest signal of new campuses and supply | Public downloads; PJM needs a free Data Miner key | M | Add monthly snapshots and report deltas by tracked territory. |
| 4 | **ERCOT large-load interconnection status report** | ERCOT's own count of large loads requesting/energized — the Texas demand curve | Public monthly report | S–M | Add as a dated watch page with table extraction. |
| 5 | **Capacity auction results & planning parameters** (PJM BRA, MISO PRA, NYISO ICAP, ISO-NE FCA) | Directly sets the capacity cost that large-load tariffs pass through | Public reports | S | Add the result pages as watch pages; parse clearing prices into metrics. |
| 6 | **CourtListener / PACER RECAP** | Appeals of tariff orders (e.g., Rider T1, Schedule LPS), federal challenges to FERC orders | Free API key | M | Add a docket-watch adapter for named cases + party search. |
| 7 | **State appellate courts** (VA Supreme Court, PA Commonwealth Court, TX 3rd Court of Appeals, etc.) | Where commission orders are actually overturned | Public sites; varied | M | Start with VA and TX, where appeals are already on file. |
| 8 | **Governor executive orders & state energy offices** | Siting/streamlining EOs, data-center incentive changes | Public pages | S | Add 18 watch pages (one per governor's EO list). |
| 9 | **County / municipal zoning and planning agendas** (Loudoun, Prince William, Fairfax, Maricopa, Bexar, etc.) | Earliest campus signal, moratoria, noise and water conditions | Public agendas; many on Granicus/Legistar APIs | L | Pilot on 6 high-activity counties via Legistar API. |
| 10 | **State legislature bill trackers (direct)** | Fallback if Open States lags | Public | M | Only if Open States proves insufficient. |
| 11 | **Utility IRP and RFP portals** (Dominion, Duke, Georgia Power, APS, Entergy RFP sites) | Supply additions and procurement before they reach a docket | Public pages | S | Add as watch pages. |
| 12 | **DOE Grid Deployment Office / LPO announcements; DOE 202(c) orders** | Federal financing and emergency-dispatch orders affecting supply | Public | S | Add to Federal Register terms and a DOE watch page. |
| 13 | **NRC licensing (ADAMS) for restarts/uprates/SMRs** | Nuclear supply for co-location (Palisades, Crane, Duane Arnold, SMR COLs) | ADAMS public API | M | Add named dockets. |
| 14 | **Hyperscaler sustainability / PPA announcements** | Counterparty commitments not filed with regulators | Company newsrooms | S | Add newsroom watch pages for MSFT, GOOGL, AMZN, META, ORCL. |
| 15 | **Earnings call transcripts** | Management commentary on large-load pipeline not in decks | Licensed (CapIQ) or company-posted | S–M | Use CapIQ transcripts if the licence covers it. |
| 16 | **S&P RRA / Halcyon / Energy Strategies / DELTa dataset** | Pre-structured docket tracking across all states | Licensed | S once licensed | Evaluate as a cross-check, not a replacement for primary filings. |
| 17 | **LBNL / Grid Strategies large-load and queue studies** | Benchmarks for the narrative | Public PDFs | S | Annual watch. |
| 18 | ~~Colorado and Oregon~~ | **Out of scope for now (Rett, 3 Oct 2026).** | — | — | — |
| 19 | **FERC Form 1 / EQR** | Utility financial and wholesale contract data (special contracts, PPAs) | Public | L | Defer; low weekly value. |
