#!/usr/bin/env python3
"""
Deep second-pass email harvester for domains where 2b found nothing.

Differences vs 2b_email_harvest.py:
- probes common contact paths directly (/contact, /contact-us, /about, ...)
  even when the homepage has no matching link;
- follows up to 5 contact-ish internal links (2b: 2);
- decodes Cloudflare email obfuscation (data-cfemail) and simple
  "name [at] domain [dot] com" spellings;
- own progress cache (_deep_harvest_progress.json) so cached empty results
  from the first pass are re-tried, then merges results back into
  layer1_contacts_raw.json (the file 3_build_instantly_csv.py reads).

Usage:
    python3 outreach/scripts/2c_deep_harvest.py --domains-file outreach/data/us_domains_noemail.txt
"""
import argparse
import concurrent.futures as cf
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module
h = import_module("2b_email_harvest")

DATA = Path(__file__).resolve().parents[1] / "data"
PROGRESS = DATA / "_deep_harvest_progress.json"
OUT = DATA / "layer1_contacts_raw.json"

COMMON_PATHS = ["contact", "contact-us", "contactus", "about", "about-us",
                "team", "our-team", "company", "get-in-touch"]
CONTACT_HINT = re.compile(r"(contact|about|team|kontakt|company|reach|touch|connect|support)", re.I)
CF_RE = re.compile(r'data-cfemail="([0-9a-f]+)"', re.I)
AT_RE = re.compile(r"([a-z0-9._%+\-]+)\s*(?:\[at\]|\(at\)|\{at\})\s*([a-z0-9.\-]+)\s*(?:\[dot\]|\(dot\)|\{dot\})\s*([a-z]{2,})", re.I)


def decode_cf(hexstr):
    try:
        b = bytes.fromhex(hexstr)
        return "".join(chr(c ^ b[0]) for c in b[1:])
    except Exception:
        return ""


def deep_harvest(domain):
    rec = {"domain": domain, "emails": [], "linkedIns": [], "scrapedUrls": []}
    pages = []
    base = None
    for scheme in ("https://", "http://"):
        try:
            html, final = fetch = h.fetch(scheme + domain)
            base = fetch[1]
            pages.append(fetch)
            break
        except Exception:
            continue
    if base is None:
        rec["error"] = "homepage_unreachable"
        return rec
    root = base.split("://")[0] + "://" + base.split("://")[1].split("/")[0]

    seen = {pages[0][0]}
    candidates = []
    for href in h.LINK_RE.findall(pages[0][1]):
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue
        if not CONTACT_HINT.search(href):
            continue
        if href.startswith("http") and domain not in href:
            continue
        url = href if href.startswith("http") else root + "/" + href.lstrip("/")
        if url not in seen and not h.IMG_EXT_RE.search(url):
            seen.add(url)
            candidates.append(url)
    for p in COMMON_PATHS:
        url = f"{root}/{p}"
        if url not in seen:
            seen.add(url)
            candidates.append(url)

    fetched = 0
    for url in candidates:
        if fetched >= 5:
            break
        try:
            html, final = h.fetch(url, timeout=12)
            pages.append((final, html))
            fetched += 1
        except Exception:
            pass

    emails, lis = set(), set()
    for final, html in pages:
        rec["scrapedUrls"].append(final)
        emails |= set(h.EMAIL_RE.findall(html))
        for m in re.findall(r'mailto:([^"\'?>]+)', html, re.I):
            emails.add(m)
        for hexstr in CF_RE.findall(html):
            d = decode_cf(hexstr)
            if d:
                emails.add(d)
        for m in AT_RE.findall(html):
            emails.add(f"{m[0]}@{m[1]}.{m[2]}")
        for li in re.findall(r'https?://[a-z]{0,3}\.?linkedin\.com/(?:company|in)/[^"\'\s<>]+', html, re.I):
            lis.add(li.rstrip("/").split("?")[0])
    rec["emails"] = sorted(h.clean_emails(emails, domain))
    rec["linkedIns"] = sorted(lis)[:3]
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains-file", required=True)
    ap.add_argument("--workers", type=int, default=30)
    args = ap.parse_args()

    domains = [d.strip() for d in Path(args.domains_file).read_text().splitlines() if d.strip()]
    cache = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    todo = [d for d in domains if d not in cache]
    print(f"{len(cache)} cached, deep-harvesting {len(todo)} domains", flush=True)

    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(deep_harvest, d): d for d in todo}
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
                print(f"  {done}/{len(todo)} | {hits} with email", flush=True)

    PROGRESS.write_text(json.dumps(cache, ensure_ascii=False))
    hits = sum(1 for v in cache.values() if v.get("emails"))
    print(f"deep pass done: {len(cache)} domains, {hits} with >=1 email", flush=True)

    # merge into the builder's contacts file: replace empty records for these domains
    records = json.loads(OUT.read_text()) if OUT.exists() else []
    by_dom = {r.get("domain"): r for r in records}
    merged = 0
    for d, rec in cache.items():
        if rec.get("emails") and not (by_dom.get(d) or {}).get("emails"):
            by_dom[d] = rec
            merged += 1
    OUT.write_text(json.dumps(list(by_dom.values()), ensure_ascii=False), encoding="utf-8")
    print(f"merged {merged} newly-found domains into {OUT}", flush=True)


if __name__ == "__main__":
    main()
