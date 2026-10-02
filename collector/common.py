"""Shared plumbing for the Grid Docket collector.

Every network call in the collector goes through `Http`, which enforces the
rules that keep the collector legitimate:

* honest identification (SEC-compliant User-Agent with a contact address);
* robots.txt honoured per RFC 9309 (2xx parse, 4xx no rules, 5xx/unreachable
  = complete disallow; a firewall block page served as robots.txt = disallow;
  an HTML app shell served as robots.txt = no robots file);
* one request per host every `delay` seconds;
* no CAPTCHA solving, no stealth, no IP rotation, no login walls;
* a firewall/CAPTCHA/login page is recorded as BLOCKED, never parsed as content.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from typing import Optional
from urllib import robotparser
from urllib.parse import urlparse

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = "BlueOwl-RegTracker/4.0 (rett.young@blueowl.com)"
MAX_TEXT = 300_000          # characters of extracted text kept per document
EMPTY_TEXT_PER_PAGE = 200   # below this per page = no text layer (needs OCR)

BLOCK_MARKERS = [
    "request rejected", "the requested url was rejected", "access denied",
    "attention required", "just a moment", "enable javascript and cookies to continue",
    "cf-chl", "captcha", "not a robot", "no robots or crawlers", "incapsula",
    "undeclared automated tool", "web page blocked", "you do not have permission to view",
]
FIREWALL_MARKERS = BLOCK_MARKERS[:3]


def now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def slug(s: str, n: int = 80) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s or "").strip("_")[:n] or "x"


def looks_blocked(text: str) -> Optional[str]:
    t = (text or "")[:20000].lower()
    for m in BLOCK_MARKERS:
        if m in t:
            return m
    return None


def aia_bundle(host: str, port: int = 443) -> str:
    """Complete a server's incomplete certificate chain the way browsers do (AIA fetching).

    Reads the leaf certificate (trusting nothing), downloads the issuing intermediate from the
    leaf's Authority Information Access URL, and returns a CA file = the normal trust store plus
    that intermediate. Verification stays fully on: the chain must still end at a trusted root
    and the hostname must still match. Never disable TLS verification instead.
    """
    import ssl
    import certifi
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID
    leaf = x509.load_pem_x509_certificate(ssl.get_server_certificate((host, port), timeout=30).encode())
    aia = leaf.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value
    urls = [d.access_location.value for d in aia if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS]
    if not urls:
        raise RuntimeError(f"no AIA issuer URL on {host}")
    raw = requests.get(urls[0], timeout=30, headers={"User-Agent": UA}).content
    try:
        inter = x509.load_der_x509_certificate(raw)
    except ValueError:
        inter = x509.load_pem_x509_certificate(raw)
    path = os.path.join(tempfile.gettempdir(), f"ca_{slug(host)}.pem")
    with open(path, "wb") as f:
        f.write(open(certifi.where(), "rb").read() + b"\n" + inter.public_bytes(serialization.Encoding.PEM))
    return path


def _chain_incomplete(e: Exception) -> bool:
    t = str(e).lower()
    return "unable to get local issuer certificate" in t or "certificate verify failed: unable to get" in t


class Blocked(Exception):
    """The host refused us (robots, firewall, challenge, 401/403/402/429)."""


@dataclass
class HostState:
    last: float = 0.0
    robots: Optional[robotparser.RobotFileParser] = None
    robots_status: object = None
    robots_note: str = ""
    ca_bundle: Optional[str] = None   # trust store + the server's missing intermediate (AIA), when needed


@dataclass
class Http:
    delay: float = 3.0
    timeout: int = 60
    session: requests.Session = field(default_factory=requests.Session)
    hosts: dict = field(default_factory=dict)
    log: list = field(default_factory=list)

    def __post_init__(self):
        self.session.headers.update({"User-Agent": UA, "Accept": "*/*",
                                     "Accept-Encoding": "gzip, deflate"})

    # ---------------- politeness ----------------
    def _host(self, url: str) -> HostState:
        p = urlparse(url)
        key = f"{p.scheme}://{p.netloc}"
        if key not in self.hosts:
            self.hosts[key] = HostState()
        return self.hosts[key]

    def _wait(self, hs: HostState):
        gap = self.delay - (time.time() - hs.last)
        if gap > 0:
            time.sleep(gap)
        hs.last = time.time()

    def _robots(self, url: str) -> HostState:
        hs = self._host(url)
        if hs.robots is not None:
            return hs
        p = urlparse(url)
        rurl = f"{p.scheme}://{p.netloc}/robots.txt"
        rp = robotparser.RobotFileParser()
        self._wait(hs)
        try:
            try:
                r = self.session.get(rurl, timeout=30, verify=hs.ca_bundle or True)
            except requests.exceptions.SSLError as e:
                if not _chain_incomplete(e):
                    raise
                hs.ca_bundle = aia_bundle(p.hostname, p.port or 443)
                r = self.session.get(rurl, timeout=30, verify=hs.ca_bundle)
            hs.robots_status = r.status_code
            body = r.content.decode("utf-8-sig", errors="replace").lstrip("﻿")
            head = body[:3000].lower()
            if 200 <= r.status_code < 300:
                if "<html" in head and any(m in head for m in FIREWALL_MARKERS):
                    rp.disallow_all = True
                    hs.robots_note = "firewall page served as robots.txt"
                elif "<html" in head:
                    rp.allow_all = True
                    hs.robots_note = "no robots.txt (HTML app shell)"
                else:
                    rp.parse(body.splitlines())
            elif 400 <= r.status_code < 500:
                rp.allow_all = True
            else:
                rp.disallow_all = True
                hs.robots_note = f"robots.txt {r.status_code} (unreachable => disallow)"
        except Exception as e:  # unreachable => complete disallow (RFC 9309)
            hs.robots_status = "error"
            hs.robots_note = repr(e)[:200]
            rp.disallow_all = True
        hs.robots = rp
        return hs

    def allowed(self, url: str) -> bool:
        return self._robots(url).robots.can_fetch(UA, url)

    # ---------------- requests ----------------
    def request(self, method: str, url: str, retries: int = 2, **kw) -> requests.Response:
        hs = self._robots(url)
        if not hs.robots.can_fetch(UA, url):
            self.log.append({"url": url, "result": "robots_disallow", "note": hs.robots_note})
            raise Blocked(f"robots.txt disallows {url} ({hs.robots_note or hs.robots_status})")
        kw.setdefault("timeout", self.timeout)
        last_exc = None
        for attempt in range(retries + 1):
            self._wait(hs)
            try:
                r = self.session.request(method, url, verify=hs.ca_bundle or True, **kw)
            except requests.exceptions.SSLError as e:
                if _chain_incomplete(e) and not hs.ca_bundle:
                    p = urlparse(url)
                    try:
                        hs.ca_bundle = aia_bundle(p.hostname, p.port or 443)
                        self.log.append({"url": url, "result": "tls_chain_completed_via_aia"})
                        continue
                    except Exception as e2:
                        last_exc = e2
                        break
                last_exc = e
                break
            except requests.RequestException as e:
                last_exc = e
                time.sleep(4 * (attempt + 1))
                continue
            if r.status_code in (401, 402, 403, 429):
                self.log.append({"url": url, "result": f"blocked_{r.status_code}"})
                raise Blocked(f"HTTP {r.status_code} for {url}")
            if r.status_code >= 500 and attempt < retries:
                time.sleep(5 * (attempt + 1))
                continue
            ctype = r.headers.get("content-type", "").lower()
            if "html" in ctype or "text" in ctype:
                m = looks_blocked(r.text)
                if m and len(r.text) < 60000:
                    self.log.append({"url": url, "result": "block_page", "marker": m})
                    raise Blocked(f"block page ({m}) at {url}")
            self.log.append({"url": url, "result": r.status_code})
            return r
        raise last_exc or RuntimeError(f"failed {url}")

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)


# ---------------- text extraction ----------------
def _run(cmd, inp=None, timeout=300):
    return subprocess.run(cmd, input=inp, capture_output=True, timeout=timeout)


def pdf_text(data: bytes) -> dict:
    """Extract text from a PDF. OCR only when there is no text layer.

    Returns {text, pages, ocr, quality}. OCR text is flagged so the sweep never
    treats an OCR-derived number as Verified.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(data)
        path = f.name
    pages = 0
    try:
        info = _run(["pdfinfo", path], timeout=60).stdout.decode("utf-8", "replace")
        m = re.search(r"Pages:\s+(\d+)", info)
        pages = int(m.group(1)) if m else 0
    except Exception:
        pass
    txt = _run(["pdftotext", "-layout", path, "-"], timeout=300).stdout.decode("utf-8", "replace")
    ocr = False
    if pages and len(txt.strip()) < EMPTY_TEXT_PER_PAGE * max(1, min(pages, 5)):
        # no text layer: OCR the first 40 pages
        ocr = True
        out = []
        with tempfile.TemporaryDirectory() as td:
            _run(["pdftoppm", "-r", "200", "-l", "40", "-png", path, os.path.join(td, "p")], timeout=600)
            for img in sorted(os.listdir(td)):
                r = _run(["tesseract", os.path.join(td, img), "-", "--psm", "1"], timeout=180)
                out.append(r.stdout.decode("utf-8", "replace"))
        txt = "\n\f".join(out)
    os.unlink(path)
    quality = "ocr" if ocr else ("empty" if len(txt.strip()) < 50 else "text_layer")
    return {"text": txt[:MAX_TEXT], "pages": pages, "ocr": ocr, "quality": quality,
            "truncated": len(txt) > MAX_TEXT}


