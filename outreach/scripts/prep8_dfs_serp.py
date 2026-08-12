#!/usr/bin/env python3
"""
Prep/3PL round 2, long-tail top-up: organic Google SERP via DataForSEO.

Maps covers businesses with a storefront pin; organic search surfaces the ones
that rank for "fba prep center <state>" style queries without a strong Maps
presence (and the state-level listicles' own members). ~$0.0035 per query.

Output: outreach/data/prep_r2_dfs_serp.jsonl {domain, country, region, source}
Resumable cache: _prep_dfs_serp_progress.json

Usage:
    python3 outreach/scripts/prep8_dfs_serp.py --dry-run
    python3 outreach/scripts/prep8_dfs_serp.py
"""
import argparse
import concurrent.futures as cf
import importlib
import json
import re
import sys
import threading
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
maps = importlib.import_module("prep7_dfs_maps")
ddg = importlib.import_module("prep3_ddg_serp")

DATA = Path(__file__).resolve().parents[1] / "data"
OUT = DATA / "prep_r2_dfs_serp.jsonl"
PROGRESS = DATA / "_prep_dfs_serp_progress.json"
COST_PER_QUERY = 0.0035
DEPTH = 50

_lock = threading.Lock()

QUERIES = (
    [(f"fba prep center {s}", "United States", "US", s) for s in ddg.US_STATES] +
    [(f"amazon prep and ship {s}", "United States", "US", s) for s in ddg.US_STATES] +
    [(f"3pl fulfillment for amazon sellers {s}", "United States", "US", s)
     for s in ddg.US_STATES] +
    [(f"ecommerce fulfillment company {c}", "United States", "US", c)
     for c in ddg.US_CITIES] +
    [("fba prep centre uk", "United Kingdom", "GB", ""),
     ("amazon fba prep service uk", "United Kingdom", "GB", ""),
     ("ecommerce fulfilment company uk", "United Kingdom", "GB", ""),
     ("3pl fulfilment uk amazon", "United Kingdom", "GB", ""),
     ("fba prep center canada", "Canada", "CA", ""),
     ("amazon fba prep service canada", "Canada", "CA", ""),
     ("3pl fulfillment canada ecommerce", "Canada", "CA", ""),
     ("fba prep australia", "Australia", "AU", ""),
     ("ecommerce fulfilment australia", "Australia", "AU", ""),
     ("fba prep center deutschland", "Germany", "DE", ""),
     ("amazon fulfillment dienstleister", "Germany", "DE", ""),
     ("fba prep center nederland", "Netherlands", "NL", ""),
     ("fba prep poland", "Poland", "PL", ""),
     ("amazon prep center espana", "Spain", "ES", ""),
     ("amazon prep center italia", "Italy", "IT", ""),
     ("prestataire logistique amazon fba", "France", "FR", ""),
     ("fba prep center ireland", "Ireland", "IE", ""),
     ("fba prep center czech", "Czech Republic", "CZ", ""),
     ("fba prep center dubai", "United Arab Emirates", "AE", ""),
     ("amazon prep center mexico", "Mexico", "MX", "")]
)


def parse_domains(items):
    out = []
    for it in items or []:
        if it.get("type") not in ("organic", None):
            continue
        url = it.get("url") or ""
        try:
            host = urllib.parse.urlparse(url).netloc.lower()
        except Exception:
            continue
        host = host[4:] if host.startswith("www.") else host
        if host and "." in host and not ddg.JUNK.search(host) \
                and not maps.JUNK.search(host):
            out.append(host)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print(f"plan: {len(QUERIES)} queries x top-{DEPTH}, "
          f"est ${len(QUERIES)*COST_PER_QUERY:.2f}")
    if args.dry_run:
        return

    hdr = maps.auth_header(maps.env())
    store = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    todo = [q for q in QUERIES if q[0] not in store]
    if args.limit:
        todo = todo[: args.limit]
    bal = maps.balance(hdr)
    need = len(todo) * COST_PER_QUERY
    print(f"{len(store)} cached, {len(todo)} to fetch | balance ${bal:.2f}, "
          f"need ~${need:.2f}")
    if need > bal:
        sys.exit("insufficient balance")

    done, spent = [0], [0.0]

    def run(item):
        kw, loc, cc, region = item
        try:
            resp = maps.post("/serp/google/organic/live/advanced", [{
                "keyword": kw, "location_name": loc, "language_code": "en",
                "depth": DEPTH}], hdr)
            task = (resp.get("tasks") or [{}])[0]
            res = (task.get("result") or [{}])[0] if task.get("result") else {}
            doms = parse_domains(res.get("items"))
            cost = resp.get("cost") or 0.0
        except Exception as ex:
            doms, cost = [], 0.0
            print(f"  FAIL [{kw[:40]}]: {str(ex)[:50]}")
        with _lock:
            store[kw] = {"country": cc, "region": region, "domains": doms}
            spent[0] += cost
            done[0] += 1
            if done[0] % 40 == 0:
                PROGRESS.write_text(json.dumps(store))
                uniq = {d for v in store.values() for d in v["domains"]}
                print(f"  {done[0]}/{len(todo)} | {len(uniq)} unique | "
                      f"${spent[0]:.2f}")

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(run, todo))
    PROGRESS.write_text(json.dumps(store))

    seen = {}
    for kw, v in store.items():
        for d in v["domains"]:
            if d not in seen:
                seen[d] = {"domain": d, "country": v["country"],
                           "region": v["region"], "source": "dfs_organic"}
    with OUT.open("w", encoding="utf-8") as f:
        for r in seen.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n{len(seen)} unique domains -> {OUT} | cost ${spent[0]:.2f}")


if __name__ == "__main__":
    main()
