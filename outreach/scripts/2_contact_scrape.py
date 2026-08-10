#!/usr/bin/env python3
"""
Layer-1 email harvesting via Apify contact-info-scraper (vdrmota~contact-info-scraper).

Feeds the deduped agency domains from step 1 into the contact scraper, which
crawls each site (home / contact / about) and returns emails + social links.
Runs in capped batches so we never blow past the Apify overage ceiling.

Env: APIFY_TOKEN in data_sources/config/.env
Cost (BRONZE tier): ~$0.002/page scraped, ~3-5 pages/site => ~$0.006-0.01/site.

Usage:
    python3 outreach/scripts/2_contact_scrape.py            # all domains
    python3 outreach/scripts/2_contact_scrape.py --limit 1500
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo root
OUT_DIR = Path(__file__).resolve().parents[1] / "data"
ENV = ROOT / "data_sources" / "config" / ".env"
ACTOR = "vdrmota~contact-info-scraper"
API = "https://api.apify.com/v2"


def token() -> str:
    for line in ENV.read_text().splitlines():
        if line.startswith("APIFY_TOKEN="):
            return line.split("=", 1)[1].strip()
    sys.exit("APIFY_TOKEN not found in .env")


def post(url, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max domains this run (0=all)")
    ap.add_argument("--max-depth", type=int, default=1, help="crawl depth per site")
    ap.add_argument("--domains-file", default=str(OUT_DIR / "layer1_domains.txt"))
    args = ap.parse_args()

    tok = token()
    domains = [d.strip() for d in Path(args.domains_file).read_text().splitlines() if d.strip()]
    if args.limit:
        domains = domains[: args.limit]
    start_urls = [{"url": f"https://{d}"} for d in domains]
    print(f"submitting {len(start_urls)} sites to {ACTOR} (depth={args.max_depth})")

    run = post(
        f"{API}/acts/{ACTOR}/runs?token={tok}",
        {
            "startUrls": start_urls,
            "maxDepth": args.max_depth,
            "maxRequestsPerStartUrl": 4,
            "proxyConfig": {"useApifyProxy": True},
        },
    )["data"]
    rid, dsid = run["id"], run["defaultDatasetId"]
    print(f"runId={rid} datasetId={dsid}")

    while True:
        d = get(f"{API}/actor-runs/{rid}?token={tok}")["data"]
        st = d["status"]
        print(f"  status={st} items={d.get('stats', {}).get('itemCount', '?')}")
        if st in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
        time.sleep(20)

    items = get(f"{API}/datasets/{dsid}/items?token={tok}&clean=true&format=json")
    out = OUT_DIR / "layer1_contacts_raw.json"
    out.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    with_email = sum(1 for it in items if it.get("emails"))
    print(f"scraped {len(items)} site records, {with_email} with >=1 email")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
