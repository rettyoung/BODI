# Grid Docket — sources

Three lists: **scoped in** (collected today, by which process), **refused** (sources that turn automated
clients away, and what covers them instead) and **candidates** (worth adding, ranked). The watchlist
(`config/watchlist.yaml`) is the operative list; this file explains it. Live health for every collector source
is in `data/health/latest.json`, refreshed nightly. Last full revision: 4 October 2026 (wave 3).

**Processes.**

| Code | Process | Where it runs | Cadence |
|---|---|---|---|
| **C** | Nightly collector (GitHub Actions, `collector/`) | Cloud | Nightly; triggers at 04:43, 06:17 and 08:41 UTC (21:43, 23:17, 01:41 PDT) — the first to start runs, the others skip |
| **S** | Weekly Sweep (Claude scheduled task) — mail, web reader (WebFetch/WebSearch), classification | Cloud | Mon 03:54 PT |
| **B** | Weekly Brief (Claude scheduled task) | Cloud | Mon 08:54 PT |
| **M** | Manual browser pass (skill `grid-docket-manual-pass`) | Rett's computer, Claude desktop app | Reminder Fri 09:04 PT (runs only on "Run now"), or whenever run; picked up by the next Sweep |

**Retrieval depth.** *Full text* = the primary document is downloaded and its text extracted (OCR only when it
has no text layer; OCR figures stay *Reported*). *Metadata* = listing only (title, date, filer, link).
*Mirror* = the same document from a permitted host other than the agency's own docket system. *Filtered* =
the item is fetched but kept only if its text matches that source's own beat pattern (agendas, newsrooms,
court lists), because the general keyword list is too loose there.

---

## 1. Scoped in

### 1a. Federal

| Source | What it gives | Process | Depth | Notes |
|---|---|---|---|---|
| FERC eLibrary (JSON API) | Every filing in watched dockets + keyword search across all filings | C | Full text | 15 watched dockets incl. EL25-49, EL26-67…72, RM26-4, AD24-11. Downloads via `DownloadP8File`. |
| FERC news & Commission meeting pages | Orders, Commission actions, press | C | Full text | Page watcher. |
| **FERC Form 1 / 3-Q / 714** (eCollection XBRL feed) — *new 3 Oct* | Annual and quarterly financial filings of the tracked utilities' operating companies; RTO and planning-area Form 714 (hourly load and 10-year load forecast) | C | Metadata + link to FERC's HTML rendering | Keyless `ecollection.ferc.gov/api/rssfeed` (newest ~650 filings). Filers matched on entity aliases + `ferc_form_filers`. The Sweep reads a rendering only when it carries a new load forecast or large-customer figure. |
| **FERC Electric Quarterly Reports** (contracts) — *new 3 Oct* | New wholesale contracts whose counterparty is a hyperscaler or data-center developer (Google Energy, Amazon Energy, Microsoft Energy, Meta, …): seller, product, price terms, term, delivery BA | C | Derived dataset (quarterly) | Read from Catalyst Cooperative's PUDL build of FERC EQR (public S3 parquet, ~3 MB a quarter), compared with the previous quarter. *Reported* until confirmed against FERC's own EQR. Counterparty list: `eqr_counterparties`. |
| Federal Register API | Rules, notices, executive orders from FERC, DOE, EPA, NRC, EOP | C | Full text | Term filter (large load, data center, 202(c), co-location, restart, uprate, SMR, loan guarantee…). |
| NERC news & announcements | Standards, reliability assessments, Level 2/3 alerts | C | Full text | Page watcher. |
| DOE newsroom, 202(c) orders, Loan Programs Office | Federal financing and emergency-dispatch orders | C | Full text | Page watchers. |
| **NRC news releases** (RSS) — *repaired 3 Oct* | Restarts, uprates, SMR construction permits, mandatory hearings | C | Full text (filtered) | `nrc.gov/public-involve/rss?feed=news` replaces the old news page, which rendered 0 links. NRC's CDN has returned an occasional HTTP 403 to the runners; health shows it. |
| **NRC ADAMS** (Public Search API) — *new 3 Oct, needs key* | Every document added to the named dockets: Palisades 50-255, Crane/TMI-1 50-289, Duane Arnold 50-331, Kairos Hermes 2 50-611/612, TerraPower Kemmerer 50-613, Long Mott 50-614, TVA Clinch River 50-615, Holtec Pioneer 50-616/617 | C | Full text | Adapter built; runs once the free key `NRC_APS_KEY` is a repo secret (§1j). The old Web-Based ADAMS host no longer resolves. |
| SEC EDGAR (submissions + full-text search) | 8-K (2.02, 7.01, 8.01, 1.01, 2.01), 10-Q, 10-K, 40-F, 6-K for 18 utility issuers and 17 market participants | C | Full text | Declared UA `BlueOwl-RegTracker/4.0 (rett.young@blueowl.com)` per SEC fair-access policy. Hyperscalers, IPPs, data-center REITs, miners, GE Vernova. |
| FERC/ERCOT mail (Outlook folders "FERC", "ERCOT") | eSubscription notices with accession numbers | S | Full text (PDF attachments via `read_resource`) | Read-only. |
| congress.gov | Federal bills on data centers, permitting, grid reliability | C | Metadata | Public DEMO_KEY; `CONGRESS_API_KEY` optional. |
| EIA Open Data v2 (Form 860M) | Planned/under-construction capacity by state; cross-check for GRDA, NOVEC, AEPCO | C | Data | Public DEMO_KEY, often rate-limited on shared runners; `EIA_API_KEY` recommended. |

