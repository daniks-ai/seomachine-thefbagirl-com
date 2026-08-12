#!/usr/bin/env python3
"""
Prep-center round 2, volume source: DuckDuckGo HTML SERP (free, no API key).

Runs localized queries ("fba prep center <state>", "ecommerce fulfillment
center <city>", ...) against html.duckduckgo.com, decodes the /l/?uddg=
redirect links, and collects business domains. Single-threaded with a polite
delay; resumable via _prep_ddg_progress.json.

Output: outreach/data/prep_r2_ddg.jsonl  {domain, country, region, source}

Usage:
    python3 outreach/scripts/prep3_ddg_serp.py --dry-run
    python3 outreach/scripts/prep3_ddg_serp.py
    python3 outreach/scripts/prep3_ddg_serp.py --limit 20   # smoke test
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

DATA = Path(__file__).resolve().parents[1] / "data"
OUT = DATA / "prep_r2_ddg.jsonl"
PROGRESS = DATA / "_prep_ddg_progress.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

US_STATES = ["Alabama", "Alaska", "Arizona", "Arkansas", "California",
    "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine",
    "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "South Carolina", "Tennessee", "Texas", "Utah", "Virginia",
    "Washington", "Wisconsin", "Wyoming"]
US_CITIES = ["Los Angeles", "Houston", "Chicago", "Phoenix", "Dallas",
    "Miami", "Atlanta", "Columbus", "Charlotte", "Indianapolis", "Seattle",
    "Denver", "Nashville", "Memphis", "Louisville", "Las Vegas", "Kansas City",
    "Salt Lake City", "Sacramento", "St Louis", "Tampa", "Cincinnati",
    "Cleveland", "Pittsburgh", "Reno"]

PLAN = (
    [("fba prep center %s" % s, "US", s) for s in US_STATES] +
    [("amazon prep center %s" % s, "US", s) for s in US_STATES] +
    [("amazon fba prep and ship %s" % s, "US", s) for s in
     ["Montana", "Delaware", "Oregon", "New Hampshire", "Florida", "Texas"]] +
    [("ecommerce fulfillment center %s" % c, "US", c) for c in US_CITIES] +
    [("3pl fulfillment for amazon sellers %s" % c, "US", c) for c in US_CITIES] +
    [("fba prep centre %s" % c, "GB", c) for c in
     ["UK", "London", "Manchester", "Birmingham", "Leeds", "Scotland"]] +
    [("amazon fulfilment centre 3pl UK", "GB", "UK"),
     ("fba prep center Canada", "CA", ""),
     ("fba prep center Toronto", "CA", "Toronto"),
     ("fba prep center Vancouver", "CA", "Vancouver"),
     ("fba prep center Australia", "AU", ""),
     ("fba prep center Germany", "DE", ""),
     ("fba prep center Netherlands", "NL", ""),
     ("fba prep center Poland", "PL", ""),
     ("fba prep center Spain", "ES", ""),
     ("fba prep center Italy", "IT", ""),
     ("fba prep center France", "FR", ""),
     ("fba prep center Mexico", "MX", ""),
     ("fba prep center UAE", "AE", ""),
     ("fba prep center Czech", "CZ", "")]
)

JUNK = re.compile(
    r"(duckduckgo|selleressentials|shiphype|rocketsource|hopstack|prepcenter\.com|"
    r"reddit|quora|youtube|facebook|linkedin|twitter|instagram|tiktok|pinterest|"
    r"amazon\.|alibaba|aliexpress|fiverr|upwork|freeup|clutch\.co|designrush|"
    r"sortlist|g2\.com|capterra|trustpilot|yelp\.|bbb\.org|yellowpages|thomasnet|"
    r"glassdoor|indeed|ziprecruiter|medium\.com|substack|wikipedia|wikihow|"
    r"junglescout|helium10|sellerapp|repricer|tactical|ecomcrew|"
    r"webretailer|ecommercebytes|fulfillmentcompanies\.net|warehousingandfulfillment\.com|"
    r"sermondo|godaddy|wixsite|wix\.com|wordpress\.com|blogspot|shopify|"
    r"google\.|bing\.|apple\.|microsoft|youtu\.be|vimeo|eventbrite|"
    r"forbes|entrepreneur\.com|inc\.com|businessinsider|nerdwallet)", re.I)


def fetch_serp(q):
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html",
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
            if host and not JUNK.search(host) and "." in host:
                out.append(host)
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.5)
    args = ap.parse_args()

    print(f"plan: {len(PLAN)} queries")
    if args.dry_run:
        return

    store = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    todo = [(q, c, r) for q, c, r in PLAN if q not in store]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(store)} cached, {len(todo)} to fetch")

    fails = 0
    for i, (q, country, region) in enumerate(todo):
        try:
            html = fetch_serp(q)
            doms = parse_domains(html)
            store[q] = {"country": country, "region": region, "domains": doms}
            fails = 0
        except Exception as e:
            print(f"  FAIL [{q}]: {str(e)[:60]}")
            fails += 1
            if fails >= 5:
                print("5 consecutive failures — rate limited, stopping early")
                break
            time.sleep(20)
            continue
        if (i + 1) % 20 == 0:
            uniq = {d for v in store.values() for d in v["domains"]}
            print(f"  {i+1}/{len(todo)} queries | {len(uniq)} unique domains")
            PROGRESS.write_text(json.dumps(store))
        time.sleep(args.delay + random.uniform(0, 1.2))

    PROGRESS.write_text(json.dumps(store))

    # first query that saw the domain wins (its geo hint)
    seen = {}
    for q, v in store.items():
        for d in v["domains"]:
            if d not in seen:
                seen[d] = {"domain": d, "country": v["country"],
                           "region": v["region"], "source": "ddg_serp"}
    with OUT.open("w", encoding="utf-8") as f:
        for rec in seen.values():
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"wrote {len(seen)} unique domains to {OUT}")


if __name__ == "__main__":
    main()
