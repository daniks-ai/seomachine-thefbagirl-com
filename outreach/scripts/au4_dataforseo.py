#!/usr/bin/env python3
"""
Wave-3 AU lead source: Google Maps at scale via DataForSEO.

The free routes (directory sweeps, industry-body member lists, Apify's $5 cap)
were exhausted around ~930 domains. This walks a wide grid of AU locations x
agency query variants, which is where the long tail of small shops actually
lives — they rank in Maps for their suburb but appear in no listicle.

Gotcha carried over from the layer-2/3 build: the live/advanced endpoint only
reliably executes ONE task per POST — batching returns empty results for all but
the first. So each request carries one search; concurrency comes from running
many such requests in parallel instead. --retry-empty re-fetches anything that
came back empty (throttled) earlier. The per-search cache makes runs resumable.

Usage:
    python3 outreach/scripts/au4_dataforseo.py --dry-run
    python3 outreach/scripts/au4_dataforseo.py [--limit 100] [--retry-empty]
"""
import argparse
import base64
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parents[1] / "data"
ENV = ROOT / "data_sources" / "config" / ".env"
API = "https://api.dataforseo.com/v3"
PROGRESS = DATA / "_au_dfs_progress.json"
OUT = DATA / "au_dfs_places.json"

DEPTH = 20
WORKERS = 10
COST_PER_SEARCH = 0.002
LOCATION = "Australia"

LOCATIONS = [
    # capitals
    "Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Canberra",
    "Hobart", "Darwin",
    # major regional
    "Gold Coast", "Sunshine Coast", "Newcastle", "Wollongong", "Geelong",
    "Townsville", "Cairns", "Toowoomba", "Ballarat", "Bendigo", "Launceston",
    "Mackay", "Rockhampton", "Bundaberg", "Hervey Bay", "Wagga Wagga",
    "Albury", "Port Macquarie", "Coffs Harbour", "Tamworth", "Dubbo",
    "Orange", "Bathurst", "Shepparton", "Mildura", "Warrnambool",
    "Mount Gambier", "Bunbury", "Mandurah", "Alice Springs", "Nowra",
    # metro sub-markets that behave like their own search markets
    "Parramatta", "Chatswood", "Penrith", "Liverpool NSW", "Bondi",
    "North Sydney", "Surry Hills", "Richmond Victoria", "St Kilda",
    "Brunswick Victoria", "Box Hill", "Frankston", "Dandenong",
    "Fortitude Valley", "Southport", "Maroochydore", "Ipswich",
    "Subiaco", "Osborne Park", "Fremantle", "Joondalup",
    "Norwood", "Glenelg", "Unley",
]

QUERIES = [
    "digital marketing agency",
    "seo agency",
    "ppc agency",
    "google ads agency",
    "ecommerce agency",
    "advertising agency",
    "social media marketing agency",
    "web design agency",
    "marketing consultant",
    "amazon marketing agency",
]


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


def map_item(it):
    ai = it.get("address_info") or {}
    website = it.get("url") or (f"https://{it['domain']}" if it.get("domain") else "")
    return {
        "title": it.get("title"),
        "category": it.get("category"),
        "website": website,
        "city": ai.get("city"),
        "countryCode": (ai.get("country_code") or "AU").upper(),
        "source": "google_maps_dataforseo_au",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max NEW searches this run")
    ap.add_argument("--retry-empty", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    searches = [{"key": f"{loc}|{q}", "keyword": f"{q} {loc}"}
                for loc in LOCATIONS for q in QUERIES]
    print(f"plan: {len(searches)} searches ({len(LOCATIONS)} locations x "
          f"{len(QUERIES)} queries), est. ${len(searches)*COST_PER_SEARCH:.2f}, "
          f"{DEPTH} places each")
    if args.dry_run:
        return

    hdr = auth_header(env())
    store = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    if args.retry_empty:
        for k in [k for k, v in store.items() if not v.get("records")]:
            del store[k]
    todo = [s for s in searches if s["key"] not in store]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(store)} cached, {len(todo)} to fetch")

    bal = balance(hdr)
    need = len(todo) * COST_PER_SEARCH
    print(f"balance ${bal:.2f}, this run needs ~${need:.2f}")
    if need > bal:
        sys.exit(f"insufficient balance: need ${need:.2f}, have ${bal:.2f}")

    # One task per POST is a hard constraint of live/advanced, but separate
    # concurrent POSTs are fine — that is what keeps a 630-search grid to
    # minutes instead of the ~2h a serial loop takes.
    def fetch(s):
        payload = [{"keyword": s["keyword"], "location_name": LOCATION,
                    "language_code": "en", "depth": DEPTH}]
        try:
            resp = post("/serp/google/maps/live/advanced", payload, hdr)
        except Exception as exc:                      # noqa: BLE001
            return s, [], 0.0, str(exc)[:60]
        task = (resp.get("tasks") or [{}])[0]
        res = (task.get("result") or [{}])[0] if task.get("result") else {}
        recs = [map_item(it) for it in (res.get("items") or []) if it.get("title")]
        return s, recs, resp.get("cost") or 0.0, None

    spent, done, failed = 0.0, 0, 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for s, recs, cost, err in ex.map(fetch, todo):
            done += 1
            spent += cost
            if err:
                failed += 1
                continue
            store[s["key"]] = {"records": recs}
            if done % 40 == 0 or done == len(todo):
                PROGRESS.write_text(json.dumps(store, ensure_ascii=False))
                got = sum(len(v["records"]) for v in store.values())
                print(f"  {done}/{len(todo)} | {got} places | ${spent:.2f}"
                      + (f" | {failed} failed" if failed else ""))

    PROGRESS.write_text(json.dumps(store, ensure_ascii=False))
    allrecs = [r for v in store.values() for r in v["records"]]
    OUT.write_text(json.dumps(allrecs, ensure_ascii=False), encoding="utf-8")
    empties = sum(1 for v in store.values() if not v["records"])
    print(f"done: {len(allrecs)} place records -> {OUT} (spent ${spent:.2f})")
    if empties:
        print(f"NOTE {empties} searches returned empty (throttled) — "
              f"re-run with --retry-empty to fill them")


if __name__ == "__main__":
    main()
