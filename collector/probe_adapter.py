"""Run adapters with every HTTP exchange recorded, for repairing parsers from real responses.

usage: python probe_adapter.py ok_occ mo_efis ...   -> data/debug/<adapter>.json
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


def main(names):
    cfg = yaml.safe_load(open(os.path.join(ROOT, "config", "watchlist.yaml")))
    for name in names:
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
