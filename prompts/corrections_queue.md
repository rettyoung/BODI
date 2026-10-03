# Corrections queue

Read by the Sweep (Step 8.6). Each item is a finding from an earlier session. **None of it is to be
written as fact on this page's say-so**: verify each claim at source, then write the rows / overlays /
state changes it calls for, or record it REFUTED with the reason. Add the item id to
`state.corrections_done` either way. Up to 6 items per run, in order.

---

## C-01 — Texas: Governor's data-center audit directive and the ERCOT Batch Zero pause (missed)
**Partly done 2026-10-03 (degraded run, from licensed mail and a law-firm note):** E-20261003-002 (TCEQ permit
halt), -011 (community impact RFI), -012 (verification RFI), -013 (directive + delay notice), -014 (provisional
classifications), all Reported. Remaining: read the primary documents (PUCT 58317 filings in data/filings/TX/,
ERCOT notices) and, where confirmed, re-record as Verified with a `supersedes` entry for the Reported row;
overlay the stale baseline Batch Zero row (still undone). Do not create duplicates of the rows above.
Claims to verify:
- 2026-08-03: Gov. Abbott directed the PUCT and ERCOT to verify and audit data centers in the large-load
  interconnection process. (Venue Executive, Instrument Directive, Jurisdiction TX; rows for ERCOT and for
  the tracked TX utilities only if the directive names them.) Primary source: gov.texas.gov press release or
  the letter itself; Holland & Knight and Baker Botts client alerts are secondary (Reported).
- 2026-08-10: ERCOT filed a good-cause exception in **PUCT Project 58317**, pausing Batch Zero classification
  and studies; no data center or crypto load energized until verification completes. PUCT considered it at
  the 2026-08-20 open meeting. The collector now watches 58317 — read the filing and any PUCT order.
- 2026-09-03 conditional Batch Zero classifications to TDSPs; 2026-09-09 Batch Zero Verification RFI;
  2026-09-14 Community Impact RFI (computational loads ≥25 MW not yet energized), **responses due
  2026-10-12 17:00 CT**. Source: ERCOT market notices (collector watch page `ercot_notices`) or ERCOT news.
- Reported 2026-09-23 (Sidley headline): the governor's environmental-permitting freeze extends the pause to
  all Texas data centers pending a statewide audit. Verify at source before writing; Reported at best otherwise.
