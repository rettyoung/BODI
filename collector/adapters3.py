"""Third-wave adapters (3 Oct 2026).

- courts_state      Supreme Court of Texas orders/opinions by release date (the courts of appeals' TAMES
                    search is closed to crawlers by robots.txt; their opinions arrive through CourtListener)
- agendas           county / city agendas outside Legistar (page lists and agenda RSS feeds)
- ercot_large_load  ERCOT large-load interconnection status: committee meeting materials, the large-load page
                    and the Board's monthly operational overview, with table extraction; plus the ERCOT
                    Public API route once its credentials exist as repo secrets
- nyiso_icap        NYISO ICAP document library (auction results, demand curves, monthly reports)
- nrc_adams         NRC ADAMS Public Search API for named dockets (restarts, uprates, SMRs); needs NRC_APS_KEY
- ferc_forms        FERC eCollection XBRL feed: Form 1 / 1-F / 3-Q filings by tracked utilities
- ferc_eqr          FERC Electric Quarterly Report contracts (Catalyst PUDL parquet): new contracts whose
                    counterparty is a watched party (hyperscalers, data-center developers)
- studies           LBNL reports via DOE OSTI (the lab's own site refuses the runners)

Every adapter follows adapters.py's Item contract and never evades a block.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import re
from html import unescape
from urllib.parse import urljoin, quote

from common import Blocked, html_text

FMT = "%Y-%m-%d"
MONTHS = {m.lower(): i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July",
                                              "August", "September", "October", "November", "December"], 1)}


def _d(s):
    if not s:
        return None
    s = str(s).strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    m = re.search(r"(\d{4})/(\d{2})/(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.search(r"([A-Za-z]+)\.?[ -](\d{1,2}),?[ -](\d{4})", s)
    if m and m.group(1).lower()[:3] in {k[:3] for k in MONTHS}:
        mo = next(v for k, v in MONTHS.items() if k[:3] == m.group(1).lower()[:3])
        return f"{m.group(3)}-{mo:02d}-{int(m.group(2)):02d}"
    return None


def _links(html, base):
    out = []
    for href, label in re.findall(r'<a[^>]+href\s*=\s*["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', html, re.S | re.I):
        out.append((urljoin(base, href.replace("&amp;", "&").strip()), unescape(re.sub(r"<[^>]+>|\s+", " ", label)).strip()))
    return out


def _since_minus(ctx, days):
    return (dt.date.fromisoformat(ctx.since) - dt.timedelta(days=days)).isoformat()


# =========================================================================== Supreme Court of Texas
TX_UTILITY_RX = (r"Public Utility Commission|PUC of Texas|Electric Reliability Council|ERCOT|Oncor|CenterPoint|"
                 r"AEP Texas|Entergy Texas|El Paso Electric|Southwestern Public Service|Texas-New Mexico Power|"
                 r"Lower Colorado River|LCRA|Luminant|Vistra|NRG|Calpine|transmission|large load|data cent")


def courts_state(ctx):
    """Supreme Court of Texas: one page per release date (www.txcourts.gov, robots-permitted), holding the
    orders list PDF and the opinions. The orders PDF is kept only if it names a utility matter (text filter);
    opinions are kept when their listing text does. search.txcourts.gov (TAMES: case search and the courts of
    appeals' released opinions) disallows crawlers in robots.txt and is not read."""
    http, items = ctx.http, []
    done = set(ctx.state.setdefault("dates_done", []))
    year = int(ctx.today[:4])
    years = [year] + ([year - 1] if ctx.today[5:7] == "01" else [])
    pages = []
    for y in years:
        idx = f"https://www.txcourts.gov/supreme/orders-opinions/{y}/"
        html = http.get(idx).text
        for u, label in _links(html, idx):
            m = re.search(rf"/orders-opinions/{y}/([a-z]+)/([a-z]+)-(\d+)-(\d{{4}})/?$", u)
            if not m or m.group(1) not in MONTHS:
                continue
            d = f"{m.group(4)}-{MONTHS[m.group(1)]:02d}-{int(m.group(3)):02d}"
            if d >= _since_minus(ctx, 10) and d not in done:
                pages.append((d, u))
    rx = re.compile(ctx.cfg.get("tx_court_filter", TX_UTILITY_RX), re.I)
    for d, u in sorted(set(pages))[:3]:            # at most three release dates a night
        html = http.get(u).text
        text = html_text(html)
        for link, label in _links(html, u):
            if re.search(r"supreme-court-of-texas-orders.*\.pdf$", link, re.I):
                items.append({"id": f"TXSC:orders:{d}", "jur": "TX", "source": "courts_state", "kind": "court",
                              "docket": None, "title": f"Supreme Court of Texas orders list {d}", "filed": d, "url": u,
                              "fetch": [{"url": link}],
                              "meta": {"court": "Supreme Court of Texas", "text_filter": ctx.cfg.get("tx_court_filter", TX_UTILITY_RX)}})
            elif re.search(r"/media/\d+/[\w-]+\.pdf$", link) and not re.search(r"budget|policy|report|request|telework|orders-", link, re.I):
                pos = html.find(link.replace("https://www.txcourts.gov", ""))
                window = html_text(html[max(0, pos - 1500): pos + 300]) if pos >= 0 else label
                if rx.search(window) or rx.search(label):
                    cn = re.search(r"\b(\d{2}-\d{4})\b", window)
                    items.append({"id": f"TXSC:op:{link}", "jur": "TX", "source": "courts_state", "kind": "court",
                                  "docket": cn.group(1) if cn else None, "title": f"Supreme Court of Texas opinion {d}: {label or window[-200:]}"[:300],
                                  "filed": d, "url": u, "fetch": [{"url": link}],
                                  "meta": {"court": "Supreme Court of Texas"}})
        done.add(d)
        ctx.record(f"txsc {d}", "ok", f"{len(text)} chars")
    ctx.state["dates_done"] = sorted(done)[-200:]
    return items


# =========================================================================== County / city agendas
AGENDA_RX = r"data ?cent|datacenter|hyperscale|server farm|data processing|large load|substation|critical facility|technology campus"


def _rss_entries(content):
    import feedparser
    f = feedparser.parse(content)
    return [(e.get("link"), re.sub(r"\s+", " ", e.get("title") or "").strip(),
             _d(e.get("published") or e.get("updated")) or (dt.datetime(*e.published_parsed[:3]).strftime(FMT) if e.get("published_parsed") else None))
            for e in f.entries]


def agendas(ctx):
    """Agenda documents from local governments that are not on the Legistar API. Each entry lists either a page
    (link pattern, optional one-hop `follow` to meeting pages) or an RSS feed. A new agenda is fetched and kept
    only if its text matches the data-center pattern (rezonings, special exceptions, moratoria, ordinances).
    First sight of a list records it and offers only its newest few links, so adding a government never floods."""
    http, items = ctx.http, []
    rx_default = ctx.cfg.get("agenda_filter", AGENDA_RX)
    for a in ctx.cfg.get("agendas", []):
        st = ctx.state.setdefault(a["id"], {})
        known = set(st.get("known", []))
        first = not st.get("known")
        try:
            if a.get("rss"):
                body = http.get(a["url"]).content
                cands = [(u, t, d) for u, t, d in _rss_entries(body) if u]
            else:
                html = ctx.render(a["url"]) if a.get("render") else http.get(a["url"]).text
                cands = [(u, t, _d(t) or _d(u)) for u, t in _links(html, a["url"])]
        except Blocked as e:
            ctx.record(a["id"], "blocked", str(e))
            continue
        except Exception as e:
            ctx.record(a["id"], "error", repr(e)[:200])
            continue
        if a.get("heading_pairs") and not a.get("rss"):
            # listing pages that name each meeting in a heading and link its agenda below (IQM2 calendar feed)
            cands = []
            for hm in re.finditer(r"<h[1-4][^>]*>(.*?)</h[1-4]>(.*?)(?=<h[1-4]|$)", html, re.S | re.I):
                head = re.sub(r"<[^>]+>|\s+", " ", hm.group(1)).strip()
                for u, t in _links(hm.group(2), a["url"]):
                    cands.append((u, f"{head} — {t}", _d(head)))
        if a.get("title_filter"):
            cands = [c for c in cands if re.search(a["title_filter"], c[1] or "", re.I)]
        horizon = (dt.date.fromisoformat(ctx.today) + dt.timedelta(days=a.get("ahead_days", 10))).isoformat()
        cands = [c for c in cands if not (c[2] and c[2] > horizon)]      # agenda not posted yet: look again later
        if any(c[2] for c in cands):
            cands.sort(key=lambda c: c[2] or "", reverse=True)
        if a.get("follow"):
            # one hop: meeting pages -> agenda documents on them (only meeting pages not seen before)
            hops = [c for c in cands if re.search(a["follow"], c[0], re.I)]
            hops = list(dict.fromkeys(hops))
            new_hops = [h for h in hops if h[0] not in known][: (2 if first else a.get("max_follow", 4))]
            docs = []
            for u, t, d in new_hops:
                try:
                    sub = http.get(u).text
                except Exception as e:
                    ctx.log(f"agendas {a['id']} follow {u}: {e!r}"[:200])
                    continue
                for su, stt in _links(sub, u):
                    if re.search(a["link"], su, re.I):
                        docs.append((su, f"{t} — {stt}".strip(" —"), d or _d(t) or _d(su)))
                known.add(u)
            if first:
                known |= {h[0] for h in hops}
            cands = docs
        else:
            cands = [c for c in cands if re.search(a.get("link", "."), c[0], re.I)]
        cands = list({c[0]: c for c in reversed(cands)}.values())[::-1]      # one entry per URL, first title wins
        new = [c for c in cands if c[0] not in known]
        if first and not a.get("follow"):
            new = new[: a.get("first_take", 3)]
        new = new[: a.get("max_new", 8)]
        for u, t, d in new:
            items.append({"id": f"AGENDA:{a['id']}:{u}", "jur": a["jur"], "source": "agendas", "kind": "agenda",
                          "docket": None, "title": f"{a['name']}: {t or u.rsplit('/', 1)[-1]}"[:300], "filed": d, "url": u,
                          "fetch": [{"url": u}],
                          "meta": {"government": a["name"], "text_filter": a.get("text_filter", rx_default), "list": a["url"]}})
        known |= {c[0] for c in cands}
        st["known"] = sorted(known)[-3000:]
        ctx.record(a["id"], "ok", f"{len(cands)} links, {len(new)} new{' (first sight)' if first else ''}")
    return items


# =========================================================================== ERCOT large-load status
LL_DOC_RX = (r"large.?load|\bLLI\b|LLIS|batch.?(zero|study)|interconnection.{0,40}(status|queue|update)|"
             r"grid.?analysis|operational.?overview")
LL_LINE_RX = re.compile(r"(?i)(large load|\bLLI\b|LLIS|approval to energi[sz]e|observed|energi[sz]ed|batch (zero|study)|"
                        r"\bILLE\b|data cent|crypto|load (request|interconnection)|standalone|co-?located)")
LL_NUM_RX = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?\s*(?:MW|GW)\b")
LL_METRICS = [   # (label, pattern): first capture group is the MW (or GW, scaled) figure
    ("approved_to_energize_mw", r"([\d,]+(?:\.\d+)?)\s*(MW|GW)\s*(?:that\s+)?ha(?:ve|s)\s+received\s+approval\s+to\s+energi[sz]e"),
    ("approved_to_energize_mw", r"approv(?:ed|al)\s+to\s+energi[sz]e[^\d\n]{0,40}?([\d,]+(?:\.\d+)?)\s*(MW|GW)"),
    ("observed_peak_consumption_mw", r"observed\s+a\s+non-simultaneous[^\d]{0,80}?([\d,]+(?:\.\d+)?)\s*(MW|GW)"),
    ("large_load_requests_mw", r"large\s+load[^\n]{0,80}?(?:requests?|interconnection)[^\d\n]{0,60}?([\d,]{5,}(?:\.\d+)?)\s*(MW|GW)"),
    ("large_load_requests_mw", r"([\d,]{5,}(?:\.\d+)?)\s*(MW|GW)\s+of\s+large\s+load"),
    ("operational_mw", r"(?:operational|energized)\s+large\s+loads?[^\d\n]{0,40}?([\d,]+(?:\.\d+)?)\s*(MW|GW)"),
]


def ercot_ll_table(item, docs):
    """Table extraction for ERCOT large-load status material: the rows that pair a large-load status term with a
    MW figure (PDF text layer in layout mode, or spreadsheet rows), plus labelled headline figures
    (approved to energize, observed peak consumption, total large-load requests) with the sentence they came from."""
    rows, metrics = [], {}
    for d in docs:
        text = d.get("text") or ""
        flat = re.sub(r"\s+", " ", text)
        for label, pat in LL_METRICS:
            if label in metrics:
                continue
            m = re.search(pat, flat, re.I)
            if m:
                try:
                    v = float(m.group(1).replace(",", "")) * (1000 if m.group(2).upper() == "GW" else 1)
                    metrics[label] = {"mw": v, "quote": flat[max(0, m.start() - 120): m.end() + 80].strip(), "doc": d.get("url")}
                except ValueError:
                    pass
        for ln in text.splitlines():
            s = re.sub(r"[ \t]{2,}", " | ", ln.strip())
            if 6 <= len(s) <= 300 and LL_LINE_RX.search(s) and LL_NUM_RX.search(s):
                rows.append(s)
    rows = list(dict.fromkeys(rows))
    item.setdefault("meta", {}).update(table_rows=rows[:120], table_metrics=metrics,
                                       summary="\n".join(rows[:60]), ocr=any(d.get("ocr") for d in docs))


def ercot_large_load(ctx):
    """ERCOT's large-load interconnection status as it is published: (1) Large Load Working Group, TAC, ROS and
    Board meeting pages (each lists its materials under /files/docs), (2) the large-load integration page,
    (3) the Board's Monthly Operational Overview. Matching documents are fetched and their status/MW rows
    extracted (meta.table_rows). The MIS data-product servlets are disallowed by ERCOT's robots.txt and are not
    called; the ERCOT Public API is used instead when ERCOT_API_* repo secrets exist."""
    http, items = ctx.http, []
    st = ctx.state
    seen_meet = set(st.setdefault("meetings_done", []))
    rx = re.compile(ctx.cfg.get("ercot_ll_filter", LL_DOC_RX), re.I)
    lo = _since_minus(ctx, 40)
    meetings = []
    for host in ("llwg", "tac", "ros", "board"):
        page = f"https://www.ercot.com/committees/{host}" if host != "llwg" else "https://www.ercot.com/committees/tac/llwg"
        try:
            html = http.get(page).text
        except Exception as e:
            ctx.record(f"ercot:{host}", "blocked" if isinstance(e, Blocked) else "error", repr(e)[:200])
            continue
        for u, label in _links(html, page):
            m = re.search(r"/calendar/(\d{2})(\d{2})(\d{4})-", u)
            if m:
                d = f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
                if lo <= d <= ctx.today and u not in seen_meet and not re.search(r"cancel", label, re.I):
                    meetings.append((d, u))
            elif "/files/docs/" in u and rx.search(u + " " + label):
                d = _d(re.search(r"/files/docs/(\d{4}/\d{2}/\d{2})/", u).group(1)) if re.search(r"/files/docs/(\d{4}/\d{2}/\d{2})/", u) else None
                if d and d >= lo:
                    items.append(_ll_item(u, label, d, page))
        ctx.record(f"ercot:{host}", "ok", "read")
    for d, u in sorted(set(meetings), reverse=True)[:8]:
        try:
            html = http.get(u).text
        except Exception as e:
            ctx.log(f"ercot meeting {u}: {e!r}"[:200])
            continue
        for link, label in _links(html, u):
            if "/files/docs/" in link and rx.search(link + " " + label):
                items.append(_ll_item(link, label, d, u))
        if d < ctx.today:
            seen_meet.add(u)
    st["meetings_done"] = sorted(seen_meet)[-400:]
    try:
        page = "https://www.ercot.com/services/rq/large-load-integration"
        for link, label in _links(http.get(page).text, page):
            mm = re.search(r"/files/docs/(\d{4}/\d{2}/\d{2})/", link)
            if mm and _d(mm.group(1)) >= lo:
                items.append(_ll_item(link, label, _d(mm.group(1)), page))
    except Exception as e:
        ctx.record("ercot:large-load-page", "blocked" if isinstance(e, Blocked) else "error", repr(e)[:200])
    items += _ercot_api(ctx)
    return list({it["id"]: it for it in items}.values())


def _ll_item(link, label, d, page):
    return {"id": f"ERCOTLL:{link.split('?')[0]}", "jur": "TX", "source": "ercot_large_load", "kind": "report",
            "docket": None, "title": f"ERCOT — {label or link.rsplit('/', 1)[-1]}"[:300], "filed": d, "url": link,
            "entity": "ERCOT", "fetch": [{"url": link}],
            "meta": {"rto": "ERCOT", "page": page, "postprocess": "ercot_ll_table"}}


def _ercot_api(ctx):
    """ERCOT Public API (apiexplorer.ercot.com): runs only when ERCOT_API_USERNAME / _PASSWORD /
    _SUBSCRIPTION_KEY exist as repo secrets. Finds report products whose name mentions large loads and takes
    each one's newest archive document. Credentials are read from the environment, never stored or logged."""
    user, pw, key = (os.environ.get(k) for k in ("ERCOT_API_USERNAME", "ERCOT_API_PASSWORD", "ERCOT_API_SUBSCRIPTION_KEY"))
    if not (user and pw and key):
        ctx.record("ercot:public_api", "no_key", "add ERCOT_API_USERNAME, ERCOT_API_PASSWORD, ERCOT_API_SUBSCRIPTION_KEY repo secrets to enable")
        return []
    import requests
    items = []
    try:
        cid = "fec253ea-0d06-4272-a5e6-b478baeecd70"
        tok = requests.post("https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token",
                            data={"username": user, "password": pw, "grant_type": "password", "scope": f"openid {cid} offline_access",
                                  "client_id": cid, "response_type": "id_token"}, timeout=60).json().get("id_token")
        if not tok:
            ctx.record("ercot:public_api", "error", "token request returned no id_token")
            return []
        hdr = {"Authorization": f"Bearer {tok}", "Ocp-Apim-Subscription-Key": key}
        prods = ctx.http.get("https://api.ercot.com/api/public-reports", headers=hdr).json()
        prods = prods.get("_embedded", {}).get("products", prods.get("products", [])) if isinstance(prods, dict) else prods
        hits = [p for p in prods if re.search(r"large.?load", json.dumps(p), re.I)]
        for p in hits[:4]:
            emil = p.get("emilId") or p.get("emil_id")
            arch = ctx.http.get(f"https://api.ercot.com/api/public-reports/archive/{emil}?size=3", headers=hdr).json()
            for a in (arch.get("archives") or arch.get("_embedded", {}).get("archives") or [])[:1]:
                did = a.get("docId")
                items.append({"id": f"ERCOTAPI:{emil}:{did}", "jur": "TX", "source": "ercot_large_load", "kind": "report",
                              "docket": emil, "title": f"ERCOT {p.get('name') or emil} ({a.get('postDatetime', '')[:10]})",
                              "filed": (a.get("postDatetime") or "")[:10] or None,
                              "url": f"https://www.ercot.com/mp/data-products/data-product-details?id={emil}",
                              "fetch": [], "meta": {"rto": "ERCOT", "emil": emil, "api_doc": did, "postprocess": "ercot_ll_table",
                                                     "api_download": f"https://api.ercot.com/api/public-reports/archive/{emil}?download={did}"}})
        ctx.record("ercot:public_api", "ok", f"{len(hits)} large-load products")
    except Exception as e:
        ctx.record("ercot:public_api", "error", repr(e)[:200])
    return items


# =========================================================================== NYISO ICAP document library
NYISO_FOLDERS = {"ICAP Auctions": "e5dd9226-d299-90bb-b450-163ad506338d",
                 "Announcements": "3f8f5187-bdda-fc3f-e2ab-463d750e28e9",
                 "Monthly Reports": "bf4a7458-f2c7-a0e7-9fb6-548ee52a3dca",
                 "Reference Documents": "07e17f2c-1449-05a9-bd9f-31ed7a290c3f"}


def nyiso_icap(ctx):
    """The ICAP page renders its document folders in the browser from POST /o/documentlibrary/subitems
    (observed 2026-10-03). Same call, folder by folder: newest-year subfolders, files published in the window."""
    http, items = ctx.http, []
    page = "https://www.nyiso.com/installed-capacity-market"
    html = http.get(page).text
    pm = re.search(r"(portlet_com_liferay_client_extension_web_internal_portlet_ClientExtensionEntryPortlet_\w+?_LXC_nyiso_document_library_INSTANCE_[A-Za-z0-9]+)", html)
    plid = (re.search(r'getPlid\s*\(\)\s*\{\s*return\s*"?(\d+)', html) or re.search(r'"plid"\s*:\s*"?(\d+)', html))
    portlet = pm.group(1) if pm else ctx.cfg.get("nyiso_portlet")
    plid = plid.group(1) if plid else str(ctx.cfg.get("nyiso_plid", "165389"))
    if not portlet:
        raise RuntimeError("NYISO document-library portlet id not found on the ICAP page")
    folders = dict(NYISO_FOLDERS, **(ctx.cfg.get("nyiso_icap_folders") or {}))

    def sub(uuid, level):
        r = http.post("https://www.nyiso.com/o/documentlibrary/subitems",
                      json={"plid": plid, "portletId": portlet, "uuid": uuid, "folderLevel": level},
                      headers={"Content-Type": "application/json", "Accept": "application/json"})
        return (r.json() or {}).get("config") or {}

    year = ctx.today[:4]
    for name, uuid in folders.items():
        stack, n = [(uuid, 2, name)], 0
        while stack and n < 40:
            u, lvl, path = stack.pop()
            n += 1
            try:
                c = sub(u, lvl)
            except Exception as e:
                ctx.record(f"nyiso:{path}", "error", repr(e)[:200])
                continue
            for f in c.get("folders") or []:
                fn = f.get("name") or f.get("description") or ""
                if re.fullmatch(r"\d{4}(-\d{4})?", fn) and fn[:4] < str(int(year) - 1):
                    continue          # year folders: this year and last only
                if (f.get("modifiedData") or f.get("date") or "9999")[:4] >= str(int(year) - 1):
                    stack.append((f["uuid"], lvl + 1, f"{path}/{fn}"))
            for f in c.get("files") or []:
                d = _d(f.get("date") or f.get("modifiedData"))
                if d and d < ctx.since:
                    continue
                url = f.get("fileUrl")
                if not url:
                    continue
                items.append({"id": f"NYISO:ICAP:{f.get('uuid')}", "jur": "FERC", "source": "nyiso_icap", "kind": "report",
                              "docket": None, "title": f"NYISO ICAP — {path} — {f.get('description') or f.get('name')}"[:300],
                              "filed": d, "url": url, "entity": "NYISO", "fetch": [{"url": url}] if (f.get("fileType") or "").lower() in ("pdf", "xlsx", "docx", "csv") else [],
                              "meta": {"rto": "NYISO", "folder": path}})
        ctx.record(f"nyiso:{name}", "ok", f"{n} folders read")
    return items


# =========================================================================== NRC ADAMS (keyed)
def nrc_adams(ctx):
    """ADAMS Public Search API (adams-api.nrc.gov, launched Dec 2025). Needs a free subscription key from
    adams-api-developer.nrc.gov stored as the repo secret NRC_APS_KEY. Documents added to the named dockets in
    the window. Without the key, NRC news (RSS) and NRC Federal Register notices still cover the beat."""
    key = os.environ.get("NRC_APS_KEY")
    if not key:
        ctx.record("nrc_adams", "no_key", "add repo secret NRC_APS_KEY (free: adams-api-developer.nrc.gov) to enable")
        return []
    http, items = ctx.http, []
    hdr = {"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/json", "Accept": "application/json"}
    for dk, label in (ctx.cfg.get("nrc_dockets") or {}).items():
        body = {"q": "", "filters": [{"field": "DocketNumber", "value": str(dk), "operator": "starts"},
                                     {"field": "DateAddedTimestamp", "value": f"(DateAddedTimestamp ge '{ctx.since}')"}],
                "anyFilters": [], "mainLibFilter": True, "legacyLibFilter": False,
                "sort": "DateAddedTimestamp", "sortDirection": 1, "skip": 0}
        try:
            j = http.post("https://adams-api.nrc.gov/aps/api/search", json=body, headers=hdr).json()
        except Blocked as e:
            ctx.record(f"nrc:{dk}", "blocked", str(e))
            continue
        except Exception as e:
            ctx.record(f"nrc:{dk}", "error", repr(e)[:200])
            continue
        results = j.get("results") or j.get("value") or j.get("documents") or []
        for r in results[:60]:
            doc = r.get("document") or r
            acc = doc.get("AccessionNumber")
            if not acc:
                continue
            d = _d(doc.get("DateAdded") or doc.get("DocumentDate"))
            items.append({"id": f"NRC:{acc}", "jur": "US-Federal", "source": "nrc_adams", "kind": "filing",
                          "docket": str(dk), "title": f"{label}: {doc.get('DocumentTitle')} [{doc.get('DocumentType') or ''}]"[:300],
                          "filed": d, "entity": doc.get("AuthorAffiliation") or doc.get("AuthorName"),
                          "url": doc.get("Url") or f"https://adams.nrc.gov/wba/search?q={acc}",
                          "fetch": [{"url": doc["Url"]}] if doc.get("Url") else [],
                          "meta": {"project": label, "accession": acc, "document_date": doc.get("DocumentDate")}})
        ctx.record(f"nrc:{dk}", "ok", f"{len(results)} documents")
    return items


# =========================================================================== FERC Form 1 / 3-Q (eCollection)
def _norm_co(n):
    n = re.sub(r"&amp;", "&", (n or "").lower())
    n = re.sub(r"[.,']", "", n)
    n = re.sub(r"\b(inc|llc|co|corp|corporation|company|the|lp|l p)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def ferc_forms(ctx):
    """FERC eCollection 'Most Recent XBRL Filings' feed (keyless; ~650 newest filings): Form 1, 3-Q and 714
    filings by the tracked utilities' operating companies. Each item carries the filing's HTML rendering link;
    the documents are large and are read by the Sweep only when a filing matters (e.g. a new Form 1)."""
    http = ctx.http
    xml = http.get("https://ecollection.ferc.gov/api/rssfeed", timeout=120).text
    names = set()
    for e in (ctx.cfg.get("entities") or {}).values():
        names |= {_norm_co(a) for a in e.get("aliases", [])}
    names |= {_norm_co(n) for n in (ctx.cfg.get("ferc_form_filers") or [])}
    names.discard("")
    want = re.compile(ctx.cfg.get("ferc_forms_rx", r"^Form (1|1-?F|3-?Q|714)$"), re.I)
    items, n_all = [], 0
    for blk in re.findall(r"<item>(.*?)</item>", xml, re.S):
        n_all += 1
        g = lambda tag: (re.search(rf"<(?:ferc:)?{tag}>(.*?)</(?:ferc:)?{tag}>", blk, re.S) or [None, ""])[1].strip()
        form, filer = g("FormName"), re.sub(r"&amp;", "&", g("title"))
        if not want.search(form) or _norm_co(filer) not in names:
            continue
        sub = _d(g("SubmittedOn")) or _d(g("a10:updated"))
        if sub and sub < ctx.since:
            continue
        html_url = (re.search(r'type="HTML_RENDERING" url="([^"]+)"', blk) or [None, None])[1]
        fid = g("FilingID")
        items.append({"id": f"FERCFORM:{fid or g('guid')}", "jur": "FERC", "source": "ferc_forms", "kind": "disclosure",
                      "docket": None, "title": f"{filer} — FERC {form} {g('Year')} {g('Period')} ({g('Status')})",
                      "filed": sub, "url": (html_url or "https://ecollection.ferc.gov/").replace("&amp;", "&"), "entity": filer,
                      "fetch": [], "meta": {"form": form, "year": g("Year"), "period": g("Period"), "cid": g("CID"), "filing_id": fid}})
    ctx.record("ecollection", "ok", f"{n_all} filings in feed, {len(items)} tracked Form 1/3-Q/714")
    return items


# =========================================================================== FERC EQR (PUDL parquet)
def ferc_eqr(ctx):
    """FERC Electric Quarterly Report contracts, as published by Catalyst Cooperative's PUDL in public S3
    (keyless). When a new quarter partition appears, read it and report contracts whose seller or customer is a
    watched party (hyperscalers, data-center developers, IPPs) or whose seller is a tracked utility selling to
    one. First sight records the latest quarter as baseline and still reports it."""
    http, items = ctx.http, []
    base = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop"
    prefix = ctx.cfg.get("eqr_prefix", "ferceqr/core_ferceqr__contracts/")
    keys, token = [], None
    while True:
        url = f"{base}?list-type=2&prefix={quote(prefix)}" + (f"&continuation-token={quote(token)}" if token else "")
        x = http.get(url).text
        keys += [(k, int(s)) for k, s in re.findall(r"<Key>([^<]+\.parquet)</Key>.*?<Size>(\d+)</Size>", x, re.S)]
        nt = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", x)
        if not nt:
            break
        token = nt.group(1)
    if not keys:
        ctx.record("pudl_eqr", "error", "no parquet partitions listed")
        return []

    def qkey(k):
        m = re.search(r"(\d{4})[^\d]?q(\d)", k, re.I)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    quarters = {}
    for k, s in keys:
        quarters.setdefault(qkey(k), []).append((k, s))
    latest = max(quarters)
    done = set(ctx.state.setdefault("quarters_done", []))
    qs = f"{latest[0]}Q{latest[1]}"
    if qs in done:
        ctx.record("pudl_eqr", "ok", f"no new quarter (latest {qs})")
        return []
    parts = quarters[latest]
    total = sum(s for _, s in parts)
    if total > int(ctx.cfg.get("eqr_max_bytes", 400_000_000)):
        ctx.record("pudl_eqr", "error", f"{qs} partition too large to read here ({total/1e6:.0f} MB)")
        return []
    import pyarrow.parquet as pq
    parties = [p.lower() for p in ctx.cfg.get("eqr_counterparties", [])]   # hyperscalers and data-center developers only
    prx = re.compile(r"\b(" + "|".join(re.escape(p) for p in parties if len(p) > 2) + r")\b", re.I)

    def read(q):
        rows, cols = [], []
        for k, _ in quarters.get(q, []):
            t = pq.read_table(io.BytesIO(http.get(f"{base}/{k}", timeout=600).content))
            cols = t.column_names
            pick = lambda *c: next((x for x in c if x in cols), None)
            cust, sell = pick("customer_company_name", "customer_name"), pick("seller_company_name", "seller_name", "company_name")
            if not cust or not sell:
                raise RuntimeError(f"unexpected EQR columns {cols[:25]}")
            for row in t.to_pylist():
                if prx.search(f"{row.get(cust) or ''} | {row.get(sell) or ''}"):
                    rows.append(row)
        return rows, cols

    def g(r, *ks):
        return next((r.get(k) for k in ks if r.get(k) not in (None, "")), "")

    def key(r):   # one contract = seller, customer and the contract's own id / execution date
        return (str(g(r, "seller_company_name", "seller_name")).lower(), str(g(r, "customer_company_name", "customer_name")).lower(),
                str(g(r, "contract_unique_id", "contract_affiliate", "contract_execution_date", "begin_date")))

    def fmt(r):
        return (f"{g(r, 'seller_company_name', 'seller_name')} -> {g(r, 'customer_company_name', 'customer_name')} | "
                f"{g(r, 'product_name', 'product_type_name')} | {str(g(r, 'rate_description', 'rate'))[:160]} | "
                f"executed {str(g(r, 'contract_execution_date'))[:10]} | term {str(g(r, 'begin_date', 'commencement_date_of_contract_term'))[:10]} "
                f"to {str(g(r, 'end_date', 'contract_termination_date'))[:10]} | {g(r, 'point_of_delivery_balancing_authority', 'point_of_delivery_specific_location')}")
    cur, cols = read(latest)
    prev_q = max((q for q in quarters if q < latest), default=None)
    prev, _ = read(prev_q) if prev_q else ([], [])
    old = {key(r) for r in prev}
    new_rows = [r for r in cur if key(r) not in old]
    by_cust = {}
    for r in cur:
        c = str(g(r, "customer_company_name", "customer_name")).strip() or "?"
        by_cust.setdefault(c, set()).add(key(r))
    lines_new = list(dict.fromkeys(fmt(r) for r in new_rows))
    done.add(qs)
    ctx.state["quarters_done"] = sorted(done)
    ctx.record("pudl_eqr", "ok", f"{qs}: {len(lines_new)} new contract lines with watched counterparties vs {prev_q}; "
                                 f"{sum(len(v) for v in by_cust.values())} active ({total/1e6:.0f} MB read)")
    if not lines_new:
        return []
    active = "\n".join(f"{c}: {len(v)} contracts" for c, v in sorted(by_cust.items(), key=lambda x: -len(x[1]))[:30])
    pq_label = f"{prev_q[0]}Q{prev_q[1]}" if prev_q else "none"
    return [{"id": f"EQR:{qs}", "jur": "FERC", "source": "ferc_eqr", "kind": "disclosure", "docket": None,
             "title": f"FERC EQR {qs}: {len(lines_new)} new contract lines with hyperscalers or data-center developers (vs {pq_label})",
             "filed": ctx.today, "url": "https://www.ferc.gov/power-sales-and-markets/electric-quarterly-reports-eqr", "fetch": [],
             "meta": {"summary": "NEW THIS QUARTER:\n" + "\n".join(lines_new[:300]) + "\n\nACTIVE CONTRACTS BY CUSTOMER:\n" + active,
                      "quarter": qs, "previous_quarter": pq_label,
                      "source_data": "Catalyst Cooperative PUDL build of FERC EQR (core_ferceqr__contracts)", "columns": cols[:40]}}]


# =========================================================================== studies (LBNL via OSTI)
def studies(ctx):
    """LBNL reports (queues, data-center electricity use, load growth) through DOE's OSTI records API.
    emp.lbl.gov / eta.lbl.gov refuse the runners (HTTP 403); OSTI hosts the same reports."""
    http, items = ctx.http, []
    for q in ctx.cfg.get("osti_queries", []):
        url = (f"https://www.osti.gov/api/v1/records?research_org={quote(q.get('org', 'LBNL'))}&q={quote(q['q'])}"
               f"&publication_date_start={dt.date.fromisoformat(_since_minus(ctx, 30)).strftime('%m/%d/%Y')}&sort=publication_date%20desc&rows=20")
        try:
            recs = http.get(url, headers={"Accept": "application/json"}).json()
        except Exception as e:
            ctx.record(f"osti:{q['q'][:30]}", "blocked" if isinstance(e, Blocked) else "error", repr(e)[:200])
            continue
        for r in recs if isinstance(recs, list) else []:
            links = {l.get("rel"): l.get("href") for l in r.get("links", [])}
            full = links.get("fulltext") or links.get("citation")
            items.append({"id": f"OSTI:{r.get('osti_id')}", "jur": "US-Federal", "source": "studies", "kind": "report",
                          "docket": r.get("report_number"), "title": f"{(r.get('research_orgs') or ['LBNL'])[0]}: {r.get('title')}"[:300],
                          "filed": _d(r.get("publication_date")), "url": links.get("citation") or full,
                          "entity": ", ".join((r.get("research_orgs") or [])[:2]),
                          "fetch": [{"url": full}] if full else [],
                          "meta": {"authors": (r.get("authors") or [])[:6], "query": q["q"], "doi": r.get("doi")}})
        ctx.record(f"osti:{q['q'][:30]}", "ok", f"{len(recs) if isinstance(recs, list) else 0} records")
    return items


POSTPROCESS = {"ercot_ll_table": ercot_ll_table}

ADAPTERS3 = {
    "courts_state": courts_state, "agendas": agendas, "ercot_large_load": ercot_large_load, "nyiso_icap": nyiso_icap,
    "nrc_adams": nrc_adams, "ferc_forms": ferc_forms, "ferc_eqr": ferc_eqr, "studies": studies,
}