### 1b. Market operators (all eight tracked as first-class entities)

| RTO | Source | Process | Depth | Notes |
|---|---|---|---|---|
| PJM | FERC dockets (EL25-49, EL26-67, ER26-*); RPM capacity page; newsroom (S) | C, S | Full text | Inside Lines RSS serves a CAPTCHA to automated clients — recorded, not bypassed. PJM queue data needs a PJM API key (§3). |
| MISO | Media center (rendered); PRA capacity page; interconnection queue API (monthly snapshot, ≥100 MW deltas by tracked state); FERC (EL26-70) | C | Full text / data | |
| SPP | Newsroom; resource-adequacy page; active queue CSV (monthly); FERC (EL26-68) | C | Full text / data | |
| ERCOT | Market-notice archive; news releases; PUCT dockets (NPRR/PGRR approvals); **large-load interconnection status — *new 3 Oct*** | C, S | Full text | **Large-load status:** the `ercot_large_load` adapter reads the LLWG, TAC, ROS and Board meeting pages and the large-load integration page (all open to the runners as of 3 Oct), fetches matching `/files/docs/` materials and the Board's Monthly Operational Overview, and extracts the status rows and headline figures (MW approved to energize, observed peak consumption of those loads, large-load requests) with the sentence each came from. ERCOT's MIS data-product servlets are disallowed by its robots.txt and are not called; the ERCOT Public API route is built and switches on with its secrets (§1j). The Sweep's web reader remains the cross-check (planning page, notices). |
| CAISO | News releases (rendered); FERC (EL26-71) | C | Full text | |
| NYISO | Press releases; FERC (EL26-69); **ICAP document library — *see §2*** | C, M | Full text | The ICAP page's documents load from NYISO's document-library API, which answers automated clients with an empty HTTP 202 (bot-management challenge). The `nyiso_icap` adapter records that refusal as `refused_known` (not a nightly failure) and stops; ICAP auction summaries and demand-curve documents come from the manual pass (monthly extra page) and NYISO's FERC filings. |
| ISO-NE | Press releases; FCM page; FERC (EL26-72) | C | Full text | |
| Western Power Pool / WRAP | News | C | Full text | |

### 1c. State commissions — 18 jurisdictions

