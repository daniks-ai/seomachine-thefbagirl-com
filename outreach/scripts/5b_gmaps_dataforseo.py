#!/usr/bin/env python3
"""
Layer-2 lead source via DataForSEO Google Maps SERP (no Apify needed).

Same search PLAN as 5_gmaps_scrape.py (~65 cities x localized queries), but runs
through DataForSEO's /v3/serp/google/maps/live/advanced endpoint at ~$0.002 per
search (20 places each) instead of the Apify actor. Google Maps is localized by
putting the city in the keyword and the country as `location_name`, so no
per-city location-database mapping is needed.

Output records use the SAME keys the Apify compass actor produces, written to
layer2_gmaps_raw/gmaps_dfs_<lang>.json, so 6_normalize_layer2.py consumes them
unchanged (it globs gmaps_*.json).

Env: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD in data_sources/config/.env
Resumable: _gmaps_dfs_progress.json caches raw results per search key.

Usage:
    python3 outreach/scripts/5b_gmaps_dataforseo.py --dry-run     # plan + cost, $0
    python3 outreach/scripts/5b_gmaps_dataforseo.py --limit 3     # smoke test, ~$0.006
    python3 outreach/scripts/5b_gmaps_dataforseo.py               # full run (~$0.25)
    python3 outreach/scripts/5b_gmaps_dataforseo.py --only-lang de,fr
"""
import argparse
import base64
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA / "layer2_gmaps_raw"
PROGRESS = DATA / "_gmaps_dfs_progress.json"
ENV = ROOT / "data_sources" / "config" / ".env"
API = "https://api.dataforseo.com/v3"
COST_PER_SEARCH = 0.002
DEPTH = 20
# live/advanced only reliably executes ~1 task per POST array (extra tasks come
# back empty/throttled), so send one keyword per request.
CHUNK = 1

# import the shared search PLAN from the Apify scraper (module name starts w/ digit)
sys.path.insert(0, str(Path(__file__).resolve().parent))
PLAN = __import__("5_gmaps_scrape").PLAN

# country code -> DataForSEO country-level location_name
DFS_LOCATION = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom", "IE": "Ireland",
    "AU": "Australia", "NZ": "New Zealand", "IN": "India", "DE": "Germany",
    "AT": "Austria", "CH": "Switzerland", "FR": "France", "ES": "Spain",
    "IT": "Italy", "NL": "Netherlands", "PL": "Poland", "BR": "Brazil",
    "MX": "Mexico", "AE": "United Arab Emirates", "SA": "Saudi Arabia",
    "SG": "Singapore", "TR": "Turkey", "JP": "Japan",
}


def env():
    d = {}
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def auth_header(e):
    tok = base64.b64encode(f"{e['DATAFORSEO_LOGIN']}:{e['DATAFORSEO_PASSWORD']}".encode()).decode()
    return "Basic " + tok


def post(endpoint, payload, hdr):
    req = urllib.request.Request(
        API + endpoint, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": hdr, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def balance(hdr):
    d = post("/appendix/user_data", [], hdr) if False else None
    req = urllib.request.Request(API + "/appendix/user_data", headers={"Authorization": hdr})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    return d["tasks"][0]["result"][0]["money"]["balance"]


def build_searches(only_lang=None, only_country=None):
    out = []
    for entry in PLAN:
        if only_lang and entry["lang"] not in only_lang:
            continue
        if only_country and entry["country"] not in only_country:
            continue
        loc = DFS_LOCATION.get(entry["country"])
        if not loc:
            print(f"  WARN no DFS location for {entry['country']}, skipping")
            continue
        for city in entry["cities"]:
            for q in entry["queries"]:
                out.append({
                    "key": f"{entry['country']}|{city}|{q}",
                    "keyword": f"{q} {city}",
                    "location_name": loc,
                    "language_code": entry["lang"],
                    "country": entry["country"],
                    "lang": entry["lang"],
                })
    return out


def map_item(it, country, lang):
    ai = it.get("address_info") or {}
    rating = it.get("rating") or {}
    website = it.get("url") or (f"https://{it['domain']}" if it.get("domain") else "")
    cid = it.get("cid")
    return {
        "title": it.get("title"),
        "categoryName": it.get("category"),
        "website": website,
        "countryCode": (ai.get("country_code") or country or "").upper() or None,
        "city": ai.get("city"),
        "address": ai.get("address"),
        "url": f"https://www.google.com/maps?cid={cid}" if cid else None,
        "totalScore": rating.get("value"),
        "reviewsCount": rating.get("votes_count"),
        "_lang": lang,
        "source": "google_maps_dataforseo",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-lang", default="")
    ap.add_argument("--only-country", default="")
    ap.add_argument("--limit", type=int, default=0, help="max NEW searches this run")
    ap.add_argument("--retry-empty", action="store_true",
                    help="re-fetch cached searches that returned 0 places (throttled)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    only_lang = set(args.only_lang.split(",")) if args.only_lang else None
    only_country = set(args.only_country.split(",")) if args.only_country else None
    searches = build_searches(only_lang, only_country)

    est = len(searches) * COST_PER_SEARCH
    langs = sorted({s["lang"] for s in searches})
    print(f"plan: {len(searches)} searches across {len(langs)} languages ({','.join(langs)}), "
          f"est. ${est:.2f} (~$0.002 each, {DEPTH} places/search)")
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
    print(f"{len(store)} cached, {len(todo)} to fetch this run")
    if not todo:
        print("nothing to fetch; rebuilding output files from cache")

    bal = balance(hdr)
    need = len(todo) * COST_PER_SEARCH
    print(f"DataForSEO balance ${bal:.2f}, this run needs ~${need:.2f}")
    if need > bal:
        sys.exit(f"insufficient balance: need ${need:.2f}, have ${bal:.2f}. Top up DataForSEO.")

    spent = 0.0
    for i in range(0, len(todo), CHUNK):
        chunk = todo[i:i + CHUNK]
        payload = [{"keyword": s["keyword"], "location_name": s["location_name"],
                    "language_code": s["language_code"], "depth": DEPTH} for s in chunk]
        resp = post("/serp/google/maps/live/advanced", payload, hdr)
        spent += resp.get("cost") or 0.0
        tasks = resp.get("tasks") or []
        for s, task in zip(chunk, tasks):
            res = (task.get("result") or [{}])[0] if task.get("result") else {}
            items = res.get("items") or []
            recs = [map_item(it, s["country"], s["lang"]) for it in items
                    if (it.get("type") in (None, "maps_search") or it.get("title"))]
            store[s["key"]] = {"lang": s["lang"], "records": recs}
        PROGRESS.write_text(json.dumps(store, ensure_ascii=False))
        got = sum(len(v["records"]) for v in store.values())
        print(f"  {min(i+CHUNK, len(todo))}/{len(todo)} searches | {got} places cached | spent ${spent:.3f}")

    # rebuild per-language raw files from the full cache
    RAW_DIR.mkdir(exist_ok=True)
    by_lang = {}
    for v in store.values():
        by_lang.setdefault(v["lang"], []).extend(v["records"])
    for lang, recs in sorted(by_lang.items()):
        out = RAW_DIR / f"gmaps_dfs_{lang}.json"
        out.write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
    total = sum(len(r) for r in by_lang.values())
    print(f"wrote {len(by_lang)} raw files, {total} total place records to {RAW_DIR}")
    print(f"run cost ${spent:.3f}. Next: python3 outreach/scripts/6_normalize_layer2.py")


if __name__ == "__main__":
    main()
