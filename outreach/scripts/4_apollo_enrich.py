#!/usr/bin/env python3
"""
Optional firmographic enrichment via Apollo Organization Enrichment.

IMPORTANT: the connected Apollo account is on the FREE plan. On free, ONLY
`/organizations/enrich` (company-level: industry, phone, LinkedIn, employee
count, city/country) is accessible. People Search / People Match / Company
Search — which return decision-maker *emails* — require a PAID Apollo plan and
return API_INACCESSIBLE on free. So this step adds company context, NOT emails.
Emails come from the Apify contact scraper (step 2).

Resumable + throttled to respect free-plan rate limits. Reads domains from
step 1, writes a domain->firmographics cache that step 3 can optionally join.

Env: APOLLO_API_KEY in data_sources/config/.env

Usage:
    python3 outreach/scripts/4_apollo_enrich.py --limit 200
"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parents[1] / "data"
ENV = ROOT / "data_sources" / "config" / ".env"
CACHE = DATA / "apollo_orgs.json"


def key() -> str:
    for line in ENV.read_text().splitlines():
        if line.startswith("APOLLO_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("APOLLO_API_KEY not found in .env")


def enrich(domain, api_key):
    url = f"https://api.apollo.io/api/v1/organizations/enrich?domain={domain}"
    req = urllib.request.Request(url, headers={
        "X-Api-Key": api_key, "Cache-Control": "no-cache",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=1.2, help="seconds between calls")
    args = ap.parse_args()

    api_key = key()
    domains = [d.strip() for d in (DATA / "layer1_domains.txt").read_text().splitlines() if d.strip()]
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    todo = [d for d in domains if d not in cache]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(cache)} cached, {len(todo)} to enrich this run")

    done = 0
    for d in todo:
        try:
            data = enrich(d, api_key)
            if data.get("error"):
                print(f"  ! {d}: {data['error'][:60]}")
                if "not accessible" in str(data.get("error", "")):
                    sys.exit("Endpoint blocked on this plan — stopping.")
                cache[d] = {"error": data.get("error_code")}
            else:
                o = data.get("organization") or {}
                cache[d] = {
                    "name": o.get("name"),
                    "industry": o.get("industry"),
                    "phone": o.get("phone"),
                    "linkedin": o.get("linkedin_url"),
                    "employees": o.get("estimated_num_employees"),
                    "city": o.get("city"),
                    "country": o.get("country"),
                    "founded": o.get("founded_year"),
                }
            done += 1
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print("  rate-limited (429); backing off 30s")
                time.sleep(30)
                continue
            print(f"  ! {d}: HTTP {e.code}")
            cache[d] = {"error": f"http_{e.code}"}
        except Exception as e:  # noqa
            print(f"  ! {d}: {e}")
        if done % 25 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"  ...{done} done, cache saved")
        time.sleep(args.sleep)

    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    ok = sum(1 for v in cache.values() if not v.get("error"))
    print(f"cache now {len(cache)} domains ({ok} enriched ok)")
    print(f"wrote {CACHE}")


if __name__ == "__main__":
    main()
