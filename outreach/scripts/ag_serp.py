#!/usr/bin/env python3
"""
Agency-domain SERP harvester (free) — layer 6.

Runs localized agency queries against Bing HTML SERP (DDG rate-limits harder),
parses organic result domains, filters directories/junk, dedupes. ~10-25
domains per query, so this scales far better than one-domain-per-page directory
scraping. Resumable via _ag_serp_progress.json.

Output: outreach/data/layer6_serp.jsonl  {domain, country, region, source}

Usage:
    python3 outreach/scripts/ag_serp.py --dry-run
    python3 outreach/scripts/ag_serp.py --limit 5
    python3 outreach/scripts/ag_serp.py
"""
import argparse
import json
import random
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib
ddg = importlib.import_module("prep3_ddg_serp")

DATA = Path(__file__).resolve().parents[1] / "data"
OUT = DATA / "layer6_serp.jsonl"
PROGRESS = DATA / "_ag_serp_progress.json"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# extra junk beyond ddg.JUNK: SaaS tools, marketplaces, big non-agency brands
EXTRA_JUNK = re.compile(
    r"(semrush|ahrefs|moz\.com|hubspot|mailchimp|shopify|bigcommerce|woocommerce|"
    r"wix\.|squarespace|godaddy|namecheap|cloudflare|wordpress|weebly|"
    r"tripadvisor|glassdoor|crunchbase|owler|zoominfo|apollo\.io|"
    r"gov|\.edu|coursera|udemy|skillshare|hootsuite|later\.com|buffer\.com|"
    r"canva|adobe|salesforce|zendesk|intercom|calendly|typeform|"
    r"nytimes|wsj\.com|cnn|bbc|theguardian|techcrunch|mashable|"
    r"expertise\.com|upcity|themanifest|goodfirms|semfirms|agencyspotter|"
    r"builtwith|similarweb|statista|ibisworld|glassdollar)", re.I)

CITIES = ddg.US_CITIES + [
    "San Diego", "San Jose", "Austin", "Jacksonville", "Columbus", "Charlotte",
    "Indianapolis", "Seattle", "Denver", "Boston", "Nashville", "Portland",
    "Las Vegas", "Detroit", "Memphis", "Louisville", "Milwaukee", "Atlanta",
    "Miami", "Tampa", "Orlando", "Minneapolis", "Cleveland", "Pittsburgh",
    "Cincinnati", "Kansas City", "Salt Lake City", "Raleigh", "Richmond",
    "Sacramento", "Brooklyn", "Scottsdale", "Irvine",
]
CITIES = list(dict.fromkeys(CITIES))  # dedupe, keep order

# query templates × geo. Agency-intent terms tuned to the white-label offer.
TEMPLATES = [
    "amazon ppc agency %s",
    "amazon advertising agency %s",
    "amazon marketing agency %s",
    "ecommerce marketing agency %s",
    "amazon fba agency %s",
    "ppc management agency %s",
    "amazon seller consultant %s",
    "digital marketing agency for ecommerce %s",
]

# a few nationwide (no-geo) niche queries to catch specialists directories miss
NATIONWIDE = [
    "amazon ppc management agency", "amazon dsp advertising agency",
    "walmart ppc agency", "amazon advertising consultancy",
    "white label amazon ppc", "amazon account management agency",
    "sponsored products management agency", "amazon growth agency",
]

PLAN = (
    [(t % c, "US", c) for c in CITIES for t in TEMPLATES] +
    [(q, "US", "") for q in NATIONWIDE]
)


def fetch_serp(q):
    # Bing now serves a Cloudflare challenge; DuckDuckGo HTML still works.
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={
        "User-Agent": ddg.UA, "Accept": "text/html",
        "Referer": "https://html.duckduckgo.com/"})
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def parse_domains(html):
    out = []
    for m in re.finditer(r'uddg=([^&"\']+)', html):
        try:
            url = urllib.parse.unquote(m.group(1))
            host = urllib.parse.urlparse(url).netloc.lower()
            host = host[4:] if host.startswith("www.") else host
            if (host and "." in host and not ddg.JUNK.search(host)
                    and not EXTRA_JUNK.search(host)):
                out.append(host)
        except Exception:
            pass
    return list(dict.fromkeys(out))  # dedupe within a query, keep order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.8)
    args = ap.parse_args()

    print(f"plan: {len(PLAN)} queries ({len(CITIES)} cities x {len(TEMPLATES)} templates + {len(NATIONWIDE)} nationwide)")
    if args.dry_run:
        for q, c, r in PLAN[:8]:
            print("  ", q)
        return

    store = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    todo = [(q, c, r) for q, c, r in PLAN if q not in store]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(store)} cached, {len(todo)} to fetch")

    empties = 0
    for i, (q, country, region) in enumerate(todo):
        try:
            doms = parse_domains(fetch_serp(q))
        except Exception as e:
            print(f"  FAIL [{q}]: {str(e)[:50]} — cooldown", flush=True)
            time.sleep(45)
            continue
        store[q] = {"country": country, "region": region, "domains": doms}
        # DDG throttles to 0 results when hit too fast; back off hard on empties
        if not doms:
            empties += 1
            time.sleep(40 + random.uniform(0, 20))
            if empties % 6 == 0:
                print(f"  {empties} empties — long cooldown", flush=True)
                time.sleep(90)
        else:
            empties = 0
            time.sleep(args.delay + random.uniform(0, 4))
        if (i + 1) % 15 == 0:
            uniq = {d for v in store.values() for d in v["domains"]}
            print(f"  {i+1}/{len(todo)} | {len(uniq)} unique domains", flush=True)
            PROGRESS.write_text(json.dumps(store))

    PROGRESS.write_text(json.dumps(store))
    seen = {}
    for q, v in store.items():
        for d in v["domains"]:
            if d not in seen:
                seen[d] = {"domain": d, "country": v["country"],
                           "region": v["region"], "source": "bing_serp"}
    with OUT.open("w", encoding="utf-8") as f:
        for rec in seen.values():
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"wrote {len(seen)} unique domains to {OUT}", flush=True)


if __name__ == "__main__":
    main()