| Jur. | Primary system | Process | Depth | Status / method |
|---|---|---|---|---|
| AZ | ACC eDocket JSON API (`efiling.azcc.gov/api/edocket`) | C (listings), M (documents) | Metadata (C); full text (M) | Docket search and full filing lists work; consumer-comment letters skipped. The PDF host `images.edocket.azcc.gov` presents a certificate for another hostname (since ≥3 Oct) and `docket.images.azcc.gov` is robots-disallowed, so documents go to the manual pass (queued by the Sweep). Rechecked weekly. |
| GA | GA PSC docket facts + document download API | C | Full text | |
| TX | PUCT Interchange filing lists + `/Documents/*.PDF` | C | Full text (OCR on scanned filings) | Absolute document links fixed 3 Oct; TX figures from OCR stay *Reported*. |
| LA | LPSC Valence portal (DocketSearch, Docket_Documents, RecentOrders) | C | Full text | Ligature-corrupted text is summarized, never quoted. |
| MO | PSC EFIS (case search → filing display) | C | Full text | |
| NM | PRC e360 (CaseX API) | C | **Full text — *repaired 3 Oct*** | Document list fixed (the request now matches the portal's own, with `searchTerm`, newest first, paged) and documents downloaded through the portal's anonymous per-document download ticket (`casex/cms/downloadToken` → `previewDocument`), exactly as a visitor's browser does. Verified on 25-00079-UT, 25-00082-UT and 26-0000062 (text layers extracted). Confidentiality agreements and non-public documents skipped. NM leaves the manual queue unless health shows empty lists. |
| KS | KCC meeting minutes PDFs + kcc.ks.gov documents | C | Full text | Evergy ESAs under the LLPS tariff are never docketed — investor disclosure covers them. |
| OK | OCC Laserfiche WebLink (case documents); GRDA board agendas/minutes | C | Full text | Each WebLink hit confirmed against the PUD cause number on page 1. GRDA has no commission docket; board pages are the record. |
| AL | PSC public-access RSS (documents, hearings); docket pages | C, S | Full text | RSS returned HTTP 500 (server fault) from 2 Oct; the Sweep's web reader covers the docket pages until it recovers. |
| PA | PUC docket pages | S | Full text | Runners are refused at TLS; Claude's web reader works. |
| VA | SCC docket search (Breeze API) | M + S fallback | Full text (M) | robots.txt admits named search engines only. Cloud fallback: utility/intervenor copies, FERC/SEC attachments, search. |
| NC | NCUC (`starw1`) | M + S fallback | Full text (M) | Cloudflare challenge. Fallback: NCUC main-site PDFs (C, mirror), NCUC subscription mail (S), `site:starw1.ncuc.gov` GUID search (S). |
| SC | PSC DMS | M + S fallback | Full text (M) | `Disallow: /`. Fallback: PSC latest-publications and ORS electric pages (C, mirror). |
| IL | ICC e-Docket | M + S fallback | Full text (M) | `Disallow: /` + CAPTCHA. The CUB mirror returns 403 and was dropped; ComEd/Exelon EDGAR and IPA pages are the cloud fallback. |
| OH | PUCO DIS | M + S fallback | Full text (M) | Firewall rejects automated clients. Fallback: Ohio Consumers' Counsel filings (C, mirror). |
| WV | PSC WebDocket | M + S fallback | Full text (M) | 403 to automated clients. WebDocket's own text layer (ViewText) is the best source when reached by M. |
| NV | PUCN (`puc.nv.gov`, `pucweb1`) | M + S fallback | Metadata (no text layer on any document) | robots.txt disallows all bots. |
| FERC | see 1a | C | Full text | |

### 1d. Courts — *expanded 3 Oct*

| Source | Covers | Process | Depth | Notes |
|---|---|---|---|---|
| Supreme Court of Texas — orders and opinions by release date (`txcourts.gov/supreme/orders-opinions/<year>/…`) — *new* | Petitions granted/denied and opinions in PUC, ERCOT and utility matters | C | Full text (filtered) | The orders-list PDF for each release date is kept only if it names a utility matter (`tx_court_filter`). Three release dates a night, catching up. |
| Texas courts of appeals (3rd and 15th) — *via CourtListener* | Appeals of PUCT orders (the 15th Court of Appeals has heard state-agency appeals since 1 Sep 2024) | C | Metadata + link | `search.txcourts.gov` (TAMES: case search and released opinions) disallows crawlers in robots.txt and is not read. Their opinions arrive through CourtListener's state-court query. |
| Pennsylvania Commonwealth Court — opinions RSS — *repaired* | PUC appeals (PPL, PECO, Duquesne, FirstEnergy …) | C | Full text (filtered) | `pacourts.us/Rss/Opinions/Commonwealth/` replaces the court-opinions page, which rendered 0 links. Entries screened by caption; matching opinion PDFs fetched. |
| West Virginia Supreme Court of Appeals — current-term opinions — *new* | PSC appeals (ApCo, Mon Power, Wheeling Power) | C | Full text (filtered) | Page watcher, captions screened. |
| Virginia Supreme Court and Court of Appeals opinion lists | SCC appeals (e.g. Rider T1) | C | Full text (filtered) | Page watchers. |
| CourtListener API | State appellate courts in all tracked states (TX, PA, OH, WV, VA, NC, SC, IL, GA, AZ, LA, MO, KS, OK, NM, NV, AL) — a state-court query runs first — plus federal opinions on large-load / tariff / co-location matters | C | Metadata + link | Keyless use is rate-limited (only the first two queries run); `COURTLISTENER_TOKEN` lifts it and adds federal RECAP dockets. The token is now passed to the job (it was not before 3 Oct). |

### 1e. Local government — data-center siting, zoning and moratoria — *expanded 3 Oct*

| Government | Platform | Process | Depth |
|---|---|---|---|
| Prince William VA, Maricopa AZ, Phoenix AZ, Mesa AZ, Columbus OH, San Antonio TX, Fort Worth TX, Kansas City MO, **Washoe County NV (new)** | Legistar Web API (matters filtered on data-center terms) | C | Metadata + link |
| **Fairfax County VA** — Board of Supervisors meetings and its land-use / environmental committees | County meeting pages | C | Full text (filtered) |
| **Henrico County VA** — Board of Supervisors agendas | Agenda PDFs | C | Full text (filtered) |
| **City of Atlanta GA** — City Council and Zoning, Community Development, Utilities, Transportation committees | IQM2 meeting calendar | C | Full text (filtered) |
| **Tulsa OK** — City Council agendas, Tulsa Metropolitan Area Planning Commission (TMAPC), Board of Adjustment | City document service; tulsaplanning.org agenda pages | C | Full text (filtered) |
| **Storey County NV** (Tahoe Reno Industrial Center) — Board of County Commissioners agendas and packets | County AgendaCenter | C | Full text (filtered) |

A new agenda is fetched and kept only if its text matches `agenda_filter` (data center, hyperscale, large load,
substation, technology campus, zoning text amendment …); first sight of a list offers only its newest three
agendas. Loudoun, City of Reno and Fulton County are not collectable — see §2.

### 1f. Companies — earnings, investor materials and newsrooms

| Source | Issuers | Process | Depth | Notes |
|---|---|---|---|---|
| Events-and-presentations pages (rendered; PDF links harvested, never guessed) | AEP, Duke, Dominion, Entergy, Ameren, PPL, Pinnacle West, Xcel, Fortis (for TEP), TXNM | C | Full text | Full pass in earnings windows; quarter-over-quarter deltas against `pipeline_baselines_for_delta`. |
| Same, where the IR page refuses automated clients | Southern (Incapsula), Evergy, Exelon, OGE, Oncor (robots.txt), BHE (CAPTCHA) | C (EDGAR exhibits) + S | Full text | Decks taken from 8-K exhibits, or found by search on the permitted q4cdn PDF host. The refusing pages are never fetched. |
| EDGAR 8-K Item 2.02 / 7.01 | same + market participants | C | Full text | Earnings trigger; the deck itself comes from the IR page. |
| **Hyperscaler newsrooms** (RSS) — *new 3 Oct* | Microsoft (On the Issues; Source), Google (all posts; Sustainability), Amazon (About Amazon), Meta (Newsroom) | C | Full text (filtered) | Entries screened by title for energy/siting terms, then fetched and kept only if the article text names data centers, power, grid, nuclear, MW/GW, utilities or PPAs. Oracle's newsroom refuses automated clients (HTTP 403) — Oracle arrives through EDGAR and party watch. Meta's data-center site publishes no feed. |

### 1g. Party watch

Any filing in a watched docket **by** Microsoft, Google, Amazon/AWS, Meta, Oracle, OpenAI, CoreWeave, the Data Center
Coalition, major data-center developers, IPPs (Constellation, Vistra, NRG, Talen), industrial-customer groups or the
main intervenors is tagged by the collector (whole-word match on title, filer and the first document's cover page)
and treated as material by the Sweep (`parties` in the watchlist).

### 1h. Studies and benchmarks — *new 3 Oct*

| Source | Process | Depth | Notes |
|---|---|---|---|
| LBNL reports via DOE OSTI records API (queues / "Queued Up", data-center electricity use, load growth) | C | Full text | `emp.lbl.gov` and `eta.lbl.gov` refuse the runners (HTTP 403); OSTI hosts the same reports (e.g. *Queued Up: 2026 Edition*). Queries in `osti_queries`. |
| LBNL "Queued Up" page | S | Full text | First Sweep of each month, web reader (opens to WebFetch). |
| Grid Strategies (RSS) | C | Full text (filtered) | Load-growth, interconnection, transmission and resource-adequacy publications. |

### 1i. News and licensed mail (discovery and cross-check — never sole basis for *Verified*)

| Source | Process | Treatment |
|---|---|---|
| Utility Dive RSS | C | Keyword-filtered leads; confirmed against primary documents. |
| Canary Media RSS | C | Same. |
| RTO Insider RSS + daily mail (`today@rtoinsider.com`) | C, S | Licensed: facts cited, sentences never reproduced. RSS is cross-check only (~10 items). |
| New Project Media alerts (`alerts@newprojectmedia.com`) | S | Licensed. Load/generation projects; 16% haircut on announcement-stage MW. |
| S&P Capital IQ / RRA alerts | S | Licensed. Rate-case status, authorized ROE, transactions. |
| DCC Bi-Weekly State Regulatory Update (PDF) | S | Licensed. State regulatory events. |
| NCUC subscription mail | S | Only cloud discovery route for Duke NC. |
| Web search (Claude) | S | Leads and refutations for manual-route states; never *Verified* on a snippet. |
| Governors' newsrooms: AL, GA, IL, LA, MO, NC, NM, NV, OH, OK, PA, SC, TX, VA, WV (C); KS (S); AZ (M) | C, S, M | Executive orders and directives — no docket exists for these. Keyword-filtered. |
| Utility IRP / RFP pages: Dominion, Georgia Power, APS, Entergy RFPs, Evergy, Xcel/SPS (C); Duke Carolinas (S) | C, S | Supply additions and procurement before they reach a docket. |

### 1j. Keys and credentials (Rett adds them as repo secrets; Claude never handles them)

Keys obtained by Rett on 4 Oct 2026 for every row except PJM; each switches on as soon as it is saved as a repository
secret (GitHub → rettyoung/BODI → Settings → Secrets and variables → Actions). Health (`data/health/latest.json`)
shows each adapter's status: `no_key` / `demo_key` until its secret exists, `ok` after.

| Secret | What it switches on |
|---|---|
| `OPENSTATES_API_KEY` | State bills in all 18 jurisdictions |
| `NRC_APS_KEY` | NRC ADAMS documents for the ten named nuclear dockets |
| `COURTLISTENER_TOKEN` | Full-rate court search (all queries, federal RECAP dockets) |
| `EIA_API_KEY` | EIA-860M without the DEMO_KEY rate limit |
| `CONGRESS_API_KEY` | congress.gov without the DEMO_KEY rate limit |
| `REGULATIONS_GOV_API_KEY` — *adapter built 4 Oct* | Regulations.gov: DOE / EPA / NRC documents on the beat, and comments by watched parties in those dockets (runs on DEMO_KEY until the secret exists) |
| `ERCOT_API_SUBSCRIPTION_KEY` + `ERCOT_API_USERNAME` + `ERCOT_API_PASSWORD` | ERCOT Public API report archives (large-load data products by EMIL id). All three are needed: the API takes the subscription key plus a sign-in token made from the ERCOT account's username and password |
| `PJM_API_KEY` | PJM queue and capacity data (adapter not built) |

**Public-repo safety (4 Oct):** EIA and congress.gov take their key in the URL, so everything the collector writes —
health, state, candidates, backfill, probe output — passes through `common.scrub()`, which masks every secret value
and any `api_key=` / `token=` / `password=` parameter before it reaches the repository.

---

## 2. Refused or unavailable, and what covers them

"Refused" means the owner's robots.txt, a bot wall, a challenge or a firewall turns the collector away. None of
these is bypassed; the alternative is listed.

| Source | How it refuses (checked 2–4 Oct 2026) | Covered instead by |
|---|---|---|
| VA SCC, SC PSC, IL ICC, OH PUCO, NC NCUC, WV PSC, NV PUCN | robots.txt, CAPTCHA, Cloudflare, firewall, 403 | Manual pass (dockets + new cases) and the cloud fallbacks in §1c |
| AZ document hosts | Certificate hostname mismatch; robots.txt | Collector listings + manual pass |
| Texas courts of appeals — `search.txcourts.gov` (TAMES) | robots.txt disallows crawlers | CourtListener state-court query; Supreme Court of Texas pages |
| Ohio Supreme Court opinion list | Readable, but paging and sorting are ASP.NET postbacks (page 1 only) | CourtListener (`ohio`) |
| NYISO ICAP document library | Empty HTTP 202 (bot-management challenge) to automated clients | Manual pass (monthly extra page); NYISO's FERC filings |
| LBNL `emp.lbl.gov`, `eta.lbl.gov` | HTTP 403 to the runners | OSTI (C); "Queued Up" page via the Sweep's web reader |
| Oracle newsroom | HTTP 403 | EDGAR 8-Ks; party watch |
| Loudoun County agendas and packets | Packets on `lfportal.loudoun.gov`, whose robots.txt cannot be read (= disallow); `loudoun.granicus.com` disallows crawlers | Not covered by the cloud. Options: the manual pass, or Loudoun data-center items surfacing through Dominion filings, NPM and DCC |
| City of Reno agendas | `reno.primegov.com` disallows crawlers | Washoe County (Legistar) and Storey County (TRIC) agendas |
| Fulton County GA agendas | The agenda list is not in the page HTML (no static link to read) | Not covered; Atlanta City Council covers the city's own zoning |
| Storey County RSS links | Point at `nv-storeycounty.civicplus.com`, which disallows crawlers | The county's own AgendaCenter page on `www.storeycounty.org` |
| ERCOT MIS data-product servlets | robots.txt disallows `/misapp/` | Meeting materials + Monthly Operational Overview (C); ERCOT Public API (key) |
| PJM Inside Lines | CAPTCHA on the RSS | FERC dockets; RTO Insider mail; PJM newsroom (S) |
| IR pages: Southern, Evergy, Exelon, OGE, Oncor, BHE | Incapsula, robots.txt, CAPTCHA | EDGAR exhibits; deck PDFs on the permitted CDN (S) |
| Arizona governor | 403 to collector and web reader | Manual pass extra page; mail; ACC dockets |
| IL Citizens Utility Board (mirror) | 403 (removed from the watchlist 4 Oct) | Manual pass for ICC |
| Fairfax County Planning Commission | Publishes monthly calendars only, no per-meeting agendas | Its data-center cases reach the Board of Supervisors' land-use agenda, which is read |

---

## 3. Candidates for addition

Ranked by value to the deliverable per unit of effort. **Effort**: S = config change, M = new adapter, L = new
adapter + data model. Items added on 2–3 October (queues, capacity pages, courts, governors, local agendas, IRP/RFP
pages, DOE, NRC, hyperscaler newsrooms, LBNL / Grid Strategies, FERC Form 1 / EQR, ERCOT large-load status) have
moved to §1.

| # | Source | Why it matters | Access | Effort | Recommendation |
|---|---|---|---|---|---|
| 1 | **Agency allowlisting (VA, NC, SC, IL, OH, WV)** | Moves six states from manual to nightly full-text collection | Letters drafted in Outlook (not sent); the commissions said they cannot change their systems | S once granted | Optional: send the drafts. A grant flips that state's `route` to `collector`. |
| 2 | **Keys already wired** (Open States, NRC ADAMS, CourtListener, EIA) | Switch on built adapters | Free accounts | S | Add as repo secrets (§1j). |
| 3 | **PJM API** (queue, capacity) and **ERCOT Public API** | Queue positions by county; ERCOT data products by EMIL id | Free accounts + subscriptions | M (PJM) / S (ERCOT, built) | Create accounts; a session with push access builds the PJM adapter. |
| 4 | **CAISO and NYISO interconnection queues** | Completes queue coverage (MISO and SPP done) | Public spreadsheets | M | Add to `queues` after checking each host admits the runners. |
| 5 | **S&P RRA / Halcyon / Energy Strategies / DELTa** | Pre-structured docket tracking; the only fully cloud route into the seven blocked commissions | Licensed | S once licensed | Evaluate as a cross-check, not a replacement for primary filings. |
| 6 | **Earnings call transcripts** | Management commentary on large-load pipeline not in decks | Licensed (CapIQ) or company-posted | S–M | Use CapIQ transcripts if the licence covers it. |
| 7 | **Loudoun County** | Largest data-center market in the country | Blocked (§2) | — | Add Loudoun's Board packets to the manual pass, or ask the county about robots access for `lfportal`. |
| 8 | **FERC Form 1 data tables** (PUDL) | Sales by rate schedule, large-customer revenue | Public parquet | M | Only if the filing alerts in §1a prove too thin. |
| 9 | **State legislature bill trackers (direct)** | Fallback if Open States lags | Public | M | Only if Open States proves insufficient. |
| 10 | ~~Colorado and Oregon~~ | **Out of scope for now (Rett, 3 Oct 2026).** | — | — | — |
