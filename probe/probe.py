"""Reachability probe for Grid Docket collector hosts.

Runs on a GitHub Actions runner. For each target it:
  1. fetches the host's robots.txt and evaluates it for our User-Agent,
  2. skips the target if robots.txt explicitly disallows it,
  3. issues a plain GET and classifies the response (ok / block page / error),
  4. for JS-driven portals, renders the page in headless Chromium and records
     the XHR/fetch endpoints the page calls (to design adapters),
  5. extracts text from PDFs with pdftotext.

Politeness: honest User-Agent, one request every few seconds per host,
no CAPTCHA solving, no evasion of bot defenses.
"""
import json, os, re, subprocess, time, tempfile, datetime
from urllib.parse import urlparse
from urllib import robotparser
import requests

UA = "GridDocketResearchBot/0.1 (+https://github.com/rettyoung/bodi)"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")
DELAY = 3.0
BLOCK_MARKERS = [
    "request rejected", "access denied", "the requested url was rejected",
    "attention required", "captcha", "cf-chl", "incapsula", "are you a robot",
    "bot detection", "enable javascript and cookies to continue", "web page blocked",
    "not a robot", "no robots or crawlers",
]

session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept": "*/*"})
robots_cache, last_hit = {}, {}


def polite(host):
    wait = DELAY - (time.time() - last_hit.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    last_hit[host] = time.time()


def robots_for(url):
    p = urlparse(url)
    host = f"{p.scheme}://{p.netloc}"
    if host in robots_cache:
        return robots_cache[host]
    info = {"robots_url": host + "/robots.txt"}
    polite(p.netloc)
    try:
        r = session.get(info["robots_url"], timeout=30)
        info["status"] = r.status_code
        # Decode with utf-8-sig so a leading byte-order mark cannot hide the first rule.
        body = r.content.decode("utf-8-sig", errors="replace").lstrip("﻿")
        info["excerpt"] = body[:600] if r.ok else ""
        rp = robotparser.RobotFileParser()
        # RFC 9309 §2.3.1: 2xx -> parse; 4xx ("unavailable") -> no restrictions;
        # 5xx or network failure ("unreachable") -> assume complete disallow.
        if 200 <= r.status_code < 300:
            head = body[:3000].lower()
            if "<html" in head and any(m in head for m in BLOCK_MARKERS[:3]):
                rp.disallow_all = True  # firewall block page served in place of robots.txt
                info["note"] = "robots.txt returned a firewall block page; treated as disallow"
            elif "<html" in head:
                rp.allow_all = True     # app returns its HTML shell for any path: no robots.txt exists
                info["note"] = "no robots.txt (host returns its HTML app shell); no rules apply"
            else:
                rp.parse(body.splitlines())
        elif 400 <= r.status_code < 500:
            rp.allow_all = True
        else:
            rp.disallow_all = True
        info["parser"] = rp
    except Exception as e:
        info["status"] = "error"
        info["error"] = repr(e)[:300]
        rp = robotparser.RobotFileParser()
        rp.disallow_all = True          # unreachable -> complete disallow (RFC 9309)
        info["parser"] = rp
    robots_cache[host] = info
    return info


def classify(status, text):
    t = (text or "").lower()
    if any(m in t for m in BLOCK_MARKERS):
        return "block_page"
    if status == 200:
        return "ok"
    if status in (401, 402, 403, 429):
        return f"blocked_{status}"
    return f"http_{status}"


def plain_get(url):
    p = urlparse(url)
    polite(p.netloc)
    res = {}
    try:
        r = session.get(url, timeout=45, allow_redirects=True)
        ctype = r.headers.get("content-type", "")
        res.update(status=r.status_code, final_url=r.url, content_type=ctype,
                   bytes=len(r.content), server=r.headers.get("server", ""))
        if "pdf" in ctype.lower():
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(r.content)
            txt = subprocess.run(["pdftotext", "-layout", f.name, "-"],
                                 capture_output=True, text=True).stdout
            res["pdf_text_chars"] = len(txt.strip())
            res["excerpt"] = re.sub(r"\s+", " ", txt)[:400]
            res["verdict"] = "ok" if r.status_code == 200 else classify(r.status_code, "")
        else:
            text = r.text
            title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
            res["title"] = re.sub(r"\s+", " ", title.group(1)).strip()[:160] if title else ""
            visible = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S | re.I)
            visible = re.sub(r"<[^>]+>", " ", visible)
            visible = re.sub(r"\s+", " ", visible).strip()
            res["visible_chars"] = len(visible)
            res["excerpt"] = visible[:400]
            res["verdict"] = classify(r.status_code, text[:20000])
    except Exception as e:
        res.update(status="error", error=repr(e)[:300], verdict="network_error")
    return res


def rendered(url, browser):
    p = urlparse(url)
    polite(p.netloc)
    calls, res = [], {}
    ctx = browser.new_context(user_agent=UA)
    page = ctx.new_page()

    def on_response(resp):
        rt = resp.request.resource_type
        if rt in ("xhr", "fetch"):
            calls.append({"method": resp.request.method, "url": resp.url[:300],
                          "status": resp.status,
                          "ctype": resp.headers.get("content-type", "")[:60],
                          "post_data": (resp.request.post_data or "")[:300]})
    page.on("response", on_response)
    try:
        resp = page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        text = page.inner_text("body")[:200000]
        res.update(status=resp.status if resp else None, title=page.title()[:160],
                   rendered_chars=len(text.strip()),
                   excerpt=re.sub(r"\s+", " ", text)[:500],
                   verdict=classify(resp.status if resp else 0, text[:20000]))
    except Exception as e:
        res.update(error=repr(e)[:300], verdict="render_error")
    res["xhr_calls"] = calls[:40]
    ctx.close()
    return res


def main():
    targets = json.load(open(os.path.join(HERE, "targets.json")))
    os.makedirs(OUT, exist_ok=True)
    from playwright.sync_api import sync_playwright
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for t in targets:
            url = t["url"]
            rob = robots_for(url)
            rp = rob.get("parser")
            allowed = rp.can_fetch(UA, url) if rp else None
            row = {**t, "robots": {k: v for k, v in rob.items() if k != "parser"},
                   "robots_allows": allowed}
            if allowed is False:
                row["verdict"] = "robots_disallow"
            else:
                row["get"] = plain_get(url)
                row["verdict"] = row["get"].get("verdict")
                if t.get("js") and row["get"].get("verdict") not in ("network_error",):
                    row["render"] = rendered(url, browser)
                    rv = row["render"].get("verdict")
                    if rv == "ok":
                        row["verdict"] = "ok"
            results.append(row)
            print(f"{t['jur']:10} {t['id']:28} {row['verdict']}", flush=True)
        browser.close()

    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    ip = ""
    try:
        ip = requests.get("https://api.ipify.org", timeout=10).text
    except Exception:
        pass
    payload = {"run_utc": stamp, "runner_ip": ip, "user_agent": UA, "results": results}
    json.dump(payload, open(os.path.join(OUT, "latest.json"), "w"), indent=2)
    json.dump(payload, open(os.path.join(OUT, f"{stamp}.json"), "w"), indent=2)
    lines = ["| Jur | Target | Verdict | robots | GET | Rendered chars | XHR calls |",
             "|---|---|---|---|---|---|---|"]
    for r in results:
        g, rd = r.get("get", {}), r.get("render", {})
        lines.append(f"| {r['jur']} | {r['id']} | {r['verdict']} | "
                     f"{r['robots'].get('status')}/{r['robots_allows']} | "
                     f"{g.get('status', '')} | {rd.get('rendered_chars', '')} | {len(rd.get('xhr_calls', []))} |")
    open(os.path.join(OUT, "latest.md"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
