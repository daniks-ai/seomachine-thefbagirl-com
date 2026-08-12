#!/usr/bin/env python3
"""Second-pass email harvester for domains that came back empty from 2b.

2b fetches the homepage + 2 contact links and regex-greps for plain emails. It
misses the three ways sites actually hide addresses:

  1. Cloudflare Email Obfuscation — `<a data-cfemail="hex">[email protected]</a>`
     (this is what daniks.ai itself uses, so it's everywhere).
  2. Human-readable munging — "info [at] example [dot] com", "info (at) example".
  3. Addresses that only live on a deeper contact page 2b never reached
     (/contact-us, /get-in-touch, /reach-us, /enquiry, /team, …).

Output merges into the same `_harvest_progress.json` / `layer1_contacts_raw.json`
shape as 2b, so downstream builders need no changes. Stdlib only, resumable.

Usage:
    python3 outreach/scripts/2c_deep_harvest.py --domains-file <file>
    python3 outreach/scripts/2c_deep_harvest.py --domains-file <file> --workers 16
"""
import argparse
import concurrent.futures as cf
import gzip
import json
import re
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
PROGRESS = DATA / "_harvest_progress.json"
OUT = DATA / "layer1_contacts_raw.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
CF_RE = re.compile(r'data-cfemail=["\']([0-9a-fA-F]+)["\']')
# "info [at] example [dot] com" / "info (at) example (dot) com" / "info AT example DOT com"
MUNGED_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]+)\s*(?:\[at\]|\(at\)|\{at\}|\s+at\s+)\s*"
    r"([a-zA-Z0-9.\-]+)\s*(?:\[dot\]|\(dot\)|\{dot\}|\s+dot\s+)\s*([a-zA-Z]{2,})",
    re.I)

CONTACT_PATHS = ["/contact", "/contact-us", "/contactus", "/about", "/about-us",
                 "/get-in-touch", "/reach-us", "/enquiry", "/team", "/support"]
CONTACT_HINT = re.compile(r"(contact|about|team|reach|touch|enquir|inquir|support|connect)", re.I)

JUNK_RE = re.compile(
    r"(no-?reply|noreply|postmaster|mailer-daemon|abuse|hostmaster|dns-admin|sentry|"
    r"@(?:example|wix|squarespace|godaddy|wordpress|shopify|cloudflare|netlify|"
    r"gmail|googlemail|yahoo|hotmail|outlook|domain|email|company)\.)", re.I)
IMG_EXT_RE = re.compile(r"\.(png|jpg|jpeg|gif|svg|webp|css|js|ico|woff|ttf)$", re.I)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def decode_cfemail(hexstr):
    """Cloudflare XORs each byte with the first byte of the hex blob."""
    try:
        b = bytes.fromhex(hexstr)
        key = b[0]
        return "".join(chr(c ^ key) for c in b[1:])
    except Exception:
        return ""


def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        raw = r.read(2_000_000)
        if r.headers.get("Content-Encoding") == "gzip":
            try:
                raw = gzip.decompress(raw)
            except OSError:
                pass
        return raw.decode("utf-8", "replace"), r.geturl()


def emails_from(html):
    found = set(EMAIL_RE.findall(html))
    for m in re.findall(r'mailto:([^"\'?>&]+)', html, re.I):
        found.add(urllib.parse.unquote(m))
    for hx in CF_RE.findall(html):
        d = decode_cfemail(hx)
        if "@" in d:
            found.add(d)
    for local, dom, tld in MUNGED_RE.findall(html):
        found.add(f"{local}@{dom}.{tld}")
    return found


def clean(found, domain):
    root = domain.split(".")[-2] if "." in domain else domain
    out = set()
    for e in found:
        e = e.strip().strip(".,;:").lower()
        e = re.sub(r"^(%20|mailto:)+", "", e)
        if IMG_EXT_RE.search(e) or JUNK_RE.search(e) or e.count("@") != 1:
            continue
        local, host = e.split("@")
        if not local or "." not in host or len(e) > 80:
            continue
        if not re.match(r"^[a-z0-9][a-z0-9._%+\-]*$", local):
            continue
        # second pass is on-domain only — third-party strays are what polluted pass 1
        if root not in host:
            continue
        out.add(e)
    return out


def harvest(domain):
    rec = {"domain": domain, "emails": [], "linkedIns": [], "scrapedUrls": [], "pass": 2}
    pages, base = [], None
    for scheme in ("https://", "http://"):
        for host in (domain, "www." + domain):
            try:
                html, final = fetch(scheme + host)
                base, pages = final, [(final, html)]
                break
            except Exception:
                continue
        if base:
            break
    if base is None:
        rec["error"] = "unreachable"
        return rec

    origin = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(base))
    seen = {base}
    targets = []
    # links the homepage itself offers
    for href in LINK_RE.findall(pages[0][1]):
        if len(targets) >= 4:
            break
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue
        if not CONTACT_HINT.search(href):
            continue
        url = urllib.parse.urljoin(base, href)
        if url in seen or IMG_EXT_RE.search(url) or urllib.parse.urlsplit(url).netloc not in base:
            continue
        seen.add(url)
        targets.append(url)
    # plus the conventional paths, which many sites don't link from the header
    for p in CONTACT_PATHS:
        if len(targets) >= 7:
            break
        url = origin + p
        if url not in seen:
            seen.add(url)
            targets.append(url)

    for url in targets:
        try:
            html, final = fetch(url)
            pages.append((final, html))
        except Exception:
            pass

    found, lis = set(), set()
    for final, html in pages:
        rec["scrapedUrls"].append(final)
        found |= emails_from(html)
        for li in re.findall(r'https?://[a-z]{0,3}\.?linkedin\.com/(?:company|in)/[^"\'\s<>]+', html, re.I):
            lis.add(li.rstrip("/").split("?")[0])
    rec["emails"] = sorted(clean(found, domain))
    rec["linkedIns"] = sorted(lis)[:3]
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains-file", required=True)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    domains = [d.strip().lower() for d in Path(args.domains_file).read_text().split() if d.strip()]
    if args.limit:
        domains = domains[: args.limit]
    cache = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}

    print(f"deep pass over {len(domains)} domains, {args.workers} workers")
    hits = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(harvest, d): d for d in domains}
        for i, fut in enumerate(cf.as_completed(futs), 1):
            d = futs[fut]
            try:
                rec = fut.result()
            except Exception as e:
                rec = {"domain": d, "emails": [], "error": str(e)[:60], "pass": 2}
            if rec.get("emails"):
                # keep pass-1 record if it already had emails; else upgrade
                if not cache.get(d, {}).get("emails"):
                    cache[d] = rec
                    hits += 1
            if i % 50 == 0:
                PROGRESS.write_text(json.dumps(cache, ensure_ascii=False))
                print(f"  {i}/{len(domains)} | {hits} recovered")

    PROGRESS.write_text(json.dumps(cache, ensure_ascii=False))
    OUT.write_text(json.dumps(list(cache.values()), ensure_ascii=False), encoding="utf-8")
    print(f"recovered {hits} domains that pass 1 left empty")


if __name__ == "__main__":
    main()
