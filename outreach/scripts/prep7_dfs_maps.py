#!/usr/bin/env python3
"""
Prep/3PL round 2, volume engine: Google Maps via DataForSEO.

Local prep centers, 3PLs and e-commerce fulfillment warehouses are Maps-native
businesses that never appear in the curated FBA directories — this is where the
remaining volume lives. Cost is ~$0.002 per search (20 places), i.e. ~40x
cheaper than the Apify actor for the same data.

Gotchas honoured (learned on layers 2-3):
- the live/advanced endpoint only reliably runs ONE task per POST, so each
  keyword is its own request (parallelised with a thread pool instead);
- city goes in the keyword, country in `location_name`, so no per-city
  location-database lookups are needed;
- `--retry-empty` re-fetches searches that came back throttled/empty.

Output: outreach/data/prep_r2_gmaps.jsonl  {domain, company, country, region, source}
Resumable cache: _prep_dfs_maps_progress.json

Usage:
    python3 outreach/scripts/prep7_dfs_maps.py --dry-run       # plan + cost, $0
    python3 outreach/scripts/prep7_dfs_maps.py --limit 5       # smoke test
    python3 outreach/scripts/prep7_dfs_maps.py                 # full sweep
    python3 outreach/scripts/prep7_dfs_maps.py --retry-empty
"""
import argparse
import base64
import concurrent.futures as cf
import json
import re
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parents[1] / "data"
ENV = ROOT / "data_sources" / "config" / ".env"
OUT = DATA / "prep_r2_gmaps.jsonl"
PROGRESS = DATA / "_prep_dfs_maps_progress.json"

API = "https://api.dataforseo.com/v3"
COST_PER_SEARCH = 0.002
DEPTH = 20

QUERIES_US = [
    "fba prep center",
    "amazon prep service",
    "3pl fulfillment center",
    "ecommerce fulfillment warehouse",
    "pick and pack fulfillment",
    "order fulfillment service",
]
QUERIES_INTL = [
    "fba prep centre",
    "amazon prep service",
    "3pl fulfilment",
    "ecommerce fulfilment centre",
]

US_CITIES = [
    "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX",
    "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA",
    "Dallas, TX", "Austin, TX", "Jacksonville, FL", "Fort Worth, TX",
    "Columbus, OH", "Charlotte, NC", "Indianapolis, IN", "San Francisco, CA",
    "Seattle, WA", "Denver, CO", "Nashville, TN", "Oklahoma City, OK",
    "Las Vegas, NV", "Portland, OR", "Memphis, TN", "Louisville, KY",
    "Baltimore, MD", "Milwaukee, WI", "Albuquerque, NM", "Tucson, AZ",
    "Fresno, CA", "Sacramento, CA", "Kansas City, MO", "Mesa, AZ",
    "Atlanta, GA", "Omaha, NE", "Colorado Springs, CO", "Raleigh, NC",
    "Virginia Beach, VA", "Long Beach, CA", "Miami, FL", "Oakland, CA",
    "Minneapolis, MN", "Tulsa, OK", "Bakersfield, CA", "Wichita, KS",
    "Arlington, TX", "Aurora, CO", "Tampa, FL", "New Orleans, LA",
    "Cleveland, OH", "Anaheim, CA", "Honolulu, HI", "Riverside, CA",
    "Corpus Christi, TX", "Lexington, KY", "Henderson, NV", "Stockton, CA",
    "Saint Paul, MN", "Cincinnati, OH", "St Louis, MO", "Pittsburgh, PA",
    "Greensboro, NC", "Lincoln, NE", "Anchorage, AK", "Plano, TX",
    "Orlando, FL", "Irvine, CA", "Newark, NJ", "Durham, NC",
    "Chula Vista, CA", "Toledo, OH", "Fort Wayne, IN", "St Petersburg, FL",
    "Laredo, TX", "Jersey City, NJ", "Chandler, AZ", "Madison, WI",
    "Lubbock, TX", "Buffalo, NY", "Reno, NV", "Boise, ID",
    "Spokane, WA", "Richmond, VA", "Salt Lake City, UT", "Des Moines, IA",
    "Grand Rapids, MI", "Little Rock, AR", "Birmingham, AL", "Knoxville, TN",
    "Providence, RI", "Charleston, SC", "Savannah, GA", "Boston, MA",
    "Detroit, MI", "Columbia, SC", "Wilmington, DE", "Bozeman, MT",
    "Billings, MT", "Missoula, MT", "Great Falls, MT", "Kalispell, MT",
    "Manchester, NH", "Nashua, NH", "Portland, ME", "Burlington, VT",
    "Cheyenne, WY", "Fargo, ND", "Sioux Falls, SD", "Boulder, CO",
    "El Paso, TX", "McAllen, TX", "Ontario, CA", "Rancho Cucamonga, CA",
    "Savannah, GA", "Norfolk, VA", "Allentown, PA", "Scranton, PA",
    "Syracuse, NY", "Rochester, NY", "Albany, NY", "Hartford, CT",
    "Springfield, MO", "Fayetteville, AR", "Chattanooga, TN", "Huntsville, AL",
    "Mobile, AL", "Jackson, MS", "Shreveport, LA", "Baton Rouge, LA",
]

