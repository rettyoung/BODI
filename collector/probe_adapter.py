"""Run adapters with every HTTP exchange recorded, for repairing parsers from real responses.

usage: python probe_adapter.py ok_occ mo_efis ...   -> data/debug/<adapter>.json
       python probe_adapter.py fetch:data/filings/TX/tx_puct/<id>.json   -> document fetch for one filing
       python probe_adapter.py tls:images.edocket.azcc.gov                -> TLS / AIA / robots diagnosis
Never writes candidates, filings or collector state.
"""
import json
import os
import sys
import traceback

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa
from common import Http, DATA, ROOT, save_json  # noqa
import adapters as A  # noqa
from run import Ctx  # noqa

SINCE = os.environ.get("PROBE_SINCE", "2026-06-01")


def tls(host):
    import ssl, socket, requests
    out = {"host": host}
    try:
        out["leaf_pem_head"] = ssl.get_server_certificate((host, 443), timeout=30)[:200]
    except Exception as e:
        out["leaf_error"] = repr(e)[:1000]
    try:
        requests.get(f"https://{host}/robots.txt", timeout=30)
        out["default_verify"] = "ok"
    except Exception as e:
        out["default_verify_error"] = repr(e)[:1500]
    try:
        b = common.aia_bundle(host)
        r = requests.get(f"https://{host}/robots.txt", timeout=30, verify=b)
        out.update(aia="ok", robots_status=r.status_code, robots_body=r.text[:800])
    except Exception as e:
        out["aia_error"] = repr(e)[:1500]
    return out


def nmdoc(http, case_id):
    """Try envelope variants for the NM e360 public-documents list; report item counts."""
    api = "https://e360.prc.nm.gov/core/api/apiflow/v1/prc/nm/intake/"
    def env(params=None, qp=None, data=None, key="CaseX"):
        params = params if params is not None else {"caseId": case_id}
        return {"data": data or {}, "origin": "", "origin_key": key, "queryParams": qp if qp is not None else ["caseId"],
                "gridInput": {"params": {"parameters": params}, "persistPrevParams": False}, "parameters": params,
                "pageNo": 1, "pageSize": 50, "sortBy": {}}
    variants = {
        "current": ("casepublicdocument/getAll", env()),
        "qp_values": ("casepublicdocument/getAll", env(qp=[case_id])),
        "lower_caseid": ("casepublicdocument/getAll", env(params={"caseid": case_id}, qp=["caseid"])),
        "data_caseId": ("casepublicdocument/getAll", env(data={"caseId": case_id})),
        "key_doc": ("casepublicdocument/getAll", env(key="CasePublicDocumentX")),
        "key_doc2": ("casepublicdocument/getAll", env(key="PublicDocumentX")),
        "casedocument": ("casedocument/getAll", env()),
        "publicdocument": ("publicdocument/getAll", env()),
        "casepublicdocuments": ("casepublicdocuments/getAll", env()),
        "docket_number": ("casepublicdocument/getAll", env(params={"caseId": case_id, "docketNumber": ""})),
    }
    out = {}
    for name, (path, body) in variants.items():
        try:
            r = http.post(api + path, json=body, headers={"Content-Type": "application/json"})
            j = r.json() if "json" in (r.headers.get("content-type") or "") else {}
            out[name] = {"status": r.status_code, "total": j.get("totalItemCount"), "first": str((j.get("items") or [None])[0])[:600],
                         "msg": j.get("message")}
        except Exception as e:
            out[name] = {"error": repr(e)[:300]}
    return out


def urlprobe(cfg, listfile):
    """Probe candidate source URLs from the runner: robots verdict, status, block markers, links.
    listfile lines: [R|]<url>   (R| = render with headless Chromium). Blank lines and # comments ignored."""
    import re
    from urllib.parse import urljoin
    http = Http(delay=2)
    http.session.headers["User-Agent"] = cfg["user_agent"]
    ctx = Ctx(cfg, {"seen": {}, "sources": {}}, http)
    out = []
    for line in open(os.path.join(ROOT, listfile)):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        render = line.startswith("R|")
        keep = line.startswith("B|")
        dump = line.startswith("D|")
        url = line[2:] if (render or keep or dump) else line
        o = {"url": url, "render": render}
        try:
            hs = http._robots(url)
            o["robots_status"], o["robots_note"] = hs.robots_status, hs.robots_note
            o["allowed"] = hs.robots.can_fetch(http.session.headers["User-Agent"], url)
            try:
                o["crawl_delay"] = hs.robots.crawl_delay(http.session.headers["User-Agent"])
            except Exception:
                pass
            if not o["allowed"]:
                out.append(o)
                continue
            if render:
                body = ctx.render(url)
                o.update(status="rendered", ctype="text/html")
            else:
                r = http.get(url, retries=0, timeout=60)
                body = r.text if not r.content[:4] == b"%PDF" else "<pdf>"
                o.update(status=r.status_code, ctype=r.headers.get("content-type"), final_url=r.url)
            o["len"] = len(body)
            o["head"] = body[:1500]
            if keep:
                o["body"] = body[:40000]
            if dump:
                from common import slug
                pth = os.path.join(DATA, "debug", "pages", slug(url, 90) + ".txt")
                os.makedirs(os.path.dirname(pth), exist_ok=True)
                open(pth, "w").write(body[:3_000_000])
                o["dumped"] = pth
            links = re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', body, re.S | re.I)
            o["n_links"] = len(links)
            o["links"] = [[urljoin(url, h.replace("&amp;", "&")), re.sub(r"<[^>]+>|\s+", " ", t).strip()[:120]] for h, t in links][:250]
            if "<rss" in body[:500] or "<feed" in body[:500]:
                o["feed_items"] = re.findall(r"<title>(.*?)</title>", body, re.S)[:15]
        except Exception as e:
            o["error"] = repr(e)[:500]
        out.append(o)
        print(url, o.get("allowed"), o.get("status"), o.get("len"), o.get("n_links"), o.get("error", ""), flush=True)
    ctx.close()
    save_json(os.path.join(DATA, "debug", "urlprobe_" + os.path.basename(listfile).rsplit(".", 1)[0] + ".json"), out)


