"""Portal discovery: open a portal the way a browser does, search one known
docket, and record the XHR/fetch calls and links the page uses.

Output feeds adapter design. Runs on demand (workflow_dispatch), never on the
nightly schedule. Robots.txt is checked before every navigation; nothing here
solves challenges or logs in.
"""
import json, os, re, sys, time
from common import Http, UA, DATA, save_json, now_utc, looks_blocked

TARGETS = [
    {"id": "ferc_docketsheet", "url": "https://elibrary.ferc.gov/eLibrary/docketsheet?docket_number=EL25-49&sub_docket=All"},
    {"id": "ferc_search", "url": "https://elibrary.ferc.gov/eLibrary/search", "search": "EL25-49", "hint": "docket"},
    {"id": "az_edocket", "url": "https://edocket.azcc.gov/", "search": "E-01345A-25-0105", "hint": "docket"},
    {"id": "nm_e360", "url": "https://e360.prc.nm.gov/", "search": "25-00079-UT", "hint": "docket|case"},
    {"id": "la_portal", "url": "https://lpscpubvalence.lpsc.louisiana.gov/portal/PSC/DocketSearch", "search": "U-37882", "hint": "docket"},
    {"id": "la_docaccess", "url": "https://lpsc.louisiana.gov/"},
    {"id": "ga_docket", "url": "https://psc.ga.gov/search/facts-docket/?docketId=56002"},
    {"id": "mo_efis", "url": "https://www.efis.psc.mo.gov/", "search": "ER-2026-0143", "hint": "case|search"},
    {"id": "al_root", "url": "https://pscpublicaccess.alabama.gov/"},
    {"id": "al_psc", "url": "https://psc.alabama.gov/"},
    {"id": "tx_interchange", "url": "https://interchange.puc.texas.gov/search/filings/?UtilityType=A&ControlNumber=58481"},
    {"id": "ks_kcc", "url": "https://kcc.ks.gov/"},
    {"id": "ok_weblink", "url": "https://public.occ.ok.gov/WebLink/"},
    {"id": "nv_dktinfo", "url": "https://pucweb1.state.nv.us/PUC2/DktInfo.aspx"},
    {"id": "grda_board", "url": "https://www.grda.com/leadership/board-meeting-agenda-minutes/"},
]


def heuristic_search(page, text, hint):
    """Fill the most plausible search box and submit. Returns a note."""
    rx = re.compile(hint, re.I)
    inputs = page.query_selector_all("input:not([type=hidden]):not([type=checkbox]):not([type=radio])")
    best = None
    for el in inputs:
        try:
            if not el.is_visible():
                continue
            attrs = " ".join(filter(None, [el.get_attribute(a) for a in ("placeholder", "aria-label", "name", "id", "title")]))
            if rx.search(attrs):
                best = el
                break
            if best is None:
                best = el
        except Exception:
            continue
    if not best:
        return "no input found"
    best.fill(text)
    best.press("Enter")
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        pass
    page.wait_for_timeout(4000)
    return "filled " + (best.get_attribute("placeholder") or best.get_attribute("name") or best.get_attribute("id") or "?")


def main(only=None):
    from playwright.sync_api import sync_playwright
    http = Http(delay=3)
    out_dir = os.path.join(DATA, "discovery")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for t in TARGETS:
            if only and t["id"] not in only:
                continue
            rec = {"id": t["id"], "url": t["url"], "at": now_utc()}
            if not http.allowed(t["url"]):
                hs = http._host(t["url"])
                rec.update(result="robots_disallow", note=hs.robots_note or str(hs.robots_status))
                save_json(os.path.join(out_dir, t["id"] + ".json"), rec)
                print(t["id"], "robots_disallow", flush=True)
                continue
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            calls = []

            def on_resp(resp, calls=calls):
                rt = resp.request.resource_type
                if rt not in ("xhr", "fetch"):
                    return
                u = resp.url
                if any(x in u for x in ("google-analytics", "doubleclick", "googletagmanager", "ddog", "demdex",
                                        "smetrics", "cdn-cgi", "weglot", "youtube", "recaptcha")):
                    return
                body = ""
                try:
                    ct = resp.headers.get("content-type", "")
                    if "json" in ct or "text" in ct or "xml" in ct:
                        body = resp.text()[:4000]
                except Exception:
                    pass
                calls.append({"method": resp.request.method, "url": u[:500], "status": resp.status,
                              "ctype": resp.headers.get("content-type", "")[:80],
                              "req_headers": {k: v for k, v in resp.request.headers.items()
                                              if k.lower() in ("content-type", "accept", "x-requested-with", "authorization")},
                              "post_data": (resp.request.post_data or "")[:3000], "body": body})
            page.on("response", on_resp)
            try:
                resp = page.goto(t["url"], wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(2500)
                rec["status"] = resp.status if resp else None
                if t.get("search"):
                    rec["search_note"] = heuristic_search(page, t["search"], t.get("hint", "search"))
                txt = page.inner_text("body")[:200000]
                rec["blocked"] = looks_blocked(txt)
                rec["final_url"] = page.url
                rec["title"] = page.title()
                rec["text_excerpt"] = re.sub(r"\s+", " ", txt)[:3000]
                links = page.eval_on_selector_all("a[href]", "els => els.map(e => [e.href, (e.innerText||'').trim().slice(0,120)])")
                rec["links"] = links[:400]
                rec["result"] = "blocked" if rec["blocked"] else "ok"
            except Exception as e:
                rec.update(result="error", error=repr(e)[:400])
            rec["xhr"] = calls[:80]
            ctx.close()
            save_json(os.path.join(out_dir, t["id"] + ".json"), rec)
            print(t["id"], rec.get("result"), rec.get("status"), len(calls), "xhr", len(rec.get("links", [])), "links", flush=True)
            time.sleep(2)
        browser.close()


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
