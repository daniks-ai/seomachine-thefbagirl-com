#!/usr/bin/env python3
"""
Scrape the three German book-industry directories that publish member email AND
website directly, so no separate harvest pass is needed.

  1. lektoren.de   — VFLL Lektorenverzeichnis. The ENTIRE directory (~1,043 cards)
                     is in one 10 MB GET of the homepage. No pagination, no JS.
                     Cards are `<div class="vlle-card" …>` with mailto + website.
  2. sbvv.ch       — Swiss Book Trade "Who is who". Open JSON endpoint, one POST
                     returns all 203 publishers with email + domain.
                     GOTCHA: the response is latin-1, NOT utf-8; records live
                     under `records`, not `data`.
  3. selfpublisher-verband.de — 1,158 author profiles enumerated from two
                     sitemaps, then one GET each for mailto + website.
                     These are actual German self-publishers = direct ICP.

Output: data/de/dir_{lektoren,sbvv,spv}.jsonl in the org/person shapes that
build_kdp_de_csv.py already understands.

Usage:
    python3 outreach/kdp/scrape_de_directories.py --source all
"""
import argparse
import gzip
import html as htmllib
import json
import re
import ssl
import urllib.parse
import urllib.request
import concurrent.futures as cf
from pathlib import Path

DE = Path(__file__).resolve().parent / "data" / "de"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
JUNK_RE = re.compile(r"(no-?reply|postmaster|abuse|@(sentry|example|wix|sample)\.)", re.I)


def fetch(url, data=None, headers=None, timeout=90):
    hdrs = {"User-Agent": UA, "Accept-Encoding": "gzip"}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw


def norm_domain(u):
    if not u:
        return ""
    u = u.strip()
    if "//" not in u:
        u = "http://" + u
    host = urllib.parse.urlparse(u).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def ok_email(e):
    e = htmllib.unescape(e or "").strip().lower()
    return e if EMAIL_RE.fullmatch(e) and not JUNK_RE.search(e) else ""


# --------------------------------------------------------------------------- 1
CARD_RE = re.compile(r'<div[^>]+class="[^"]*vlle-card[^"]*"(.*?)</div>\s*(?=<div[^>]+class="[^"]*vlle-card|$)', re.S)
NAME_RE = re.compile(r'data-namesort=["\']([^"\']+)["\']')
MAILTO_RE = re.compile(r'href=["\']mailto:([^"\'?]+)', re.I)
SITE_RE = re.compile(r'<a[^>]+title=["\']Website["\'][^>]+href=["\']([^"\']+)', re.I)
SITE_RE2 = re.compile(r'href=["\'](https?://(?!www\.lektoren\.de)[^"\']+)["\'][^>]*>\s*(?:Website|Homepage)', re.I)


def scrape_lektoren():
    html = fetch("https://www.lektoren.de/").decode("utf-8", "replace")
    out, seen = [], set()
    for chunk in CARD_RE.findall(html):
        m = MAILTO_RE.search(chunk)
        email = ok_email(m.group(1)) if m else ""
        s = SITE_RE.search(chunk) or SITE_RE2.search(chunk)
        dom = norm_domain(s.group(1)) if s else ""
        if not email and not dom:
            continue
        key = email or dom
        if key in seen:
            continue
        seen.add(key)
        nm = NAME_RE.search(chunk)
        name = nm.group(1).strip() if nm else ""
        first, last = "", ""
        if "," in name:
            last, first = [p.strip() for p in name.split(",", 1)]
        elif " " in name:
            first, last = name.rsplit(" ", 1)
        out.append({"first": first, "last": last, "brand": name or dom,
                    "domain": dom, "what": "VFLL-Lektor:in / freies Lektorat",
                    "country": "DE", "email": email})
    return out