def main(names):
    cfg = yaml.safe_load(open(os.path.join(ROOT, "config", "watchlist.yaml")))
    for name in names:
        if name.startswith("urls:"):
            urlprobe(cfg, name[5:])
            continue
        if name.startswith("nmdoc:"):
            http = Http(delay=2)
            http.session.headers["User-Agent"] = cfg["user_agent"]
            o = nmdoc(http, name[6:])
            save_json(os.path.join(DATA, "debug", "nmdoc.json"), o)
            print(json.dumps(o)[:3000], flush=True)
            continue
        if name.startswith("tls:"):
            o = tls(name[4:])
            save_json(os.path.join(DATA, "debug", "tls_" + name[4:].replace(".", "_") + ".json"), o)
            print(o, flush=True)
            continue
        if name.startswith("fetch:"):
            from run import fetch_docs
            http = Http(delay=2)
            http.session.headers["User-Agent"] = cfg["user_agent"]
            filing = json.load(open(os.path.join(ROOT, name[6:])))
            o = {"filing": name[6:], "fetch": filing.get("fetch")}
            try:
                if filing.get("fetch") and "tx_item" in filing["fetch"][0]:
                    ctrl, item = filing["fetch"][0]["tx_item"]
                    r = http.get(f"https://interchange.puc.texas.gov/search/documents/?controlNumber={ctrl}&itemNumber={item}")
                    o.update(listing_status=r.status_code, listing_len=len(r.text), listing_head=r.text[:3000],
                             hrefs=__import__("re").findall(r'href="([^"]+)"', r.text)[:80])
                docs = fetch_docs(http, filing, Ctx(cfg, {"seen": {}, "sources": {}}, http))
                o["docs"] = [{k: (v[:300] if isinstance(v, str) else v) for k, v in d.items()} for d in docs]
            except Exception as e:
                o["error"] = repr(e)[:1500]
            o["log"] = http.log[-30:]
            save_json(os.path.join(DATA, "debug", "fetch_" + os.path.basename(name[6:])), o)
            print(json.dumps(o)[:2000], flush=True)
            continue
        with_docs = name.endswith("+docs")
        name = name[:-5] if with_docs else name
        http = Http(delay=2)
        http.session.headers["User-Agent"] = cfg["user_agent"]
        exchanges = []
        orig = http.session.request

        def rec(method, url, _o=orig, **kw):
            r = _o(method, url, **kw)
            body = kw.get("json") or kw.get("data")
            exchanges.append({"method": method, "url": url, "req": str(body)[:1500], "status": r.status_code,
                              "ctype": r.headers.get("content-type"), "len": len(r.content),
                              "body": r.text[:6000] if "pdf" not in (r.headers.get("content-type") or "") else "<pdf>"})
            return r
        http.session.request = rec
        ctx = Ctx(cfg, {"seen": {}, "sources": {}}, http)
        ctx.since = SINCE
        out = {"adapter": name, "since": SINCE}
        try:
            items = A.ADAPTERS[name](ctx) or []
            out.update(items=len(items), sample=items[:8])
            if with_docs:
                from run import fetch_docs
                fetched = []
                for it in [i for i in items if i.get("fetch")][:3]:
                    docs = fetch_docs(http, it, ctx)
                    pp = (it.get("meta") or {}).get("postprocess")
                    if pp:
                        A.POSTPROCESS[pp](it, docs)
                    fetched.append({"id": it["id"], "meta": it.get("meta"),
                                    "docs": [{k: (v[:1500] if isinstance(v, str) else v) for k, v in d.items()} for d in docs]})
                out["fetched"] = fetched
        except Exception as e:
            out.update(error=repr(e), trace=traceback.format_exc()[-2000:])
        finally:
            ctx.close()
        out.update(notes=ctx.notes, sub=ctx.sub, exchanges=[{**x, "body": x["body"][:2000]} for x in exchanges[:60]], adapter_state=ctx.state)
        save_json(os.path.join(DATA, "debug", f"{name}.json"), out)
        print(name, out.get("items"), out.get("error", ""), len(exchanges), "exchanges", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or ["ok_occ", "mo_efis", "al_psc", "nm_prc", "az_acc"])
