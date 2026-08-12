#!/usr/bin/env python3
"""
Prep/3PL round 2, Google Maps via Apify (compass/crawler-google-places).

Local FBA prep centers and 3PLs are Maps-native businesses that never show up
in the curated directories, so this is the densest remaining source. Runs a
tight, budget-capped sweep: refuses to start if the Apify monthly-usage
headroom can't cover the requested place count.

Output: outreach/data/prep_r2_gmaps.jsonl  {domain, company, country, region, source}

Usage:
    python3 outreach/scripts/prep6_gmaps.py --dry-run
    python3 outreach/scripts/prep6_gmaps.py --max-places 300
"""
import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parents[1] / "data"
ENV = ROOT / "data_sources" / "config" / ".env"
OUT = DATA / "prep_r2_gmaps.jsonl"
RAW = DATA / "prep_r2_gmaps_raw.json"

ACTOR = "compass~crawler-google-places"
API = "https://api.apify.com/v2"
COST_PER_PLACE = 0.004
BUDGET_BUFFER = 0.15

QUERIES = [
    "fba prep center", "amazon prep service", "3pl fulfillment center",
    "ecommerce fulfillment warehouse",
]
CITIES = [
    "Los Angeles, CA", "Dallas, TX", "Chicago, IL", "Miami, FL",
    "Atlanta, GA", "New York, NY", "Phoenix, AZ", "Seattle, WA",
    "Columbus, OH", "Las Vegas, NV", "Wilmington, DE", "Bozeman, MT",
    "Toronto, Canada", "London, UK", "Manchester, UK",
]

JUNK = re.compile(
    r"(amazon\.|google\.|facebook|instagram|linkedin|twitter|yelp|"
    r"ups\.com|fedex|usps|dhl\.|maersk|xpo\.com|chrobinson|jbhunt|"
    r"wixsite|wordpress\.com|blogspot|squarespace|godaddysites|"
    r"business\.site|sites\.google)", re.I)


def token():
    for line in ENV.read_text().splitlines():
        if line.startswith("APIFY_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("APIFY_TOKEN missing")


def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.loads(r.read())


def post(url, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def headroom(tok):
    d = get(f"{API}/users/me/limits?token={tok}")["data"]
    return d["limits"]["maxMonthlyUsageUsd"] - d["current"]["monthlyUsageUsd"]


def domain_of(url):
    if not url:
        return ""
    m = re.match(r"https?://([^/\s]+)", url.strip())
    if not m:
        return ""
    d = m.group(1).lower().split(":")[0]
    return d[4:] if d.startswith("www.") else d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-places", type=int, default=300)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    searches = [f"{q} in {c}" for c in CITIES for q in QUERIES]
    per_search = max(1, args.max_places // len(searches))
    est = args.max_places * COST_PER_PLACE
    print(f"plan: {len(searches)} searches x {per_search} places "
          f"= {len(searches)*per_search} places, est ${len(searches)*per_search*COST_PER_PLACE:.2f}")
    if args.dry_run:
        return

    tok = token()
    left = headroom(tok)
    print(f"Apify headroom ${left:.2f}, this run needs ~${est:.2f}")
    if est > left - BUDGET_BUFFER:
        raise SystemExit(f"not enough headroom: need ${est:.2f}, have ${left:.2f}")

    run = post(f"{API}/acts/{ACTOR}/runs?token={tok}", {
        "searchStringsArray": searches,
        "maxCrawledPlacesPerSearch": per_search,
        "language": "en",
        "skipClosedPlaces": True,
        "scrapePlaceDetailPage": False,
    })["data"]
    rid = run["id"]
    print(f"run {rid} started; polling…")
    while True:
        time.sleep(20)
        st = get(f"{API}/actor-runs/{rid}?token={tok}")["data"]
        print(f"  status={st['status']} usage=${st.get('usageTotalUsd', 0):.2f}")
        if st["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
    items = get(f"{API}/actor-runs/{rid}/dataset/items?token={tok}&clean=true")
    RAW.write_text(json.dumps(items, ensure_ascii=False))
    print(f"{len(items)} raw places -> {RAW}")

    seen, recs = set(), []
    for it in items:
        dom = domain_of(it.get("website") or "")
        if not dom or dom in seen or JUNK.search(dom):
            continue
        seen.add(dom)
        cc = (it.get("countryCode") or "US").upper()
        recs.append({"domain": dom, "company": it.get("title") or dom,
                     "country": cc, "region": it.get("state") or it.get("city") or "",
                     "source": "google_maps"})
    with OUT.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(recs)} unique business domains -> {OUT}")


if __name__ == "__main__":
    main()