INTL = [
    ("United Kingdom", ["London", "Manchester", "Birmingham", "Leeds",
                        "Glasgow", "Bristol", "Liverpool", "Sheffield",
                        "Nottingham", "Southampton"]),
    ("Canada", ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa",
                "Edmonton", "Winnipeg", "Mississauga"]),
    ("Australia", ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"]),
    ("Germany", ["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt"]),
    ("Netherlands", ["Amsterdam", "Rotterdam", "Eindhoven"]),
    ("Poland", ["Warsaw", "Krakow", "Wroclaw", "Gdansk"]),
    ("Spain", ["Madrid", "Barcelona", "Valencia"]),
    ("Italy", ["Milan", "Rome", "Naples"]),
    ("France", ["Paris", "Lyon", "Marseille"]),
    ("Ireland", ["Dublin"]),
    ("Czech Republic", ["Prague"]),
    ("United Arab Emirates", ["Dubai"]),
    ("Mexico", ["Mexico City", "Guadalajara", "Monterrey", "Tijuana"]),
]

COUNTRY_CODE = {
    "United States": "US", "United Kingdom": "GB", "Canada": "CA",
    "Australia": "AU", "Germany": "DE", "Netherlands": "NL", "Poland": "PL",
    "Spain": "ES", "Italy": "IT", "France": "FR", "Ireland": "IE",
    "Czech Republic": "CZ", "United Arab Emirates": "AE", "Mexico": "MX",
}

JUNK = re.compile(
    r"(amazon\.|google\.|facebook|instagram|linkedin|twitter|yelp|"
    r"^ups\.com|fedex|usps\.com|dhl\.|maersk|xpo\.com|chrobinson|jbhunt|"
    r"penske|ryder\.com|uhaul|publicstorage|extraspace|cubesmart|"
    r"indeed|ziprecruiter|glassdoor|craigslist|"
    r"wixsite|wordpress\.com|blogspot|squarespace|godaddysites|"
    r"business\.site|sites\.google|linktr\.ee)", re.I)

_lock = threading.Lock()


def env():
    d = {}
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def auth_header(e):
    tok = base64.b64encode(
        f"{e['DATAFORSEO_LOGIN']}:{e['DATAFORSEO_PASSWORD']}".encode()).decode()
    return "Basic " + tok


