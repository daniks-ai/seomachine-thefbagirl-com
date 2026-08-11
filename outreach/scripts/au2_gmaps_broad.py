#!/usr/bin/env python3
"""
AU broad-ICP lead source: Google Maps via Apify compass/crawler-google-places.

Second wave for the [AU] campaign after the Amazon-specific niche was
exhausted (~120 leads): digital marketing / ecommerce / Google Ads agencies
across 7 AU cities. They pitch well for white-label Amazon PPC.

One actor run, EN language, budget-guarded against the $5/mo Apify cap.
Raw output -> data/au_gmaps_broad_raw.json (list of place records).

Usage:
    python3 outreach/scripts/au2_gmaps_broad.py --dry-run
    python3 outreach/scripts/au2_gmaps_broad.py
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parents[1] / "data"
ENV = ROOT / "data_sources" / "config" / ".env"
ACTOR = "compass~crawler-google-places"
API = "https://api.apify.com/v2"
OUT = DATA / "au_gmaps_broad_raw.json"

COST_PER_PLACE = 0.004
BUDGET_BUFFER = 0.5

CITIES = ["Sydney, Australia", "Melbourne, Australia", "Brisbane, Australia",
          "Perth, Australia", "Adelaide, Australia", "Gold Coast, Australia",
          "Canberra, Australia"]
QUERIES = ["digital marketing agency", "ecommerce marketing agency",
           "google ads agency"]
MAX_PLACES = 30


def token():
    for line in ENV.read_text().splitlines():
        if line.startswith("APIFY_TOKEN="):
            return line.split("=", 1)[1].strip()
    sys.exit("APIFY_TOKEN not found in .env")


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=120) as r:
        return json.load(r)


def post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def budget_left(tok):
    d = get(f"{API}/users/me/limits?token={tok}")["data"]
    return d["limits"]["maxMonthlyUsageUsd"] - d["current"]["monthlyUsageUsd"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    searches = [f"{q} in {c}" for c in CITIES for q in QUERIES]
    est = len(searches) * MAX_PLACES * COST_PER_PLACE
    print(f"{len(searches)} searches x {MAX_PLACES} places, est ${est:.2f}")
    if args.dry_run:
        return

    tok = token()
    left = budget_left(tok)
    print(f"Apify budget left: ${left:.2f}")
    if left - est < BUDGET_BUFFER:
        sys.exit("not enough Apify budget headroom")

    payload = {
        "searchStringsArray": searches,
        "language": "en",
        "maxCrawledPlacesPerSearch": MAX_PLACES,
        "skipClosedPlaces": True,
        "website": "withWebsite",
        "maxImages": 0,
        "maxReviews": 0,
        "scrapeDirectories": False,
        "maxQuestions": 0,
    }
    run = post(f"{API}/acts/{ACTOR}/runs?token={tok}", payload)["data"]
    rid, dsid = run["id"], run["defaultDatasetId"]
    print(f"runId={rid} datasetId={dsid}")
    while True:
        d = get(f"{API}/actor-runs/{rid}?token={tok}")["data"]
        print(f"  status={d['status']} usage=${d.get('usageTotalUsd', 0):.2f}")
        if d["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
        time.sleep(30)
    items = get(f"{API}/datasets/{dsid}/items?token={tok}&clean=true&format=json")
    OUT.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    print(f"saved {len(items)} places -> {OUT}")


if __name__ == "__main__":
    main()