# --------------------------------------------------------------------------- 2
def scrape_sbvv():
    body = urllib.parse.urlencode({
        "sqlid": "300", "count": "500", "offset": "0",
        "wiw_suche_fachbereich": "verlage",
    }).encode()
    raw = fetch("https://sbvv.ch/cgi-bin/swiss2017_web.exe/getjson", data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"})
    data = json.loads(raw.decode("latin-1"))          # latin-1, not utf-8
    out = []
    for rec in data.get("records", []):
        email = ok_email(rec.get("email"))
        dom = norm_domain(rec.get("domain") or rec.get("homepage") or "")
        if not email and not dom:
            continue
        out.append({"name": (rec.get("firma") or rec.get("name") or "").strip(),
                    "domain": dom, "what": "Schweizer Verlag (SBVV-Mitglied)",
                    "country": "CH", "email": email})
    return out


# --------------------------------------------------------------------------- 3
LOC_RE = re.compile(r"<loc>([^<]+)</loc>")


def scrape_spv(workers=16):
    urls = []
    for sm in ("https://www.selfpublisher-verband.de/selfpublisher_pseudo-sitemap.xml",
               "https://www.selfpublisher-verband.de/selfpublisher_pseudo-sitemap2.xml"):
        try:
            urls += [u for u in LOC_RE.findall(fetch(sm).decode("utf-8", "replace"))
                     if "/autor/" in u]
        except Exception as e:
            print(f"  sitemap {sm} failed: {e}")
    urls = sorted(set(urls))
    print(f"  {len(urls)} author profiles")

    SELF = "selfpublisher-verband.de"
    SOCIAL = re.compile(
        r"(facebook|instagram|twitter|x\.com|youtube|youtu\.be|amazon|tiktok|linkedin|"
        r"threads|bsky|mastodon|pinterest|goodreads|lovelybooks|thalia|buecher\.de|"
        r"hugendubel|osiander|epubli|bod\.de|tolino|google|w3\.org|gravatar|wordpress\.org)", re.I)

    def one(u):
        try:
            h = fetch(u, timeout=25).decode("utf-8", "replace")
        except Exception:
            return None
        # ALL mailtos; the association's own footer address is always first -> drop it
        mails = [ok_email(m) for m in MAILTO_RE.findall(h)]
        mails = [m for m in mails if m and SELF not in m]
        # the author's own site, skipping socials/retailers
        sites = []
        for cand in re.findall(r'href=["\'](https?://[^"\']+)["\']', h):
            d = norm_domain(cand)
            if d and SELF not in d and not SOCIAL.search(d) and d not in sites:
                sites.append(d)
        dom = sites[0] if sites else ""
        # prefer an address that lives on the author's own domain
        email = ""
        root = ".".join(dom.split(".")[-2:]) if dom.count(".") >= 1 else dom
        for m in mails:
            if root and m.split("@")[-1].endswith(root):
                email = m
                break
        if not email and mails:
            email = mails[0]
        if not email:
            return None
        name = ""
        t = re.search(r"<title>([^<]+)</title>", h)
        if t:
            name = re.split(r"[|\u2013-]", htmllib.unescape(t.group(1)))[0].strip()
        first, last = (name.split(" ", 1) + [""])[:2] if " " in name else (name, "")
        return {"first": first, "last": last, "brand": name or dom, "domain": dom,
                "what": "Selfpublisher (Verbandsmitglied)", "country": "DE",
                "email": email}

    out = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for i, r in enumerate(ex.map(one, urls), 1):
            if r:
                out.append(r)
            if i % 200 == 0:
                print(f"  {i}/{len(urls)} | {len(out)} usable")
    return out


SOURCES = {"lektoren": (scrape_lektoren, "dir_lektoren.jsonl"),
           "sbvv": (scrape_sbvv, "dir_sbvv.jsonl"),
           "spv": (scrape_spv, "dir_spv.jsonl")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="all", choices=list(SOURCES) + ["all"])
    a = ap.parse_args()
    todo = list(SOURCES) if a.source == "all" else [a.source]
    for key in todo:
        fn, out = SOURCES[key]
        print(f"== {key}")
        try:
            rows = fn()
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")
            continue
        (DE / out).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
        print(f"  {len(rows)} rows -> {DE/out} ({sum(1 for r in rows if r['email'])} with email)")


if __name__ == "__main__":
    main()