def post(endpoint, payload, hdr):
    req = urllib.request.Request(
        API + endpoint, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": hdr, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def balance(hdr):
    req = urllib.request.Request(API + "/appendix/user_data",
                                 headers={"Authorization": hdr})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["tasks"][0]["result"][0]["money"]["balance"]


def build_searches():
    out = []
    for city in US_CITIES:
        for q in QUERIES_US:
            out.append({"key": f"US|{city}|{q}", "keyword": f"{q} {city}",
                        "location_name": "United States", "country": "US",
                        "region": city.split(",")[-1].strip()})
    for country, cities in INTL:
        for city in cities:
            for q in QUERIES_INTL:
                out.append({"key": f"{country}|{city}|{q}",
                            "keyword": f"{q} {city}",
                            "location_name": country,
                            "country": COUNTRY_CODE[country], "region": city})
    # dedupe identical keys (duplicate city entries)
    seen, uniq = set(), []
    for s in out:
        if s["key"] not in seen:
            seen.add(s["key"])
            uniq.append(s)
    return uniq


def map_item(it):
    site = it.get("url") or (f"https://{it['domain']}" if it.get("domain") else "")
    return {"title": it.get("title"), "website": site,
            "category": it.get("category")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--retry-empty", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    searches = build_searches()
    print(f"plan: {len(searches)} searches x {DEPTH} places, "
          f"est ${len(searches)*COST_PER_SEARCH:.2f}")
    if args.dry_run:
        return

    e = env()
    hdr = auth_header(e)
    store = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    if args.retry_empty:
        for k in [k for k, v in store.items() if not v.get("records")]:
            del store[k]
    todo = [s for s in searches if s["key"] not in store]
    if args.limit:
        todo = todo[: args.limit]

    bal = balance(hdr)
    need = len(todo) * COST_PER_SEARCH
    print(f"{len(store)} cached, {len(todo)} to fetch | "
          f"balance ${bal:.2f}, need ~${need:.2f}")
    if need > bal:
        sys.exit(f"insufficient balance: need ${need:.2f}, have ${bal:.2f}")

    done = [0]
    spent = [0.0]

    def run(s):
        try:
            resp = post("/serp/google/maps/live/advanced", [{
                "keyword": s["keyword"], "location_name": s["location_name"],
                "language_code": "en", "depth": DEPTH}], hdr)
            task = (resp.get("tasks") or [{}])[0]
            res = (task.get("result") or [{}])[0] if task.get("result") else {}
            items = res.get("items") or []
            recs = [map_item(it) for it in items if it.get("title")]
            cost = resp.get("cost") or 0.0
        except Exception as ex:
            recs, cost = [], 0.0
            print(f"  FAIL [{s['keyword'][:40]}]: {str(ex)[:50]}")
        with _lock:
            store[s["key"]] = {"country": s["country"], "region": s["region"],
                               "records": recs}
            spent[0] += cost
            done[0] += 1
            if done[0] % 50 == 0:
                PROGRESS.write_text(json.dumps(store, ensure_ascii=False))
                places = sum(len(v["records"]) for v in store.values())
                print(f"  {done[0]}/{len(todo)} searches | {places} places | "
                      f"spent ${spent[0]:.2f}")

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(run, todo))
    PROGRESS.write_text(json.dumps(store, ensure_ascii=False))

    by_dom = {}
    for v in store.values():
        for r in v["records"]:
            site = r.get("website") or ""
            m = re.match(r"https?://([^/\s]+)", site)
            if not m:
                continue
            d = m.group(1).lower().split(":")[0]
            d = d[4:] if d.startswith("www.") else d
            if not d or "." not in d or JUNK.search(d) or d in by_dom:
                continue
            # Amazon-specific prep centers get the prep copy; generic
            # 3PL/fulfillment warehouses get their own segment later.
            blob = f"{r.get('title') or ''} {r.get('category') or ''} {d}".lower()
            kind = "prep" if re.search(r"(\bprep\b|\bfba\b|amazon)", blob) else "3pl"
            by_dom[d] = {"domain": d, "company": r.get("title") or d,
                         "country": v["country"], "region": v["region"],
                         "kind": kind, "source": "google_maps_dfs"}
    with OUT.open("w", encoding="utf-8") as f:
        for r in by_dom.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    total_places = sum(len(v["records"]) for v in store.values())
    print(f"\n{total_places} places cached -> {len(by_dom)} unique business "
          f"domains -> {OUT}")
    print(f"run cost ${spent[0]:.2f}")
    print("next: python3 outreach/scripts/prep4_normalize_r2.py")


if __name__ == "__main__":
    main()
