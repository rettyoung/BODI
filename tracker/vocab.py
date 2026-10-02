"""Controlled vocabulary for the Grid Docket row store (schema 3.5).

A value outside these lists is a drifted value. The builders refuse to ship a
workbook whose totals do not reconcile to the row count, and say why.
"""
COLUMNS = [
    "Date", "Event ID", "Utility", "Jurisdiction", "Subject", "Venue", "Instrument",
    "Document", "Headline", "Takeaway", "Status", "Next Milestone", "Next Date",
    "Materiality", "Confidence", "Appeal", "Superseded",
    "Upfront Costs", "Rates", "Term", "Speed", "Curtailment", "Deliverability",
    "Supply/Demand", "Market Participation", "Source URL",
]
LEVERS = COLUMNS[17:25]

SUBJECTS = [
    "Large Load Customer Terms", "Generation Supply", "Rates & Cost Allocation", "Law & Governance",
    "Interconnection Queue", "Commercial Activity", "Transmission & Delivery",
    "Self-Supply & Colocation", "Market Structure", "Technology",
]
VENUES = [
    "State Commission", "Utility", "Legislature", "Market Operator", "Court",
    "Other State/Federal Agency", "FERC", "Executive", "Company / Industry Group", "Misc",
]
INSTRUMENTS = [
    "Statute", "Rule", "Directive", "Final Order", "Procedural Order", "Tariff", "Contract",
    "Settlement / Stipulation", "Application / Petition", "Auction Result", "Study / Report", "Disclosure",
]
MATERIALITY = ["High / near-term", "Medium / long-term"]
CONFIDENCE = ["Verified", "Reported", "Unverified"]
YESNO = ["Yes", "No"]

# The 18 baseline jurisdictions, plus the values the v3 schema adds for items that
# have no state or FERC home (resolves the open decision on federal legislation).
JURISDICTIONS = [
    "FERC", "AL", "AZ", "GA", "IL", "KS", "LA", "MO", "NC", "NM", "NV", "OH", "OK",
    "PA", "SC", "TX", "VA", "WV",
    "US-Federal",   # Congress, White House, DOE/EPA/NERC actions not docketed at FERC, federal courts
]
