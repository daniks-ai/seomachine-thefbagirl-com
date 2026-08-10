#!/usr/bin/env python3
"""
Layer-3 lead source via DataForSEO Google organic SERP (no Apify needed).

Same PLAN + localized query sets as 7_serp_scrape.py (22 countries × language
Q-sets, ~115 queries), but runs through DataForSEO's
/v3/serp/google/organic/live/advanced at ~$0.0035 per query (depth 20) instead
of the Apify actor. Country geo comes from `location_name`; language from
`language_code`.

Output is written per country as serp_dfs_<country>_<lang>.json in the SAME
wrapper shape the Apify path produces ({"country","lang","items":[{organicResults:[...]}]}),
so 8_normalize_layer3.py consumes it unchanged (it globs serp_*.json).

Env: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD in data_sources/config/.env
Resumable: _serp_dfs_progress.json caches organic results per (country, query).

Same live/advanced gotcha as the Maps scraper: only ~1 task runs per POST array,
so we send one keyword per request and `--retry-empty` re-fetches throttled ones.

Usage:
    python3 outreach/scripts/7b_serp_dataforseo.py --dry-run     # plan + cost, $0
    python3 outreach/scripts/7b_serp_dataforseo.py --limit 3     # smoke test
    python3 outreach/scripts/7b_serp_dataforseo.py               # full run (~$0.40)
    python3 outreach/scripts/7b_serp_dataforseo.py --retry-empty
    python3 outreach/scripts/7b_serp_dataforseo.py --only-country US,GB,DE
"""
import argparse
import base64
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA / "layer3_serp_raw"
PROGRESS = DATA / "_serp_dfs_progress.json"
ENV = ROOT / "data_sources" / "config" / ".env"
API = "https://api.dataforseo.com/v3"
COST_PER_SEARCH = 0.0035
DEPTH = 20
CHUNK = 1  # live/advanced reliably runs ~1 task per POST; send one keyword each

# reuse the country PLAN + localized query sets from the Apify layer-3 scraper,
# and the country->DataForSEO location_name map from the layer-2 DFS scraper
sys.path.insert(0, str(Path(__file__).resolve().parent))
_serp = __import__("7_serp_scrape")
PLAN, Q = _serp.PLAN, _serp.Q
DFS_LOCATION = __import__("5b_gmaps_dataforseo").DFS_LOCATION


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
    req = urllib.request.Request(API + "/appendix/user_data", headers={"Authorization": hdr})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    return d["tasks"][0]["result"][0]["money"]["balance"]


def build_searches(only_country=None):
    out = []
    for e in PLAN:
        if only_country and e["country"] not in only_country:
            continue
        loc = DFS_LOCATION.get(e["country"])
        queries = Q.get(e["lang"])
        if not loc or not queries:
            print(f"  WARN missing loc/queries for {e['country']}/{e['lang']}, skipping")
            continue
        for q in queries:
            out.append({
                "key": f"{e['country']}|{q}",
                "keyword": q,
                "location_name": loc,
                "language_code": e["lang"],
                "country": e["country"],
                "lang": e["lang"],
            })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-country", default="")
    ap.add_argument("--limit", type=int, default=0, help="max NEW queries this run")
    ap.add_argument("--retry-empty", action="store_true",
                    help="re-fetch cached queries that returned 0 organic results")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    only_country = set(args.only_country.split(",")) if args.only_country else None
    searches = build_searches(only_country)

    est = len(searches) * COST_PER_SEARCH
    countries = sorted({s["country"] for s in searches})
    print(f"plan: {len(searches)} queries across {len(countries)} countries, "
          f"est. ${est:.2f} (~${COST_PER_SEARCH} each, depth {DEPTH})")
    if args.dry_run:
        return

    e = env()
    hdr = auth_header(e)

    store = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    if args.retry_empty:
        for k in [k for k, v in store.items() if not v.get("results")]:
            del store[k]
    todo = [s for s in searches if s["key"] not in store]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(store)} cached, {len(todo)} to fetch this run")

    if todo:
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
        resp = post("/serp/google/organic/live/advanced", payload, hdr)
        spent += resp.get("cost") or 0.0
        for s, task in zip(chunk, resp.get("tasks") or []):
            res = (task.get("result") or [{}])[0] if task.get("result") else {}
            items = res.get("items") or []
            results = [{"title": it.get("title"), "description": it.get("description"),
                        "url": it.get("url")}
                       for it in items if it.get("type") == "organic" and it.get("url")]
            store[s["key"]] = {"country": s["country"], "lang": s["lang"], "results": results}
        PROGRESS.write_text(json.dumps(store, ensure_ascii=False))
        got = sum(len(v["results"]) for v in store.values())
        print(f"  {min(i+CHUNK, len(todo))}/{len(todo)} queries | {got} organic cached | spent ${spent:.3f}")

    # rebuild per-country wrapper files from the full cache
    RAW_DIR.mkdir(exist_ok=True)
    by_country = {}
    for v in store.values():
        by_country.setdefault((v["country"], v["lang"]), []).append({"organicResults": v["results"]})
    for (country, lang), pages in sorted(by_country.items()):
        out = RAW_DIR / f"serp_dfs_{country}_{lang}.json"
        out.write_text(json.dumps({"country": country, "lang": lang, "items": pages},
                                  ensure_ascii=False), encoding="utf-8")
    total = sum(len(v["results"]) for v in store.values())
    print(f"wrote {len(by_country)} country files, {total} organic results to {RAW_DIR}")
    print(f"run cost ${spent:.3f}. Next: python3 outreach/scripts/8_normalize_layer3.py")


if __name__ == "__main__":
    main()
