"""Source adapters. Each adapter is a function(ctx) -> list[Item].

An Item is a dict with:
  id        stable native identifier (dedupe key), e.g. "FERC:20261001-5390"
  jur       jurisdiction code (watchlist vocabulary)
  source    adapter id
  docket    docket / control / case number or None
  title     description as published
  filed     YYYY-MM-DD or None
  url       human-readable landing URL (cited in the tracker)
  fetch     list of document URLs to download and extract (optional)
  entity    filer / company as published (optional)
  kind      filing | order | notice | disclosure | news | agenda | minutes | deck | rule | keyword_hit
  meta      dict of extra fields (optional)

ctx provides: http (common.Http), cfg (watchlist), since (YYYY-MM-DD), today,
state (per-source dict), browser() (lazy Playwright), log(msg).
Adapters NEVER evade a block: a common.Blocked propagates and is recorded.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from urllib.parse import urljoin, quote

from common import Blocked, html_text

FMT = "%Y-%m-%d"


def _d(s):
    """Normalise many date shapes to YYYY-MM-DD (or None)."""
    if not s:
        return None
    s = str(s).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.match(r"/Date\((\d+)\)/", s)
    if m:
        return dt.datetime.utcfromtimestamp(int(m.group(1)) / 1000).strftime(FMT)
    for f in ("%B %d, %Y", "%b %d, %Y", "%A, %B %d, %Y", "%d %B %Y"):
        try:
            return dt.datetime.strptime(s, f).strftime(FMT)
        except ValueError:
            pass
    return None


def _after(d, since):
    return d is None or d >= since


# =========================================================================== FERC
FERC_API = "https://elibrary.ferc.gov/eLibraryWebAPI/api/"


def ferc(ctx):
    """Watched dockets via the eLibrary search API (filings with file IDs), plus
    a keyword search across all dockets for new large-load matters."""
    http, items, since = ctx.http, [], ctx.since
    end = ctx.today

    def search(docket=None, text="*"):
        body = {"searchText": text, "searchFullText": True, "searchDescription": True,
                "dateSearches": [{"dateType": "filed_date", "startDate": since, "endDate": end}],
                "availability": None, "affiliations": [], "categories": [], "libraries": [],
                "accessionNumber": None, "eFiling": False,
                "docketSearches": [{"docketNumber": docket, "subDocketNumbers": []}] if docket else [],
                "resultsPerPage": 100, "curPage": 0, "classTypes": [], "sortBy": "", "groupBy": "NONE",
                "idolResultID": "", "allDates": False}
        r = http.post(FERC_API + "Search/AdvancedSearch", json=body,
                      headers={"Content-Type": "application/json", "Accept": "application/json"})
        return r.json().get("searchHits", [])

    def to_item(h, why):
        acc = h.get("acesssionNumber") or h.get("accessionNumber")
        files = [t for t in (h.get("transmittals") or []) if (t.get("fileType") or "").upper() in ("PDF", "DOCX", "XLSX", "TXT", "HTML", "ZIP")]
        return {"id": f"FERC:{acc}", "jur": "FERC", "source": "ferc", "kind": "filing",
                "docket": ",".join(sorted({d.split("-0")[0] if re.match(r".*-\d{3}$", d) else d for d in h.get("docketNumbers", [])}))[:400],
                "title": h.get("description"), "filed": _d(h.get("filedDate")),
                "url": f"https://elibrary.ferc.gov/eLibrary/filelist?accession_num={acc}",
                "entity": "; ".join(a.get("affiliation", "") for a in (h.get("affiliations") or []) if a.get("afType") == "AUTHOR")[:300],
                "fetch": [{"ferc_file": f["fileId"], "name": f.get("fileName"), "type": f.get("fileType")} for f in files[:4]],
                "meta": {"category": h.get("category"), "class": h.get("classTypes"), "why": why,
                         "issued": _d(h.get("issuedDate"))}}

    seen = set()
    for d in ctx.cfg["dockets"].get("FERC", []):
        for h in search(docket=d):
            it = to_item(h, f"watched docket {d}")
            if it["id"] not in seen:
                seen.add(it["id"])
                items.append(it)
    for q in ['"large load"', '"data center"', '"co-location" OR "co-located load"', '"large loads"']:
        for h in search(text=q):
            it = to_item(h, f"keyword {q}")
            it["kind"] = "keyword_hit"
            if it["id"] not in seen:
                seen.add(it["id"])
                items.append(it)
    return items


def ferc_download(http, file_id):
    """eLibrary file download (route observed 2026-10-02): POST File/DownloadP8File."""
    body = {"FileType": "", "accession": "", "fileid": 0, "FileIDAll": "", "fileidLst": [str(file_id).lower()],
            "Islegacy": False}
    r = http.post(FERC_API + "File/DownloadP8File", json=body,
                  headers={"Content-Type": "application/json", "Accept": "application/octet-stream, application/pdf, */*"})
    if not r.content or (r.content[:4] != b"%PDF" and r.content[:2] != b"PK" and b"<html" in r.content[:200].lower()):
        raise RuntimeError(f"FERC DownloadP8File returned {r.headers.get('content-type')} ({len(r.content)} bytes)")
    return r


# =========================================================================== Federal Register
def federal_register(ctx):
    http, items, fr = ctx.http, [], ctx.cfg.get("federal_register", {})
    base = "https://www.federalregister.gov/api/v1/documents.json"
    for term in fr.get("terms", []):
        params = [("per_page", "100"), ("order", "newest"),
                  ("conditions[publication_date][gte]", ctx.since), ("conditions[term]", f'"{term}"')]
        params += [("conditions[agencies][]", a) for a in fr.get("agencies", [])]
        for f in ("document_number", "title", "type", "abstract", "html_url", "pdf_url", "raw_text_url",
                  "publication_date", "agencies", "docket_ids", "action", "comments_close_on", "effective_on"):
            params.append(("fields[]", f))
        r = http.get(base, params=params)
        for d in r.json().get("results", []):
            ags = [a.get("slug") or a.get("name") for a in d.get("agencies", [])]
            jur = "FERC" if any("energy-regulatory" in (a or "") for a in ags) else "US-Federal"
            items.append({"id": f"FR:{d['document_number']}", "jur": jur, "source": "federal_register",
                          "kind": "rule" if d.get("type") in ("Rule", "Proposed Rule") else "notice",
                          "docket": ",".join(d.get("docket_ids") or [])[:300], "title": d.get("title"),
                          "filed": d.get("publication_date"), "url": d.get("html_url"),
                          "entity": ", ".join(filter(None, ags)),
                          "fetch": [{"url": d["raw_text_url"]}] if d.get("raw_text_url") else [],
                          "meta": {"type": d.get("type"), "action": d.get("action"), "abstract": d.get("abstract"),
                                   "comments_close_on": d.get("comments_close_on"), "effective_on": d.get("effective_on"),
                                   "term": term}})
    return items


# =========================================================================== EDGAR
def edgar(ctx):
    http, items, ecfg = ctx.http, [], ctx.cfg["edgar"]
    st = ctx.state
    if "ciks" not in st or st.get("ciks_date", "") < ctx.today[:7]:
        tick = http.get("https://www.sec.gov/files/company_tickers.json").json()
        st["ciks"] = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in tick.values()}
        st["ciks_date"] = ctx.today[:7]
    names = {**ecfg.get("utilities", {}), **ecfg.get("market_participants", {})}
    forms = set(ecfg["forms"])
    want_items = set(ecfg.get("eight_k_items", []))
    for name, tk in names.items():
        cik = tk if str(tk).isdigit() else st["ciks"].get(str(tk).upper())
        if not cik:
            ctx.log(f"edgar: no CIK for {name} ({tk})")
            continue
        cik = str(cik).zfill(10)
        sub = http.get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
        rec = sub.get("filings", {}).get("recent", {})
        is_mp = name in ecfg.get("market_participants", {})
        for i, form in enumerate(rec.get("form", [])):
            fdate = rec["filingDate"][i]
            if fdate < ctx.since or form not in forms:
                continue
            itm = set((rec.get("items", [""] * 999)[i] or "").split(","))
            if form in ("8-K", "6-K") and want_items and not (itm & want_items) and form == "8-K":
                continue
            if is_mp and form in ("10-Q", "10-K"):
                continue  # market participants: 8-K only (earnings, deals); periodic reports are too broad
            acc = rec["accessionNumber"][i]
            nodash = acc.replace("-", "")
            idx_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{nodash}/"
            fetch = [{"url": idx_url + rec["primaryDocument"][i]}]
            try:
                idx = http.get(idx_url + "index.json").json()
                for f in idx.get("directory", {}).get("item", []):
                    n = f.get("name", "")
                    if re.search(r"(ex-?99|ex99|exhibit99|press|presentation|slides).*\.(htm|html|pdf|txt)$", n, re.I):
                        fetch.append({"url": idx_url + n})
            except Exception as e:
                ctx.log(f"edgar index {acc}: {e!r}")
            items.append({"id": f"SEC:{acc}", "jur": "CORP", "source": "edgar", "kind": "disclosure",
                          "docket": None, "title": f"{name} {form} {rec.get('primaryDocDescription', [''] * 999)[i] or ''} items {','.join(sorted(itm - {''}))}".strip(),
                          "filed": fdate, "url": idx_url, "entity": name, "fetch": fetch[:5],
                          "meta": {"form": form, "items": sorted(itm - {""}), "cik": cik, "market_participant": is_mp}})
    # full-text search across all filers for the beat
    for q in ecfg.get("full_text_queries", []):
        try:
            r = http.get("https://efts.sec.gov/LATEST/search-index", params={"q": q, "dateRange": "custom",
                         "startdt": ctx.since, "enddt": ctx.today, "forms": "8-K,10-Q,10-K"})
            for h in r.json().get("hits", {}).get("hits", [])[:40]:
                s = h.get("_source", {})
                acc = (h.get("_id") or "").split(":")[0]
                if not acc:
                    continue
                items.append({"id": f"SEC:{acc}", "jur": "CORP", "source": "edgar_fts", "kind": "keyword_hit",
                              "docket": None, "title": f"{', '.join(s.get('display_names', [])[:2])} {s.get('form')} — full-text hit {q}",
                              "filed": s.get("file_date"), "url": f"https://www.sec.gov/Archives/edgar/data/{int((s.get('ciks') or ['0'])[0])}/{acc.replace('-', '')}/",
                              "entity": ", ".join(s.get("display_names", [])[:2]), "fetch": [],
                              "meta": {"query": q, "form": s.get("form")}})
        except Exception as e:
            ctx.log(f"edgar fts {q}: {e!r}")
    return items


# =========================================================================== Arizona
def az_acc(ctx):
    http, items = ctx.http, []
    api = "https://efiling.azcc.gov/api/edocket/"
    for d in ctx.cfg["dockets"].get("AZ", []):
        body = {"companyID": None, "docketID": None, "yearMatter": None, "docketTypeID": None, "documentID": None,
                "caseTypeID": None, "docketStatusID": None, "docketNumber": d, "searchAsString": None,
                "descriptionContains": None, "docketDateSearchFrom": None, "docketDateSearchTo": None,
                "currentPageIndex": 0, "rowsPerPage": 500, "rowsToSkip": 0}
        res = http.post(api + "searchByDocketDetailRequest", json=body).json().get("searchResult", [])
        if not res:
            ctx.log(f"az: docket {d} not found")
            continue
        did = res[0]["docketID"]
        docs = None
        for route in (f"GetDocketDocuments/{did}", f"docketDocuments/{did}", f"docket/{did}/documents"):
            try:
                r = http.get(api + route, retries=0)
                j = r.json()
                docs = j if isinstance(j, list) else j.get("documents") or j.get("docketDocuments")
                if docs:
                    ctx.state["az_docs_route"] = route.split("/")[0]
                    break
            except Blocked:
                raise
            except Exception:
                continue
        if not docs:
            j = http.get(api + f"docket/{did}").json()
            docs = j.get("documents") or j.get("docketDocuments") or []
        for doc in docs or []:
            filed = _d(doc.get("docketDate") or doc.get("filedDate") or doc.get("documentDate"))
            if not _after(filed, ctx.since):
                continue
            img = doc.get("imageNumber") or doc.get("barcode")
            items.append({"id": f"AZ:{doc.get('documentID') or img}", "jur": "AZ", "source": "az_acc", "kind": "filing",
                          "docket": d, "title": doc.get("description") or doc.get("documentDescription"),
                          "filed": filed, "url": f"https://edocket.azcc.gov/search/docket-search/item-detail/{did}",
                          "entity": doc.get("filedBy") or doc.get("companyName"),
                          "fetch": [{"url": f"https://images.edocket.azcc.gov/docketpdf/{img}.pdf"}] if img else [],
                          "meta": {"docketID": did}})
    # new AZ dockets opened in the window (electric), for discovery of new matters
    body = {"companyID": None, "docketID": None, "yearMatter": None, "docketTypeID": 1228, "documentID": None,
            "caseTypeID": None, "docketStatusID": None, "docketNumber": None, "searchAsString": None,
            "descriptionContains": None, "docketDateSearchFrom": ctx.since, "docketDateSearchTo": ctx.today,
            "currentPageIndex": 0, "rowsPerPage": 500, "rowsToSkip": 0}
    try:
        for r0 in http.post(api + "searchByDocketDetailRequest", json=body).json().get("searchResult", []):
            items.append({"id": f"AZDKT:{r0.get('docketNumber')}", "jur": "AZ", "source": "az_acc", "kind": "keyword_hit",
                          "docket": r0.get("docketNumber"), "title": r0.get("docketDescription") or r0.get("description"),
                          "filed": _d(r0.get("filedDate") or r0.get("docketDate")), "entity": r0.get("companyName"),
                          "url": f"https://edocket.azcc.gov/search/docket-search/item-detail/{r0.get('docketID')}", "fetch": [],
                          "meta": {"new_docket": True}})
    except Exception as e:
        ctx.log(f"az new-docket search: {e!r}")
    return items


# =========================================================================== Georgia
def ga_psc(ctx):
    http, items = ctx.http, []
    for d in ctx.cfg["dockets"].get("GA", []):
        r = http.get("https://psc.ga.gov/search/service-facts-docket/", params={
            "docketId": d, "sortDirection": "DESC", "sortColumn": "Filed", "searchText": "", "pageSize": 50, "pageNumber": 1})
        for doc in r.json().get("resultsItems", []):
            filed = _d(doc.get("filedDate"))
            if not _after(filed, ctx.since):
                continue
            did = doc["documentId"]
            items.append({"id": f"GA:{did}", "jur": "GA", "source": "ga_psc", "kind": "filing", "docket": d,
                          "title": (doc.get("description") or "").strip(), "filed": filed,
                          "entity": ", ".join(c.get("companyName", "") for c in doc.get("companyDetailsVm", [])),
                          "url": f"https://psc.ga.gov/search/facts-document/?documentId={did}",
                          "fetch": [{"ga_document": did}] if doc.get("hasAttachment") else []})
    return items


def ga_files(http, document_id):
    """Document page -> services.psc.ga.gov DownloadFile links."""
    html = http.get(f"https://psc.ga.gov/search/facts-document/?documentId={document_id}").text
    links = re.findall(r'https://services\.psc\.ga\.gov/api/v1/External/Public/Get/Document/DownloadFile/\d+/\d+', html)
    return list(dict.fromkeys(links))


# =========================================================================== Texas
def tx_puct(ctx):
    http, items = ctx.http, []
    base = "https://interchange.puc.texas.gov/search/filings/"
    for ctrl in ctx.cfg["dockets"].get("TX", []):
        html = http.get(base, params={"UtilityType": "A", "ControlNumber": ctrl, "ItemMatch": 0,
                                      "SortBy": "ItemNumber", "SortOrder": "Descending"}).text
        rows = re.findall(r'(<tr[^>]*>.*?</tr>)', html, re.S)
        found = 0
        for row in rows:
            m = re.search(r'search/documents/\?controlNumber=(\d+)&(?:amp;)?itemNumber=(\d+)', row)
            if not m:
                continue
            cells = [re.sub(r"\s+", " ", html_text(c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            filed = next((_d(c) for c in cells if _d(c)), None)
            if not _after(filed, ctx.since):
                continue
            found += 1
            item_no = m.group(2)
            items.append({"id": f"TX:{ctrl}-{item_no}", "jur": "TX", "source": "tx_puct", "kind": "filing", "docket": ctrl,
                          "title": " | ".join(c for c in cells if c and c != item_no)[:500], "filed": filed,
                          "url": f"https://interchange.puc.texas.gov/search/documents/?controlNumber={ctrl}&itemNumber={item_no}",
                          "fetch": [{"tx_item": [ctrl, item_no]}]})
        if not rows:
            ctx.log(f"tx: no table rows for {ctrl} (page may need JavaScript)")
    return items


def tx_files(http, ctrl, item):
    html = http.get(f"https://interchange.puc.texas.gov/search/documents/?controlNumber={ctrl}&itemNumber={item}").text
    return list(dict.fromkeys(urljoin("https://interchange.puc.texas.gov/", u) for u in
                              re.findall(r'href="(/Documents/[^"]+\.(?:PDF|pdf|ZIP|zip|DOCX|docx|XLSX|xlsx))"', html)))


# =========================================================================== Kansas
def ks_kcc(ctx):
    http, items = ctx.http, []
    html = http.get("https://www.kcc.ks.gov/minutesIndex.php").text
    for href, label in re.findall(r"<a href='([^']+minutes_(\d{8})\.pdf)'>", html):
        pass
    for href, ymd in re.findall(r"href='(/commission_meetings_files/minutes_(\d{8})\.pdf)'", html):
        filed = f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}"
        if filed < ctx.since:
            continue
        items.append({"id": f"KS:minutes:{ymd}", "jur": "KS", "source": "ks_kcc", "kind": "minutes", "docket": None,
                      "title": f"KCC Commission business meeting minutes {filed}", "filed": filed,
                      "url": "https://www.kcc.ks.gov" + href, "fetch": [{"url": "https://www.kcc.ks.gov" + href}]})
    return items


# =========================================================================== Louisiana
def la_lpsc(ctx):
    """LPSC portal: new dockets (DocketSearch, newest first), watched dockets' detail pages,
    and the recent-orders feed. Transportation (T-) matters are discarded."""
    http, items = ctx.http, []
    base = "https://lpscpubvalence.lpsc.louisiana.gov/portal/PSC/"

    def dsearch(number=""):
        return http.post(base + "DocketSearch", data={"sort": "DateFiled-desc", "page": 1, "pageSize": 100, "group": "",
                         "filter": "", "paramSet.DocketNumber": number, "paramSet.StartDate": "",
                         "paramSet.EndDate": "", "paramSet.CompanyName": ""}).json().get("Data", [])

    for dk in dsearch():
        filed = _d(dk.get("DateFiled"))
        num = dk.get("MatterNumber") or ""
        if not _after(filed, ctx.since) or not num.startswith(("U-", "R-")):
            continue
        items.append({"id": f"LADKT:{num}", "jur": "LA", "source": "la_lpsc", "kind": "keyword_hit", "docket": num,
                      "title": dk.get("Description"), "filed": filed,
                      "url": f"{base}DocketDetails?docketId={dk.get('MatterId')}", "fetch": [],
                      "meta": {"new_docket": True}})
    for num in ctx.cfg["dockets"].get("LA", []):
        hits = dsearch(num)
        if not hits:
            ctx.log(f"la: {num} not found")
            continue
        mid = hits[0]["MatterId"]
        html = ctx.render(f"{base}DocketDetails?docketId={mid}")
        for did, label in re.findall(r'DocumentDetails\?documentId=(\d+)"[^>]*>(.*?)</a>', html, re.S):
            seg = html[html.find(f"documentId={did}"):][:1200]
            filed = next((_d(x) for x in re.findall(r"\d{1,2}/\d{1,2}/\d{4}", seg)), None)
            if not _after(filed, ctx.since):
                continue
            items.append({"id": f"LA:doc:{did}", "jur": "LA", "source": "la_lpsc", "kind": "filing", "docket": num,
                          "title": re.sub(r"<[^>]+>|\s+", " ", label).strip()[:300], "filed": filed,
                          "url": f"{base}DocumentDetails?documentId={did}", "fetch": [{"la_document": did}]})
    r = http.post(base + "RecentOrders", data={"sort": "OrderDate-desc", "page": 1, "pageSize": 100, "group": "", "filter": ""})
    for o in r.json().get("Data", []):
        num = o.get("DocumentNumber") or ""
        filed = _d(o.get("OrderDate"))
        if not _after(filed, ctx.since) or num.startswith("T-"):
            continue
        items.append({"id": f"LA:order:{o.get('OrderId') or num}", "jur": "LA", "source": "la_lpsc", "kind": "order",
                      "docket": num, "title": (o.get("Description") or "") + " — " + (o.get("Synopsis") or ""),
                      "filed": filed, "url": f"{base}DocumentDetails?documentId={o.get('OrderId')}",
                      "fetch": [{"la_document": o.get("OrderId")}] if o.get("OrderId") else []})
    return items


def la_files(http, document_id):
    html = http.get(f"https://lpscpubvalence.lpsc.louisiana.gov/portal/PSC/DocumentDetails?documentId={document_id}").text
    return list(dict.fromkeys(urljoin("https://lpscpubvalence.lpsc.louisiana.gov/", u) for u in
                              re.findall(r'href="([^"]*ViewFile\?fileId=[^"]+)"', html)))


# =========================================================================== Oklahoma
def ok_occ(ctx):
    """OCC WebLink (recovered 2026-10-02): search each watched case number."""
    http, items = ctx.http, []
    base = "https://public.occ.ok.gov/WebLink/"
    hdr = {"Content-Type": "application/json; charset=UTF-8"}
    form = "ImagedCaseDocumentsfiledafter3212022"
    for case in ctx.cfg["dockets"].get("OK", []):
        q = http.post(base + "CustomSearchService.aspx/GetSearchQuery", headers=hdr, data=json.dumps({
            "repoName": "OCC", "searchFormID": form,
            "queryValues": {f"{form}_Input0": [case]}})).json().get("data")
        if not q:
            continue
        lst = http.post(base + "SearchService.aspx/GetSearchListing", headers=hdr, data=json.dumps({
            "repoName": "OCC", "searchSyn": q, "searchUuid": "", "sortColumn": "", "startIdx": 0, "endIdx": 100,
            "getNewListing": True, "sortOrder": 2, "displayInGridView": False})).json().get("data", {})
        cols = [c.get("name") for c in lst.get("columns", [])]
        for res in lst.get("results", []) or lst.get("rows", []) or []:
            rec = res if isinstance(res, dict) else dict(zip(cols, res))
            eid = rec.get("entryId") or rec.get("Id") or rec.get("id")
            name = rec.get("name") or rec.get("Name")
            filed = _d(rec.get("f_Scan Date") or rec.get("CreationDate") or rec.get("LastModified"))
            if not _after(filed, ctx.since) and filed is not None:
                continue
            items.append({"id": f"OK:{eid}", "jur": "OK", "source": "ok_occ", "kind": "filing", "docket": case,
                          "title": name, "filed": filed,
                          "url": f"{base}DocView.aspx?id={eid}&dbid=0&repo=OCC",
                          "fetch": [{"url": f"{base}ElectronicFile.aspx?docid={eid}&dbid=0&repo=OCC"}] if eid else [],
                          "meta": {"raw": {k: rec.get(k) for k in list(rec)[:12]}}})
        if not lst:
            ctx.log(f"ok: empty listing for {case}")
    return items


# =========================================================================== Alabama
def al_psc(ctx):
    http, items = ctx.http, []
    import feedparser
    for feed in ("DocumentSearchRssfeed.aspx", "HearingSearchRssFeed.aspx"):
        url = f"https://www.pscpublicaccess.alabama.gov/pscpublicaccess/RSS/PSC/{feed}"
        r = http.get(url)
        f = feedparser.parse(r.content)
        for e in f.entries:
            filed = _d(e.get("published") or e.get("updated"))
            try:
                if not filed and e.get("published_parsed"):
                    filed = dt.datetime(*e.published_parsed[:3]).strftime(FMT)
            except Exception:
                pass
            if not _after(filed, ctx.since):
                continue
            items.append({"id": f"AL:{e.get('id') or e.get('link')}", "jur": "AL", "source": "al_psc",
                          "kind": "filing" if "Document" in feed else "notice", "docket": None,
                          "title": e.get("title"), "filed": filed, "url": e.get("link"),
                          "fetch": [{"url": e.get("link")}] if e.get("link") and "ViewFile" in e.get("link", "") else [],
                          "meta": {"summary": (e.get("summary") or "")[:500]}})
    return items


# =========================================================================== New Mexico
def nm_prc(ctx):
    """e360 CaseX API (envelope observed 2026-10-02). Watched dockets plus new cases filed in the window."""
    http, items = ctx.http, []
    api = "https://e360.prc.nm.gov/core/api/apiflow/v1/prc/nm/intake/"

    def params(**kw):
        p = {"docketNumber": "", "caseType": [""], "caseCategory": [], "caseCategories": "", "other": "",
             "caseCaption": "", "status": [], "statuses": "", "partyName": "", "primaryPartyCompany": [""],
             "primaryPartyCompanies": "", "caseFiledDateFrom": "", "caseFiledDateTo": "", "confirmationId": "",
             "cancel": False, "reset": False, "submit": True, "searchTerm": ""}
        p.update(kw)
        return {"data": {}, "origin": "", "origin_key": "CaseX", "queryParams": [],
                "gridInput": {"params": {"parameters": p}, "persistPrevParams": False}, "parameters": p,
                "pageNo": 1, "pageSize": 100, "sortBy": {}}

    def cases(**kw):
        return http.post(api + "casedetails/getAll", json=params(**kw),
                         headers={"Content-Type": "application/json"}).json().get("items", [])

    def docs(case):
        env = {"data": {}, "origin": "", "origin_key": "CaseX", "queryParams": ["caseId"],
               "gridInput": {"params": {"parameters": {"caseId": case["id"]}}, "persistPrevParams": False},
               "parameters": {"caseId": case["id"]}, "pageNo": 1, "pageSize": 200, "sortBy": {}}
        try:
            return http.post(api + "casepublicdocument/getAll", json=env,
                             headers={"Content-Type": "application/json"}).json().get("items", [])
        except Exception as e:
            ctx.log(f"nm documents {case.get('casedocketnumber')}: {e!r}")
            return []

    for d in ctx.cfg["dockets"].get("NM", []):
        for c in cases(docketNumber=d)[:2]:
            n = 0
            for doc in docs(c):
                filed = _d(doc.get("filingdate") or doc.get("fileddate") or doc.get("createddate") or doc.get("documentdate"))
                if not _after(filed, ctx.since):
                    continue
                n += 1
                did = doc.get("id") or doc.get("documentid")
                items.append({"id": f"NM:{did}", "jur": "NM", "source": "nm_prc", "kind": "filing", "docket": d,
                              "title": doc.get("documenttitle") or doc.get("documentname") or doc.get("description") or doc.get("filename"),
                              "filed": filed, "entity": doc.get("filedby") or c.get("caseprimarycompany"),
                              "url": "https://e360.prc.nm.gov/portal/public/#/public/nm-prc/en/home",
                              "fetch": [], "meta": {"caseId": c["id"], "confidential": doc.get("isconfidential"),
                                                    "fields": sorted(doc.keys())[:40]}})
            ctx.log(f"nm {d}: {n} documents in window")
    for c in cases(caseFiledDateFrom=ctx.since, caseFiledDateTo=ctx.today):
        items.append({"id": f"NMDKT:{c.get('casedocketnumber')}", "jur": "NM", "source": "nm_prc", "kind": "keyword_hit",
                      "docket": c.get("casedocketnumber"), "title": c.get("casedatacaption"), "filed": _d(c.get("filingdate")),
                      "entity": c.get("caseprimarycompany"), "url": "https://e360.prc.nm.gov/portal/public/#/public/nm-prc/en/home",
                      "fetch": [], "meta": {"new_docket": True, "category": c.get("docketcategory"), "type": c.get("dockettype")}})
    return items


# =========================================================================== Missouri
def mo_efis(ctx):
    """EFIS case search (anti-forgery token read from the search page, as a browser does).
    New cases filed in the window, plus filings in watched cases."""
    http, items = ctx.http, []
    base = "https://www.efis.psc.mo.gov/"
    page = http.get(base + "Case/NewSearch").text
    m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', page)
    if not m:
        raise RuntimeError("EFIS search form token not found")

    def search(date_from):
        form = {"FromDateFiled": date_from, "ToDateFiled": "", "SubmissionNumber": "", "RelatedSubmissionNumber": "",
                "CaseMasterStatusId": "", "IncludeOnlyActiveCases": "false", "CompanyDetailId": "", "CompanyName": "",
                "IncludeInactive": "false", "IsSingleItemSearch": "false", "IsSubjectCompaniesOnly": "false",
                "IncludeOnlySessionOrders": "false", "Description": "", "IsIndividualFilingSearch": "false",
                "GridResultOptions.SelectedResultLimit": "500", "GridResultOptions.SortBy": "DateTimeFiled",
                "GridResultOptions.SortDirection": "DESC", "__RequestVerificationToken": m.group(1)}
        j = http.post(base + "Case", data=form, headers={"X-Requested-With": "XMLHttpRequest"}).json()
        html = j.get("searchGridResultContent", "")
        return re.findall(r'href="/Case/Display/(\d+)"[^>]*>\s*([A-Z]{2}-\d{4}-\d{4})', html), html

    watched = set(ctx.cfg["dockets"].get("MO", []))
    ids = ctx.state.setdefault("case_ids", {})
    new, _ = search(ctx.since)
    for cid, num in dict((n, c) for c, n in new).items():
        pass
    for cid, num in new:
        if num.startswith(("E", "EA", "EO", "ER", "ET", "EF", "EE", "EC")):
            ids.setdefault(num, cid)
            items.append({"id": f"MODKT:{num}", "jur": "MO", "source": "mo_efis", "kind": "keyword_hit", "docket": num,
                          "title": f"New Missouri PSC case {num}", "filed": None,
                          "url": f"{base}Case/Display/{cid}", "fetch": [{"url": f"{base}Case/Display/{cid}"}],
                          "meta": {"new_docket": True}})
    if watched - set(ids):
        older, _ = search("2025-01-01")
        for cid, num in older:
            ids.setdefault(num, cid)
    for num in sorted(watched):
        cid = ids.get(num)
        if not cid:
            ctx.log(f"mo: case id not resolved for {num}")
            continue
        html = http.get(f"{base}Case/Display/{cid}").text
        for fid, label in re.findall(r'href="/Case/FilingDisplay/(\d+)"[^>]*>(.*?)</a>', html, re.S):
            seg = html[html.find(f"/Case/FilingDisplay/{fid}"):][:1500]
            filed = next((_d(x) for x in re.findall(r"\d{1,2}/\d{1,2}/\d{4}", seg)), None)
            if not _after(filed, ctx.since):
                continue
            items.append({"id": f"MO:{fid}", "jur": "MO", "source": "mo_efis", "kind": "filing", "docket": num,
                          "title": re.sub(r"<[^>]+>|\s+", " ", label).strip()[:300], "filed": filed,
                          "url": f"{base}Case/FilingDisplay/{fid}", "fetch": [{"mo_filing": fid}]})
    return items


def mo_files(http, filing_id):
    html = http.get(f"https://www.efis.psc.mo.gov/Case/FilingDisplay/{filing_id}").text
    return list(dict.fromkeys(urljoin("https://www.efis.psc.mo.gov/", u) for u in
                              re.findall(r'href="([^"]*(?:Document/Display|DownloadDocument|/Document/)[^"]*)"', html)))


# =========================================================================== generic page watcher
def watch_pages(ctx):
    http, items = ctx.http, []
    for p in ctx.cfg.get("watch_pages", []):
        try:
            if p.get("render"):
                html = ctx.render(p["url"])
            else:
                html = http.get(p["url"]).text
        except Blocked as e:
            ctx.record(p["id"], "blocked", str(e))
            continue
        except Exception as e:
            ctx.record(p["id"], "error", repr(e)[:200])
            continue
        rx = re.compile(p.get("link", "."), re.I)
        links = re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', html, re.S | re.I)
        n = 0
        for href, label in links:
            u = urljoin(p["url"], href.replace("&amp;", "&"))
            text = re.sub(r"<[^>]+>|\s+", " ", label).strip()
            if not rx.search(u + " " + text) or len(text) < 3:
                continue
            n += 1
            items.append({"id": f"PAGE:{p['id']}:{u}", "jur": p.get("jur"), "source": f"page:{p['id']}", "kind": "news",
                          "docket": None, "title": text[:300], "filed": None, "url": u,
                          "fetch": [{"url": u}], "meta": {"rto": p.get("rto"), "page": p["url"], "keyword_filter": p.get("jur") not in ("OK", "KS")}})
        ctx.record(p["id"], "ok", f"{n} links")
    return items


def rss(ctx):
    import feedparser
    http, items = ctx.http, []
    for f in ctx.cfg.get("rss", []):
        try:
            feed = feedparser.parse(http.get(f["url"]).content)
        except Exception as e:
            ctx.record(f["id"], "error", repr(e)[:200])
            continue
        for e in feed.entries:
            filed = None
            if e.get("published_parsed"):
                filed = dt.datetime(*e.published_parsed[:3]).strftime(FMT)
            if not _after(filed, ctx.since):
                continue
            items.append({"id": f"RSS:{f['id']}:{e.get('id') or e.get('link')}", "jur": None, "source": f"rss:{f['id']}",
                          "kind": "news", "docket": None, "title": e.get("title"), "filed": filed, "url": e.get("link"),
                          "fetch": [], "meta": {"rto": f.get("rto"), "summary": re.sub(r"<[^>]+>", " ", e.get("summary") or "")[:800],
                                                "keyword_filter": True}})
        ctx.record(f["id"], "ok", f"{len(feed.entries)} entries")
    return items


def ir_decks(ctx):
    items = []
    for p in ctx.cfg.get("ir_pages", []):
        try:
            html = ctx.render(p["url"])
        except Blocked as e:
            ctx.record("ir:" + p["issuer"], "blocked", str(e))
            continue
        except Exception as e:
            ctx.record("ir:" + p["issuer"], "error", repr(e)[:200])
            continue
        pdfs = set()
        for href in re.findall(r'href="([^"]+\.pdf[^"]*)"', html, re.I):
            pdfs.add(urljoin(p["url"], href.replace("&amp;", "&")))
        for u in sorted(pdfs):
            items.append({"id": f"IR:{u.split('?')[0]}", "jur": "CORP", "source": "ir_decks", "kind": "deck",
                          "docket": None, "title": f"{p['issuer']} — {u.rsplit('/', 1)[-1]}", "filed": None, "url": u,
                          "entity": p["issuer"], "fetch": [{"url": u}], "meta": {"issuer": p["issuer"]}})
        ctx.record("ir:" + p["issuer"], "ok", f"{len(pdfs)} pdf links")
    return items


def mirrors(ctx):
    items = []
    for m in ctx.cfg.get("mirrors", []) or []:
        try:
            html = ctx.render(m["url"]) if m.get("render") else ctx.http.get(m["url"]).text
        except Exception as e:
            ctx.record("mirror:" + m["id"], "blocked" if isinstance(e, Blocked) else "error", repr(e)[:200])
            continue
        rx = re.compile(m.get("link", r"\.pdf"), re.I)
        n = 0
        for href, label in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
            u = urljoin(m["url"], href.replace("&amp;", "&"))
            if not rx.search(u):
                continue
            n += 1
            items.append({"id": f"MIRROR:{u}", "jur": m["jur"], "source": "mirror:" + m["id"], "kind": "filing",
                          "docket": None, "title": re.sub(r"<[^>]+>|\s+", " ", label).strip()[:300], "filed": None,
                          "url": u, "entity": m.get("owner"), "fetch": [{"url": u}],
                          "meta": {"mirror_of": m.get("mirror_of"), "keyword_filter": True}})
        ctx.record("mirror:" + m["id"], "ok", f"{n} links")
    return items


# Order matters only for budgeting: highest-value sources first.
ADAPTERS = {
    "ferc": ferc, "federal_register": federal_register, "edgar": edgar, "tx_puct": tx_puct,
    "az_acc": az_acc, "ga_psc": ga_psc, "la_lpsc": la_lpsc, "ok_occ": ok_occ, "ks_kcc": ks_kcc,
    "nm_prc": nm_prc, "mo_efis": mo_efis, "al_psc": al_psc, "watch_pages": watch_pages, "rss": rss, "ir_decks": ir_decks,
    "mirrors": mirrors,
}
