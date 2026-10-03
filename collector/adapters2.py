"""Second-wave adapters.

- Keyed public APIs (run only when the repo secret exists): eia, congress, openstates, courtlistener
  (CourtListener also runs keyless at a lower rate).
- Interconnection queues (monthly snapshots, deltas by tracked state): queues.
- Local government agendas via the Legistar Web API: legistar.

Every adapter returns Items as described in adapters.py and never evades a block.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
from urllib.parse import quote, urljoin

from common import Blocked

TRACKED_STATES = ["AL", "AZ", "GA", "IL", "KS", "LA", "MO", "NC", "NM", "NV", "OH", "OK", "PA", "SC", "TX", "VA", "WV"]
STATE_NAMES = {"AL": "Alabama", "AZ": "Arizona", "GA": "Georgia", "IL": "Illinois", "KS": "Kansas", "LA": "Louisiana",
               "MO": "Missouri", "NC": "North Carolina", "NM": "New Mexico", "NV": "Nevada", "OH": "Ohio", "OK": "Oklahoma",
               "PA": "Pennsylvania", "SC": "South Carolina", "TX": "Texas", "VA": "Virginia", "WV": "West Virginia"}


def _d(s):
    if not s:
        return None
    s = str(s).strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return dt.datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _after(d, since):
    return d is None or d >= since


def _kw(cfg):
    return [k.lower() for k in cfg.get("keywords", [])]


def _hit(text, kws):
    t = (text or "").lower()
    return sorted({k for k in kws if k in t})


# =========================================================================== EIA (key)
def eia(ctx):
    """EIA-860M planned capacity by state and technology; reports the change since the last snapshot."""
    # Falls back to api.data.gov's public DEMO_KEY (published for anonymous use; low rate limit).
    key = os.environ.get("EIA_API_KEY") or "DEMO_KEY"
    if key == "DEMO_KEY":
        ctx.record("eia", "demo_key", "running on the public DEMO_KEY; a repo secret EIA_API_KEY lifts the rate limit")
    last_ok = ctx.state.get("last_period")
    url = ("https://api.eia.gov/v2/electricity/operating-generator-capacity/data/?frequency=monthly"
           "&data[0]=nameplate-capacity-mw&sort[0][column]=period&sort[0][direction]=desc&length=1")
    head = ctx.http.get(url + f"&api_key={key}").json().get("response", {}).get("data", [])
    if not head:
        ctx.log("eia: no data")
        return []
    period = head[0]["period"]
    if period == last_ok:
        ctx.record("eia", "ok", f"no new period (latest {period})")
        return []
    totals = {}
    for st in TRACKED_STATES:
        offset = 0
        while True:
            q = (f"https://api.eia.gov/v2/electricity/operating-generator-capacity/data/?frequency=monthly"
                 f"&data[0]=nameplate-capacity-mw&facets[stateid][]={st}&start={period}&end={period}"
                 f"&offset={offset}&length=5000&api_key={key}")
            rows = ctx.http.get(q).json().get("response", {}).get("data", [])
            for r in rows:
                status = (r.get("status") or r.get("statusDescription") or "")
                if not re.match(r"\(?[PLTUV]\)?\b|planned|regulatory|under construction|construction", status, re.I):
                    continue
                k = (st, r.get("technology") or r.get("energy_source_code") or "?")
                totals[k] = totals.get(k, 0.0) + float(r.get("nameplate-capacity-mw") or 0)
            if len(rows) < 5000:
                break
            offset += 5000
    prev = {tuple(k.split("|")): v for k, v in (ctx.state.get("planned") or {}).items()}
    ctx.state["planned"] = {"|".join(k): round(v, 1) for k, v in totals.items()}
    ctx.state["last_period"] = period
    if not prev:
        ctx.record("eia", "ok", f"baseline {period}")
        return []
    lines = []
    for k in sorted(set(totals) | set(prev)):
        d = totals.get(k, 0) - prev.get(k, 0)
        if abs(d) >= 100:
            lines.append(f"{k[0]} {k[1]}: {prev.get(k, 0):,.0f} -> {totals.get(k, 0):,.0f} MW ({d:+,.0f})")
    if not lines:
        return []
    return [{"id": f"EIA:860M:{period}", "jur": "US-Federal", "source": "eia", "kind": "disclosure", "docket": None,
             "title": f"EIA-860M {period}: planned/under-construction capacity changes ≥100 MW in tracked states",
             "filed": None, "url": "https://www.eia.gov/electricity/data/eia860m/", "fetch": [],
             "meta": {"summary": "\n".join(lines[:80]), "period": period}}]


# =========================================================================== congress.gov (key)
def congress(ctx):
    # Falls back to api.data.gov's public DEMO_KEY (published for anonymous use; low rate limit).
    key = os.environ.get("CONGRESS_API_KEY") or "DEMO_KEY"
    if key == "DEMO_KEY":
        ctx.record("congress", "demo_key", "running on the public DEMO_KEY; a repo secret CONGRESS_API_KEY lifts the rate limit")
    kws = _kw(ctx.cfg) + ["electric grid", "transmission", "permitting", "ferc", "data centers", "artificial intelligence"]
    since = f"{ctx.since}T00:00:00Z"
    items, offset = [], 0
    while offset < 1000:
        j = ctx.http.get(f"https://api.congress.gov/v3/bill?fromDateTime={since}&sort=updateDate+desc&limit=250"
                         f"&offset={offset}&format=json&api_key={key}").json()
        bills = j.get("bills", [])
        for b in bills:
            title = b.get("title") or ""
            hits = _hit(title, kws)
            if not hits:
                continue
            bid = f"{b.get('congress')}-{b.get('type')}-{b.get('number')}"
            la = b.get("latestAction") or {}
            items.append({"id": f"BILL:US:{bid}:{la.get('actionDate')}", "jur": "US-Federal", "source": "congress",
                          "kind": "legislation", "docket": f"{b.get('type')} {b.get('number')}", "title": title[:300],
                          "filed": la.get("actionDate"),
                          "url": f"https://www.congress.gov/bill/{b.get('congress')}th-congress/"
                                 f"{'house' if str(b.get('type','')).upper().startswith('H') else 'senate'}-bill/{b.get('number')}",
                          "fetch": [], "meta": {"latest_action": la.get("text"), "keywords": hits}})
        if len(bills) < 250:
            break
        offset += 250
    return items


# =========================================================================== Open States (key)
def openstates(ctx):
    key = os.environ.get("OPENSTATES_API_KEY")
    if not key:
        ctx.record("openstates", "no_key", "add repo secret OPENSTATES_API_KEY to enable")
        return []
    items = []
    queries = ctx.cfg.get("openstates_queries", ["data center", "large load"])
    for st in TRACKED_STATES:
        for q in queries:
            try:
                j = ctx.http.get(f"https://v3.openstates.org/bills?jurisdiction={quote(STATE_NAMES[st])}&q={quote(q)}"
                                 f"&updated_since={ctx.since}&sort=updated_desc&per_page=20&include=actions",
                                 headers={"X-API-KEY": key}).json()
            except Blocked:
                raise
            except Exception as e:
                ctx.log(f"openstates {st} {q}: {e!r}"[:200])
                continue
            for b in j.get("results", []):
                last = (b.get("actions") or [{}])[-1]
                items.append({"id": f"BILL:{st}:{b.get('id')}:{b.get('latest_action_date')}", "jur": st, "source": "openstates",
                              "kind": "legislation", "docket": b.get("identifier"), "title": (b.get("title") or "")[:300],
                              "filed": (b.get("latest_action_date") or "")[:10] or None,
                              "url": b.get("openstates_url"), "fetch": [],
                              "meta": {"session": b.get("session"), "latest_action": last.get("description"), "query": q}})
    return items


# =========================================================================== CourtListener (key optional)
def courtlistener(ctx):
    """Federal and state appellate opinions and RECAP dockets on large-load / tariff matters.
    Keyless use is throttled by CourtListener; with COURTLISTENER_TOKEN it runs at full rate."""
    tok = os.environ.get("COURTLISTENER_TOKEN")
    hdr = {"Authorization": f"Token {tok}"} if tok else {}
    items = []
    queries = ctx.cfg.get("court_queries", [])
    if not tok:
        queries = queries[:2]   # keyless use is rate-limited hard; a free token lifts it
    for q in queries:
        for typ in ("o", "r"):
            if typ == "r" and not tok:
                continue   # RECAP docket search needs a token
            url = (f"https://www.courtlistener.com/api/rest/v4/search/?type={typ}&order_by=dateFiled%20desc"
                   f"&filed_after={ctx.since}&q={quote(q)}")
            try:
                j = ctx.http.get(url, headers=hdr).json()
            except Blocked as e:
                if "429" in str(e):
                    ctx.record("courtlistener", "rate_limited", "add repo secret COURTLISTENER_TOKEN (free account) for full coverage")
                    return items
                raise
            except Exception as e:
                ctx.log(f"courtlistener {typ} {q[:40]}: {e!r}"[:200])
                continue
            for r in j.get("results", [])[:40]:
                cid = r.get("cluster_id") or r.get("docket_id") or r.get("id")
                abs_url = r.get("absolute_url") or ""
                items.append({"id": f"COURT:{typ}:{cid}", "jur": "US-Federal", "source": "courtlistener", "kind": "court",
                              "docket": r.get("docketNumber"), "title": (r.get("caseName") or r.get("case_name") or "")[:300],
                              "filed": (r.get("dateFiled") or "")[:10] or None,
                              "url": "https://www.courtlistener.com" + abs_url if abs_url.startswith("/") else abs_url,
                              "fetch": [], "meta": {"court": r.get("court") or r.get("court_id"), "query": q}})
    return items


# =========================================================================== Interconnection queues
def _rows_from(content, ctype, url):
    low = url.lower()
    if low.endswith(".json") or "json" in (ctype or ""):
        j = json.loads(content)
        return j if isinstance(j, list) else (j.get("data") or j.get("projects") or j.get("value") or [])
    if low.endswith(".csv") or "csv" in (ctype or "") or "csv" in low:
        txt = content.decode("utf-8-sig", errors="replace")
        lines = txt.splitlines()
        # skip preamble lines ("Last Updated On", ...): the header is the first line with >= 5 named columns
        hi = next((i for i, ln in enumerate(lines[:30]) if sum(1 for c in next(csv.reader([ln])) if c.strip()) >= 5), 0)
        return list(csv.DictReader(io.StringIO("\n".join(lines[hi:]))))
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    best = []
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        # header = first row with >= 5 non-empty string cells
        hi = next((i for i, r in enumerate(rows[:30]) if sum(isinstance(c, str) and c.strip() != "" for c in r) >= 5), None)
        if hi is None:
            continue
        hdr = [str(c).strip() if c is not None else f"col{i}" for i, c in enumerate(rows[hi])]
        data = [dict(zip(hdr, r)) for r in rows[hi + 1:] if any(c is not None for c in r)]
        if len(data) > len(best):
            best = data
    return best


def _pick(row, pats):
    for k in row:
        if any(re.search(p, str(k), re.I) for p in pats):
            v = row[k]
            if v not in (None, ""):
                return v
    return None


def queues(ctx):
    """Monthly snapshot of each RTO's public interconnection queue; emits one summary per queue with new
    projects in tracked states (>= 100 MW) and MW totals by state. First sight is a baseline."""
    items = []
    month = ctx.today[:7]
    for qd in ctx.cfg.get("queues", []):
        st = ctx.state.setdefault(qd["id"], {})
        if st.get("month") == month and not qd.get("daily"):
            continue
        try:
            r = ctx.http.get(qd["url"], timeout=180)
            rows = _rows_from(r.content, r.headers.get("content-type", ""), qd["url"])
        except Blocked as e:
            ctx.record(qd["id"], "blocked", str(e))
            continue
        except Exception as e:
            ctx.record(qd["id"], "error", repr(e)[:200])
            continue
        if not rows:
            ctx.record(qd["id"], "error", "no rows parsed")
            continue
        ids, by_state, new = set(), {}, []
        prev_ids = set(st.get("ids", []))
        for row in rows:
            status = str(_pick(row, [r"^status$", r"status"]) or "") + " " + str(_pick(row, [r"withdrawn"]) or "")
            if re.search(r"withdrawn|cancel|commercial operation|in.?service|completed|suspended", status, re.I):
                continue   # active queue only
            pid = _pick(row, qd.get("id_cols", [r"queue.?(id|number|#|pos)", r"interconnection number", r"^project.?(id|number)",
                                                r"^inr$", r"^id$", r"projectnumber"]))
            state = str(_pick(row, qd.get("state_cols", [r"^state$", r"state"])) or "").strip().upper()[:2]
            if state not in TRACKED_STATES:
                continue
            try:
                mw = float(str(_pick(row, qd.get("mw_cols", [r"summer.*mw", r"capacity.*mw", r"^mw", r"\bmw\b", r"capacity"])) or 0).replace(",", ""))
            except ValueError:
                mw = 0.0
            fuel = str(_pick(row, [r"fuel", r"type", r"technology", r"generation"]) or "")[:30]
            name = str(_pick(row, [r"project.?name", r"^name", r"facility"]) or "")[:80]
            county = str(_pick(row, [r"county"]) or "")[:30]
            key = str(pid) if pid not in (None, "") else hashlib.sha1(f"{name}{county}{mw}".encode()).hexdigest()[:12]
            ids.add(key)
            b = by_state.setdefault(state, [0, 0.0])
            b[0] += 1
            b[1] += mw
            if prev_ids and key not in prev_ids and mw >= 100:
                new.append(f"{state} {county} — {name} — {fuel} — {mw:,.0f} MW (queue id {key})")
        first = not prev_ids
        prev_tot = st.get("by_state", {})
        st.update(month=month, ids=sorted(ids), by_state={k: [v[0], round(v[1], 1)] for k, v in by_state.items()})
        ctx.record(qd["id"], "ok", f"{len(ids)} tracked-state projects{' (baseline)' if first else ''}")
        if first:
            continue
        deltas = [f"{k}: {prev_tot.get(k, [0, 0])[1]:,.0f} -> {v[1]:,.0f} MW ({v[1] - prev_tot.get(k, [0, 0])[1]:+,.0f}); "
                  f"{v[0]} projects" for k, v in sorted(by_state.items())]
        if not new and all(abs(v[1] - prev_tot.get(k, [0, 0])[1]) < 250 for k, v in by_state.items()):
            continue
        items.append({"id": f"QUEUE:{qd['id']}:{month}", "jur": qd.get("jur", "FERC"), "source": "queues", "kind": "queue_delta",
                      "docket": None, "title": f"{qd['name']} interconnection queue — {month}: {len(new)} new projects ≥100 MW in tracked states",
                      "filed": ctx.today, "url": qd.get("page") or qd["url"], "fetch": [],
                      "meta": {"rto": qd.get("rto"), "summary": "New projects:\n" + "\n".join(new[:120]) + "\n\nTotals by state:\n" + "\n".join(deltas)}})
    return items


# =========================================================================== Local government (Legistar)
def legistar(ctx):
    """County / city legislative items mentioning data centers (rezonings, special exceptions, moratoria)."""
    items = []
    rx = re.compile(ctx.cfg.get("legistar_filter", r"data ?cent|hyperscale|substation|large load|server farm"), re.I)
    since = ctx.since
    for c in ctx.cfg.get("legistar", []):
        url = (f"https://webapi.legistar.com/v1/{c['client']}/matters?$filter=MatterIntroDate ge datetime'{since}'"
               f"&$orderby=MatterIntroDate desc&$top=500")
        try:
            rows = ctx.http.get(url).json()
        except Blocked as e:
            ctx.record(c["client"], "blocked", str(e))
            continue
        except Exception as e:
            ctx.record(c["client"], "error", repr(e)[:200])
            continue
        if not isinstance(rows, list):
            ctx.record(c["client"], "error", f"unexpected response {str(rows)[:120]}")
            continue
        n = 0
        for m in rows:
            text = " ".join(str(m.get(k) or "") for k in ("MatterName", "MatterTitle", "MatterTypeName", "MatterBodyName"))
            if not rx.search(text):
                continue
            n += 1
            items.append({"id": f"LEG:{c['client']}:{m.get('MatterId')}", "jur": c["jur"], "source": "legistar", "kind": "agenda",
                          "docket": m.get("MatterFile"), "title": f"{c['name']}: {(m.get('MatterTitle') or m.get('MatterName') or '')[:260]}",
                          "filed": (m.get("MatterIntroDate") or "")[:10] or None,
                          "url": f"https://{c['client']}.legistar.com/LegislationDetail.aspx?ID={m.get('MatterId')}&GUID={m.get('MatterGuid')}",
                          "fetch": [], "meta": {"county": c["name"], "status": m.get("MatterStatusName"), "body": m.get("MatterBodyName")}})
        ctx.record(c["client"], "ok", f"{len(rows)} matters, {n} on-topic")
    return items


ADAPTERS2 = {
    "eia": eia, "congress": congress, "openstates": openstates, "courtlistener": courtlistener,
    "queues": queues, "legistar": legistar,
}
