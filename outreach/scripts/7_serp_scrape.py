#!/usr/bin/env python3
"""
Layer-3 lead source: Google SERP domains via Apify apify/google-search-scraper.

Runs localized "amazon ppc agency"-style queries per country (each country =
one actor run so it gets the right geo + language), and saves the organic
results per batch (resumable). Same budget-headroom guard as layer 2: it refuses
to submit a batch unless the Apify account has enough room under its
Max-monthly-usage cap.

SERP is the widest, cheapest layer — it surfaces agencies that never registered
in the Amazon partner directory or on Google Maps, plus long-tail / boutique
shops. It also surfaces a lot of directories and listicles, which the layer-3
normalizer (8_normalize_layer3.py) filters out.

Env: APIFY_TOKEN in data_sources/config/.env

Cost model: apify/google-search-scraper bills per result (~$0.0035/organic
result incl. Apify margin). Default plan = ~110 queries x 2 pages x 10 results
=> ~2,200 results ~= $8-15.

Usage:
    python3 outreach/scripts/7_serp_scrape.py --dry-run          # print plan + cost, no spend
    python3 outreach/scripts/7_serp_scrape.py                    # run all country batches
    python3 outreach/scripts/7_serp_scrape.py --only-country US,GB,DE
    python3 outreach/scripts/7_serp_scrape.py --pages 3          # deeper SERP (more cost)
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA / "layer3_serp_raw"
PROGRESS = DATA / "_serp_progress.json"
ENV = ROOT / "data_sources" / "config" / ".env"
ACTOR = "apify~google-search-scraper"
API = "https://api.apify.com/v2"

COST_PER_RESULT = 0.0035  # conservative BRONZE-tier per-result estimate
RESULTS_PER_PAGE = 10     # actor returns Google's standard ~10 organic/page
BUDGET_BUFFER = 1.0       # keep at least this many $ unspent

# Localized agency-intent query sets, reused across countries that share a
# language. SERP rewards long-tail, so these are broader than the Maps queries.
Q = {
    "en": ["amazon ppc agency", "amazon marketing agency", "amazon advertising agency",
           "amazon ppc management agency", "amazon fba agency", "amazon dsp agency",
           "amazon seller agency"],
    "de": ["amazon agentur", "amazon ppc agentur", "amazon marketing agentur",
           "amazon werbeagentur", "amazon seo agentur"],
    "fr": ["agence amazon", "agence amazon ppc", "agence marketing amazon",
           "agence publicité amazon"],
    "es": ["agencia amazon", "agencia amazon ppc", "agencia publicidad amazon",
           "consultoría amazon"],
    "it": ["agenzia amazon", "agenzia amazon ppc", "agenzia marketing amazon"],
    "pt": ["agência amazon", "consultoria amazon fba", "agência marketing amazon"],
    "nl": ["amazon marketing bureau", "amazon reclamebureau", "amazon agency"],
    "pl": ["agencja amazon", "agencja marketingowa amazon", "amazon agency"],
    "tr": ["amazon ajansı", "amazon reklam ajansı", "amazon danışmanlık"],
    "ja": ["amazon 運用代行", "amazon 広告代理店", "amazon コンサルティング"],
}

# One entry per country → one actor run. `country` (ISO2 upper) flows into the
# normalizer so 3_build_instantly_csv.py segments it correctly. `cc` is the
# actor's countryCode (lower); `lang` is the actor's languageCode + the Q key.
PLAN = [
    {"country": "US", "cc": "us", "lang": "en"},
    {"country": "CA", "cc": "ca", "lang": "en"},
    {"country": "GB", "cc": "gb", "lang": "en"},
    {"country": "IE", "cc": "ie", "lang": "en"},
    {"country": "AU", "cc": "au", "lang": "en"},
    {"country": "NZ", "cc": "nz", "lang": "en"},
    {"country": "SG", "cc": "sg", "lang": "en"},
    {"country": "IN", "cc": "in", "lang": "en"},
    {"country": "AE", "cc": "ae", "lang": "en"},
    {"country": "SA", "cc": "sa", "lang": "en"},
    {"country": "DE", "cc": "de", "lang": "de"},
    {"country": "AT", "cc": "at", "lang": "de"},
    {"country": "CH", "cc": "ch", "lang": "de"},
    {"country": "FR", "cc": "fr", "lang": "fr"},
    {"country": "ES", "cc": "es", "lang": "es"},
    {"country": "MX", "cc": "mx", "lang": "es"},
    {"country": "BR", "cc": "br", "lang": "pt"},
    {"country": "IT", "cc": "it", "lang": "it"},
    {"country": "NL", "cc": "nl", "lang": "nl"},
    {"country": "PL", "cc": "pl", "lang": "pl"},
    {"country": "TR", "cc": "tr", "lang": "tr"},
    {"country": "JP", "cc": "jp", "lang": "ja"},
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


def build_batches(only_country=None):
    batches = []
    for e in PLAN:
        if only_country and e["country"] not in only_country:
            continue
        queries = Q.get(e["lang"])
        if not queries:
            print(f"  WARN: no query set for lang={e['lang']} ({e['country']}), skipping")
            continue
        batches.append({**e, "queries": queries})
    return batches


def run_batch(tok, batch, pages):
    payload = {
        "queries": "\n".join(batch["queries"]),
        "countryCode": batch["cc"],
        "languageCode": batch["lang"],
        "maxPagesPerQuery": pages,
        "mobileResults": False,
        "saveHtml": False,
        "saveHtmlToKeyValueStore": False,
        "includeUnfilteredResults": False,
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
        time.sleep(20)
    items = get(f"{API}/datasets/{dsid}/items?token={tok}&clean=true&format=json")
    return items, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=2, help="SERP pages per query")
    ap.add_argument("--only-country", default="", help="comma list, e.g. US,GB,DE")
    ap.add_argument("--dry-run", action="store_true", help="print plan + cost estimate only")
    args = ap.parse_args()

    only_country = set(args.only_country.split(",")) if args.only_country else None
    batches = build_batches(only_country)

    total_queries = sum(len(b["queries"]) for b in batches)
    est_results = total_queries * args.pages * RESULTS_PER_PAGE
    est_cost = est_results * COST_PER_RESULT
    print(f"plan: {len(batches)} country runs, {total_queries} queries, "
          f"<= {est_results} results, est. <= ${est_cost:.0f}")
    for b in batches:
        print(f"  {b['country']} [{b['lang']}] {len(b['queries'])} queries")
    if args.dry_run:
        return

    tok = token()
    RAW_DIR.mkdir(exist_ok=True)
    progress = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}

    for b in batches:
        key = b["country"]
        if progress.get(key) == "done":
            print(f"[{key}] already done, skipping")
            continue
        batch_est = len(b["queries"]) * args.pages * RESULTS_PER_PAGE * COST_PER_RESULT
        left = budget_left(tok)
        print(f"[{key}] {len(b['queries'])} queries, est ${batch_est:.1f}, budget left ${left:.1f}")
        if left - batch_est < BUDGET_BUFFER:
            print(f"[{key}] SKIPPED — not enough Apify budget headroom. "
                  f"Raise Max monthly usage in Apify Console > Billing > Limits, then re-run "
                  f"(progress is saved, finished batches won't re-run).")
            continue
        items, st = run_batch(tok, b, args.pages)
        out = RAW_DIR / f"serp_{key}_{b['lang']}.json"
        out.write_text(json.dumps(
            {"country": b["country"], "lang": b["lang"], "items": items},
            ensure_ascii=False), encoding="utf-8")
        print(f"[{key}] {st}: {len(items)} SERP items -> {out}")
        if st == "SUCCEEDED":
            progress[key] = "done"
            PROGRESS.write_text(json.dumps(progress))

    print("all batches processed. Next: python3 outreach/scripts/8_normalize_layer3.py")


if __name__ == "__main__":
    main()
