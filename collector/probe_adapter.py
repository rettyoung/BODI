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


def main(names):
    cfg = yaml.safe_load(open(os.path.join(ROOT, "config", "watchlist.yaml")))
    for name in names:
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
        except Exception as e:
            out.update(error=repr(e), trace=traceback.format_exc()[-2000:])
        finally:
            ctx.close()
        out.update(notes=ctx.notes, sub=ctx.sub, exchanges=exchanges[:80], adapter_state=ctx.state)
        save_json(os.path.join(DATA, "debug", f"{name}.json"), out)
        print(name, out.get("items"), out.get("error", ""), len(exchanges), "exchanges", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or ["ok_occ", "mo_efis", "al_psc", "nm_prc", "az_acc"])
