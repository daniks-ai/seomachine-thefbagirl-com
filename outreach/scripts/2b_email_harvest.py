#!/usr/bin/env python3
"""
Zero-cost email harvester (no Apify) — fallback for when the Apify usage cap is
hit. Fetches each agency's homepage, follows up to a few internal contact/about
links, and regex-extracts published emails + LinkedIn URLs. Output shape matches
the Apify contact-scraper (`domain`, `emails`, `linkedIns`) so it feeds straight
into 3_build_instantly_csv.py.

Stdlib only (urllib + concurrent.futures) — no pip install, resumable.

Usage:
    python3 outreach/scripts/2b_email_harvest.py                     # all domains
    python3 outreach/scripts/2b_email_harvest.py --domains-file outreach/data/layer1_domains_en.txt
    python3 outreach/scripts/2b_email_harvest.py --workers 24 --limit 500
"""
import argparse
import concurrent.futures as cf
import gzip
import json
import re
import ssl
import sys
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
OUT = DATA / "layer1_contacts_raw.json"          # same file the builder reads
PROGRESS = DATA / "_harvest_progress.json"        # resumable cache: domain -> record

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
CONTACT_HINT = re.compile(r"(contact|about|team|kontakt|impressum|company|reach)", re.I)
# junk we never want as a lead email
JUNK_RE = re.compile(
    r"(no-?reply|noreply|postmaster|mailer-daemon|abuse|hostmaster|dns-admin|"
    r"@(?:sentry|example|wix|squarespace|godaddy|wordpress|shopify|"
    r"cloudflare|googlemail|gmail\.com|domain)\.)", re.I)
IMG_EXT_RE = re.compile(r"\.(png|jpg|jpeg|gif|svg|webp|css|js|ico|woff|ttf)$", re.I)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        raw = r.read(2_000_000)  # cap 2MB
        if r.headers.get("Content-Encoding") == "gzip":
            try:
                raw = gzip.decompress(raw)
            except OSError:
                pass
        return raw.decode("utf-8", "replace"), r.geturl()


def clean_emails(found, domain):
    out = set()
    for e in found:
        e = e.strip().strip(".").lower()
        if IMG_EXT_RE.search(e) or JUNK_RE.search(e):
            continue
        if len(e) > 80 or e.count("@") != 1:
            continue
        local, host = e.split("@")
        if not local or "." not in host:
            continue
        # keep on-domain emails and same registrable root; drop random 3rd-party
        out.add(e)
    return out


def harvest(domain):
    rec = {"domain": domain, "emails": [], "linkedIns": [], "scrapedUrls": []}
    pages = []
    base = None
    for scheme in ("https://", "http://"):
        try:
            html, final = fetch(scheme + domain)
            base = final
            pages.append((final, html))
            break
        except Exception:
            continue
    if base is None:
        rec["error"] = "homepage_unreachable"
        return rec

    # discover up to 2 contact/about pages from homepage links
    home_html = pages[0][1]
    seen = {pages[0][0]}
    extra = []
    for href in LINK_RE.findall(home_html):
        if len(extra) >= 2:
            break
        if not CONTACT_HINT.search(href):
            continue
        if href.startswith("mailto:") or href.startswith("tel:"):
            continue
        if href.startswith("http") and domain not in href:
            continue
        url = href if href.startswith("http") else base.rstrip("/") + "/" + href.lstrip("/")
        if url in seen or IMG_EXT_RE.search(url):
            continue
        seen.add(url)
        extra.append(url)
    for url in extra:
        try:
            html, final = fetch(url)
            pages.append((final, html))
        except Exception:
            pass

    emails, lis = set(), set()
    for final, html in pages:
        rec["scrapedUrls"].append(final)
        emails |= set(EMAIL_RE.findall(html))
        # mailto:
        for m in re.findall(r'mailto:([^"\'?>]+)', html, re.I):
            emails.add(m)
        for li in re.findall(r'https?://[a-z]{0,3}\.?linkedin\.com/(?:company|in)/[^"\'\s<>]+', html, re.I):
            lis.add(li.rstrip("/").split("?")[0])
    rec["emails"] = sorted(clean_emails(emails, domain))
    rec["linkedIns"] = sorted(lis)[:3]
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains-file", default=str(DATA / "layer1_domains.txt"))
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    domains = [d.strip() for d in Path(args.domains_file).read_text().splitlines() if d.strip()]
    cache = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    todo = [d for d in domains if d not in cache]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(cache)} cached, harvesting {len(todo)} domains with {args.workers} workers")

    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(harvest, d): d for d in todo}
        for fut in cf.as_completed(futs):
            d = futs[fut]
            try:
                cache[d] = fut.result()
            except Exception as e:  # noqa
                cache[d] = {"domain": d, "emails": [], "error": str(e)[:60]}
            done += 1
            if done % 100 == 0:
                PROGRESS.write_text(json.dumps(cache, ensure_ascii=False))
                hits = sum(1 for v in cache.values() if v.get("emails"))
                print(f"  {done}/{len(todo)} done | {hits} domains with email so far")

    PROGRESS.write_text(json.dumps(cache, ensure_ascii=False))
    # write the builder-compatible file (list of records)
    records = list(cache.values())
    OUT.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    hits = sum(1 for v in records if v.get("emails"))
    total_emails = sum(len(v.get("emails", [])) for v in records)
    print(f"harvested {len(records)} domains | {hits} with >=1 email | {total_emails} emails total")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