Then: overlay the baseline Batch Zero event (search the store for "Batch Zero"; it shows "Effective
2026-07-11" with next milestone "Batch 1 applications open 2027-06-30") — Status and Next Milestone /
Next Date updated to the verified current state. Add 2026-10-12 to near_term_milestones if verified.

## C-02 — Arizona: Microsoft's closing brief in the APS rate case (missed)
- ACC image **E000054018**, docket **E-01345A-25-0105**, docketed **2026-08-27**, Microsoft's Closing Brief
  (50 pp.; exhibits MSFT-6, -7, -9, -16). The collector's Arizona adapter now lists this docket's filings;
  find the item and its text in data/filings/AZ/. If the PDF did not extract, WebFetch
  https://images.edocket.azcc.gov/docketpdf/E000054018.pdf; if that is refused, add it to manual_queue
  requests and leave this item open.
- What to capture (verify each point in the brief): AG-XHLF rider expanding AG-X (capped at 200 MW) to all
  uncommitted large load, with third-party generation service providers and WRAP resource adequacy;
  tri-party PPAs under XHLF revisions; opposition to the formula rate (FRAM) or a 3–4%/inflation cap; opposition
  to "class pays for growth" allocation and annual cost-of-service reallocation; Load Commitment Agreement
  terms (minimum demand at 80% of full buildout from day one); CIAC/AIAC for generation only at customer
  election; large-load queue reform; Fair Value Return increment to zero; AED-4CP allocation.
  Record also, if confirmed in the record (MSFT-15): APS has not committed to serve any new large load since
  2024-01-01. Subject Large Load Customer Terms / Rates & Cost Allocation; Venue State Commission; Instrument
  Application / Petition (a brief advocates — it creates nothing; use the closest vocabulary entry and say
  "closing brief" in Document); Utility APS; levers per content.
- KJZZ 2026-09-02: Microsoft opposes APS's proposed ~45% data-center rate increase; APS reports ~4,000 MW
  committed to data centers and a 9,100+ MW peak in early August 2026. Reported unless found in the record.

## C-03 — Arizona XHLF eligibility (closes a REMAINING_GAP)
- MSFT-9 (in the brief above) and the tariff itself (A.C.C. No. 6067 Rev. 3, effective 2024-03-08, Decision
  79293) state XHLF eligibility: ≥5,000 kW monthly maximum demand and ≥92% load factor in 9 of the prior 12
  months; 15,000 kW for the economic-development/sustainability features; caps of 50 MW per customer per year
  and 500 MW aggregate. Verify, then update the APS entry in tariff_terms.json (threshold, source URL,
  confidence) and remove the Arizona XHLF item from REMAINING_GAPS. Exhibit APS-54 is no longer needed.

## C-04 — Louisiana U-37882 milestone
- One earlier session read the LPSC order as decided at the 2026-04-15 B&E session (order issued 2026-05-14);
  another established that the LPSC took original jurisdiction on 2026-05-14 and set a **2026-12-16**
  certification vote. Read the docket's newest orders and notices (collector `la_lpsc`) and keep or correct
  the 2026-12-16 milestone accordingly. Applicant reported as Evest LLC, Richland Parish, adjacent to the
  Laidley facility (U-37425); filed 2026-03-25 under the LPSC "Lightning Directive" of 2025-12-17.

## C-05 — Store housekeeping (no web reads needed)
- state.baseline.flags.superseded says 1; the store has 3 superseded rows across 2 events (E-20260918-035
  ×2, E-20260918-110). Recompute flags from the data (Step 9.3 does this every run).
- backfill_state.json still says "Phases 2 and 3 pending". Replace its `_doc` and phase statuses with the
  truth: Phase 1 done 2026-09-18; Phases 2–3 done as a single pass 2026-09-18 with a gap-closing second pass
  for VA, AZ, NM, SC, GRDA, KS and WV only; TX, ERCOT and the remaining states had one pass; docket activity
  was not enumerated filing-by-filing anywhere (the cause of C-01 and C-02). Note that the v3 collector
  backfill (data/backfill/) and the manual pass now close that gap, and point to this queue.
- seen_index.json entries E-126..E-161 are out of date order — harmless; leave them.

## C-06 — Texas text quality
- REMAINING_GAPS says all PUCT figures are capped at Reported because the documents are OCR-only. A later
  session found PUCT filings carry a clean text layer except the letterhead seal; the real problems were
  HTTP 402s and ZIP-wrapped spreadsheets, which the collector handles. Confirm from three recent TX
  documents' quality flags in data/filings/TX/, then replace that REMAINING_GAPS line with the confirmed
  finding.

## C-07 — Docket-activity backfill (ongoing until empty)
- data/backfill/<date>.jsonl holds full docket activity from 2025-11-07 for the collector states (one-off pull).
- data/backfill/baseline_links_<date>.jsonl lists links that were already on watched pages (RTO notices,
  governors, agencies, IR decks, mirrors) when the collector first saw them — metadata only, keyword hits on
  the title. Triage these by title; for any that could postdate 2026-09-18 and look on-beat, WebFetch the link
  and treat it as a candidate (the ERCOT Batch Zero RFIs of 9 and 14 September are likely among them).
  Each run, after this week's candidates, take up to 10 backfill documents that pass Step 3.2 triage, newest
  first, and process them exactly like candidates (discovery-date Event IDs, as always). Track progress in
  state.backfill_cursor. Party filings and orders first. Mark C-07 done when the backfill files are exhausted.
