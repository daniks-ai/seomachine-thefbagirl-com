#!/usr/bin/env python3
"""
Layer-2 lead source: Google Maps via Apify compass/crawler-google-places.

Searches "amazon ppc agency"-style queries (localized) across ~65 cities in the
markets our Instantly segments cover. Runs in per-language batches so the actor
gets the right `language` param, saves raw output per batch (resumable), and
refuses to submit a batch if the Apify account doesn't have enough headroom
under its Max-monthly-usage cap.

Env: APIFY_TOKEN in data_sources/config/.env

Cost model (BRONZE): ~$0.004/place scraped + actor runtime overhead.
Default config = ~126 searches x 20 places cap = <=2,520 places ~= $12-25.

Usage:
    python3 outreach/scripts/5_gmaps_scrape.py --dry-run     # print plan + cost, no spend
    python3 outreach/scripts/5_gmaps_scrape.py               # run all batches
    python3 outreach/scripts/5_gmaps_scrape.py --only-lang de,fr
    python3 outreach/scripts/5_gmaps_scrape.py --max-places 15
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA / "layer2_gmaps_raw"
PROGRESS = DATA / "_gmaps_progress.json"
ENV = ROOT / "data_sources" / "config" / ".env"
ACTOR = "compass~crawler-google-places"
API = "https://api.apify.com/v2"

COST_PER_PLACE = 0.004   # rough BRONZE-tier estimate incl. overhead
BUDGET_BUFFER = 1.0      # keep at least this many $ unspent

# Search plan: one entry per country. Each city is combined with each query as
# "<query> in <city>". Grouped into batches by `lang` (actor language param).
PLAN = [
    {"country": "US", "lang": "en", "queries": ["amazon ppc agency", "amazon marketing agency"],
     "cities": ["New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Miami, FL",
                "Dallas, TX", "Austin, TX", "Seattle, WA", "San Francisco, CA", "San Diego, CA",
                "Atlanta, GA", "Boston, MA", "Denver, CO", "Phoenix, AZ", "Philadelphia, PA"]},
    {"country": "CA", "lang": "en", "queries": ["amazon ppc agency", "amazon marketing agency"],
     "cities": ["Toronto, Canada", "Vancouver, Canada", "Montreal, Canada"]},
    {"country": "GB", "lang": "en", "queries": ["amazon ppc agency", "amazon marketing agency"],
     "cities": ["London, UK", "Manchester, UK", "Birmingham, UK", "Leeds, UK"]},
    {"country": "IE", "lang": "en", "queries": ["amazon ppc agency", "amazon marketing agency"],
     "cities": ["Dublin, Ireland"]},
    {"country": "AU", "lang": "en", "queries": ["amazon ppc agency", "amazon marketing agency"],
     "cities": ["Sydney, Australia", "Melbourne, Australia", "Brisbane, Australia"]},
    {"country": "NZ", "lang": "en", "queries": ["amazon marketing agency"],
     "cities": ["Auckland, New Zealand"]},
    {"country": "IN", "lang": "en", "queries": ["amazon ppc agency", "amazon marketing agency"],
     "cities": ["Delhi, India", "Mumbai, India", "Bangalore, India", "Hyderabad, India",
                "Ahmedabad, India", "Jaipur, India", "Surat, India", "Pune, India"]},
    {"country": "DE", "lang": "de", "queries": ["amazon agentur", "amazon ppc agentur"],
     "cities": ["Berlin, Deutschland", "Hamburg, Deutschland", "München, Deutschland",
                "Köln, Deutschland", "Frankfurt am Main, Deutschland"]},
    {"country": "AT", "lang": "de", "queries": ["amazon agentur", "amazon marketing agentur"],
     "cities": ["Wien, Österreich"]},
    {"country": "CH", "lang": "de", "queries": ["amazon agentur", "amazon marketing agentur"],
     "cities": ["Zürich, Schweiz"]},
    {"country": "FR", "lang": "fr", "queries": ["agence amazon", "agence amazon ppc"],
     "cities": ["Paris, France", "Lyon, France", "Marseille, France"]},
    {"country": "ES", "lang": "es", "queries": ["agencia amazon", "agencia amazon ppc"],
     "cities": ["Madrid, España", "Barcelona, España", "Valencia, España"]},
    {"country": "IT", "lang": "it", "queries": ["agenzia amazon", "agenzia amazon ppc"],
     "cities": ["Milano, Italia", "Roma, Italia"]},
    {"country": "NL", "lang": "nl", "queries": ["amazon marketing bureau", "amazon agency"],
     "cities": ["Amsterdam, Nederland", "Rotterdam, Nederland"]},
    {"country": "PL", "lang": "pl", "queries": ["agencja amazon", "amazon agency"],
     "cities": ["Warszawa, Polska"]},
    {"country": "BR", "lang": "pt", "queries": ["agência amazon", "consultoria amazon fba"],
     "cities": ["São Paulo, Brasil", "Rio de Janeiro, Brasil"]},
    {"country": "MX", "lang": "es", "queries": ["agencia amazon", "consultoría amazon"],
     "cities": ["Ciudad de México, México", "Guadalajara, México", "Monterrey, México"]},
    {"country": "AE", "lang": "en", "queries": ["amazon ppc agency", "amazon marketing agency"],
     "cities": ["Dubai, UAE", "Abu Dhabi, UAE"]},
    {"country": "SA", "lang": "en", "queries": ["amazon ppc agency", "amazon marketing agency"],
     "cities": ["Riyadh, Saudi Arabia"]},
    {"country": "SG", "lang": "en", "queries": ["amazon ppc agency", "amazon marketing agency"],
     "cities": ["Singapore"]},
    {"country": "TR", "lang": "tr", "queries": ["amazon ajansı", "amazon danışmanlık"],
     "cities": ["İstanbul, Türkiye"]},
    {"country": "JP", "lang": "ja", "queries": ["amazon 運用代行", "amazon コンサルティング"],
     "cities": ["東京, 日本"]},
]


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


def budget_left(tok) -> float:
    d = get(f"{API}/users/me/limits?token={tok}")["data"]
    used = d["current"]["monthlyUsageUsd"]
    cap = d["limits"]["maxMonthlyUsageUsd"]
    return cap - used


def build_batches(only_lang=None, only_country=None):
    """Group PLAN entries by language; each batch = one actor run."""
    batches = {}
    for entry in PLAN:
        if only_lang and entry["lang"] not in only_lang:
            continue
        if only_country and entry["country"] not in only_country:
            continue
        b = batches.setdefault(entry["lang"], {"lang": entry["lang"], "searches": []})
        for city in entry["cities"]:
            for q in entry["queries"]:
                b["searches"].append({
                    "search": f"{q} in {city}",
                    "country": entry["country"],
                })
    return [batches[k] for k in sorted(batches)]


def run_batch(tok, batch, max_places):
    payload = {
        "searchStringsArray": [s["search"] for s in batch["searches"]],
        "language": batch["lang"],
        "maxCrawledPlacesPerSearch": max_places,
        "skipClosedPlaces": True,
        "website": "withWebsite",
        "maxImages": 0,
        "maxReviews": 0,
        "scrapeDirectories": False,
        "maxQuestions": 0,
    }
    run = post(f"{API}/acts/{ACTOR}/runs?token={tok}", payload)["data"]
    rid, dsid = run["id"], run["defaultDatasetId"]
    print(f"  runId={rid} datasetId={dsid}")
    while True:
        d = get(f"{API}/actor-runs/{rid}?token={tok}")["data"]
        st = d["status"]
        print(f"  status={st} usage=${d.get('usageTotalUsd', 0):.2f}")
        if st in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
        time.sleep(30)
    items = get(f"{API}/datasets/{dsid}/items?token={tok}&clean=true&format=json")
    return items, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-places", type=int, default=20, help="cap per search string")
    ap.add_argument("--only-lang", default="", help="comma list, e.g. de,fr")
    ap.add_argument("--only-country", default="", help="comma list, e.g. US,GB")
    ap.add_argument("--dry-run", action="store_true", help="print plan + cost estimate only")
    args = ap.parse_args()

    only_lang = set(args.only_lang.split(",")) if args.only_lang else None
    only_country = set(args.only_country.split(",")) if args.only_country else None
    batches = build_batches(only_lang, only_country)

    total_searches = sum(len(b["searches"]) for b in batches)
    est_cost = total_searches * args.max_places * COST_PER_PLACE
    print(f"plan: {len(batches)} language batches, {total_searches} searches, "
          f"<= {total_searches * args.max_places} places, est. <= ${est_cost:.0f}")
    for b in batches:
        print(f"  [{b['lang']}] {len(b['searches'])} searches")
    if args.dry_run:
        return

    tok = token()
    RAW_DIR.mkdir(exist_ok=True)
    progress = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}

    for b in batches:
        key = b["lang"]
        if progress.get(key) == "done":
            print(f"[{key}] already done, skipping")
            continue
        batch_est = len(b["searches"]) * args.max_places * COST_PER_PLACE
        left = budget_left(tok)
        print(f"[{key}] {len(b['searches'])} searches, est ${batch_est:.1f}, budget left ${left:.1f}")
        if left - batch_est < BUDGET_BUFFER:
            print(f"[{key}] SKIPPED — not enough Apify budget headroom. "
                  f"Raise Max monthly usage in Apify Console > Billing > Limits, then re-run "
                  f"(progress is saved, finished batches won't re-run).")
            continue
        items, st = run_batch(tok, b, args.max_places)
        out = RAW_DIR / f"gmaps_{key}.json"
        out.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
        print(f"[{key}] {st}: {len(items)} places -> {out}")
        if st == "SUCCEEDED":
            progress[key] = "done"
            PROGRESS.write_text(json.dumps(progress))

    print("all batches processed. Next: python3 outreach/scripts/6_normalize_layer2.py")


if __name__ == "__main__":
    main()