def html_text(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "svg"]):
        t.decompose()
    text = soup.get_text("\n")
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()[:MAX_TEXT]


def xlsx_text(data: bytes) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f"## sheet: {ws.title}")
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i > 2000:
                out.append("...truncated")
                break
            out.append("\t".join("" if v is None else str(v) for v in row))
    return "\n".join(out)[:MAX_TEXT]


def docx_text(data: bytes) -> str:
    import docx  # python-docx
    d = docx.Document(io.BytesIO(data))
    return "\n".join(p.text for p in d.paragraphs)[:MAX_TEXT]


def extract(data: bytes, ctype: str = "", url: str = "") -> dict:
    """Best-effort text extraction for any document type."""
    ctype = (ctype or "").lower()
    low = url.lower().split("?")[0]
    try:
        if data[:4] == b"%PDF" or "pdf" in ctype or low.endswith(".pdf"):
            return pdf_text(data)
        if data[:2] == b"PK" or "zip" in ctype or low.endswith((".zip", ".xlsx", ".docx")):
            zf = zipfile.ZipFile(io.BytesIO(data))
            names = zf.namelist()
            if "word/document.xml" in names:
                return {"text": docx_text(data), "pages": None, "ocr": False, "quality": "docx"}
            if "xl/workbook.xml" in names:
                return {"text": xlsx_text(data), "pages": None, "ocr": False, "quality": "xlsx"}
            parts, ocr = [], False
            for n in names[:25]:
                if n.lower().endswith((".pdf", ".xlsx", ".docx", ".txt", ".htm", ".html", ".csv")):
                    sub = extract(zf.read(n), url=n)
                    ocr = ocr or sub.get("ocr", False)
                    parts.append(f"=== {n} ===\n{sub['text']}")
            return {"text": "\n\n".join(parts)[:MAX_TEXT], "pages": None, "ocr": ocr,
                    "quality": "zip", "members": names[:50]}
        if "html" in ctype or low.endswith((".htm", ".html")) or data.lstrip()[:1] == b"<":
            return {"text": html_text(data.decode("utf-8", "replace")), "pages": None,
                    "ocr": False, "quality": "html"}
        return {"text": data.decode("utf-8", "replace")[:MAX_TEXT], "pages": None,
                "ocr": False, "quality": "text"}
    except Exception as e:
        return {"text": "", "pages": None, "ocr": False, "quality": f"extract_error: {e!r}"[:200]}


# ---------------- storage ----------------
def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, default=str)
    os.replace(tmp, path)
