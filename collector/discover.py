"""Portal discovery: open a portal the way a browser does, search one known
docket, and record the XHR/fetch calls and links the page uses.

Output feeds adapter design. Runs on demand (workflow_dispatch), never on the
nightly schedule. Robots.txt is checked before every navigation; nothing here
solves challenges or logs in.
"""
import json, os, re, sys, time
from common import Http, UA, DATA, save_json, now_utc, looks_blocked

TARGETS = [
    {"id": "ferc_download", "url": "https://elibrary.ferc.gov/eLibrary/filelist?accession_num=20261001-5390",
     "steps": [{"click": "a[href*='download'], a[title*='Download'], a[aria-label*='ownload'], i.fa-download, .fa-file-pdf, a[href*='filedownload']"}]},
    {"id": "ferc_filedownload", "url": "https://elibrary.ferc.gov/eLibrary/filedownload?fileid=7C898DAD-BB3D-CBE0-9E07-A0FC83C00000"},
    {"id": "az_docs", "url": "https://edocket.azcc.gov/search/docket-search/item-detail/29551",
     "steps": [{"click": "text=Docket Documents"}, {"wait": 6000}]},
    {"id": "nm_advsearch", "url": "https://e360.prc.nm.gov/portal/public/#/public/nm-prc/en/CaseXscreen?screen=external-AdvancedSearch",
     "steps": [{"wait": 6000}, {"fill": ["input[name='data[docketNumber]']", "25-00079-UT"]}, {"click": "button:has-text('Search')"}, {"wait": 8000}]},
    {"id": "la_docketsearch", "url": "https://lpscpubvalence.lpsc.louisiana.gov/portal/lpsc-web-portal",
     "steps": [{"click": "text=Search for Dockets"}, {"wait": 4000}, {"fill_hint": ["docket|number", "U-37882"]}, {"press": "Enter"}, {"wait": 6000}]},
    {"id": "mo_casesearch", "url": "https://www.efis.psc.mo.gov/Case/NewSearch",
     "steps": [{"fill_hint": ["casenumber|case number|caseno|CaseNumber", "ER-2026-0143"]}, {"press": "Enter"}, {"wait": 6000}]},
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


def run_steps(page, steps):
    notes = []
    for st in steps:
        try:
            if "click" in st:
                page.locator(st["click"]).first.click(timeout=15000, force=True)
                notes.append("clicked " + st["click"][:60])
            elif "fill" in st:
                page.locator(st["fill"][0]).first.fill(st["fill"][1], timeout=15000)
                notes.append("filled " + st["fill"][0])
            elif "fill_hint" in st:
                notes.append(heuristic_fill(page, st["fill_hint"][1], st["fill_hint"][0]))
            elif "press" in st:
                page.keyboard.press(st["press"])
                notes.append("pressed " + st["press"])
            elif "wait" in st:
                page.wait_for_timeout(st["wait"])
        except Exception as e:
            notes.append("FAILED " + str(st)[:80] + ": " + repr(e)[:160])
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    return notes


def heuristic_fill(page, text, hint):
    rx = re.compile(hint, re.I)
    for el in page.query_selector_all("input:not([type=hidden]):not([type=checkbox]):not([type=radio])"):
        try:
            attrs = " ".join(filter(None, [el.get_attribute(a) for a in ("placeholder", "aria-label", "name", "id", "title")]))
            if el.is_visible() and rx.search(attrs):
                el.fill(text)
                el.focus()
                return "filled " + attrs[:80]
        except Exception:
            continue
    names = [(" ".join(filter(None, [el.get_attribute(a) for a in ("name", "id", "placeholder")])))[:60]
             for el in page.query_selector_all("input")][:30]
    return "no match; inputs=" + "; ".join(names)


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
            downloads = []
            page.on("download", lambda d, downloads=downloads: downloads.append({"url": d.url, "name": d.suggested_filename}))
            page.on("popup", lambda p2, downloads=downloads: downloads.append({"popup": p2.url}))
            try:
                resp = page.goto(t["url"], wait_until="domcontentloaded", timeout=60000)
                try:
                    page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    pass
                page.wait_for_timeout(4000)
                if t.get("steps"):
                    rec["step_notes"] = run_steps(page, t["steps"])
                if t.get("click"):
                    try:
                        page.get_by_text(t["click"], exact=False).first.click(timeout=15000)
                        page.wait_for_timeout(6000)
                        rec["click_note"] = "clicked " + t["click"]
                    except Exception as e:
                        rec["click_note"] = "click failed: " + repr(e)[:200]
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
            rec["downloads"] = downloads
            ctx.close()
            save_json(os.path.join(out_dir, t["id"] + ".json"), rec)
            print(t["id"], rec.get("result"), rec.get("status"), len(calls), "xhr", len(rec.get("links", [])), "links", flush=True)
            time.sleep(2)
        browser.close()


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
