#!/usr/bin/env python3
"""
Prep/3PL round 2, volume source: Bing HTML SERP (free; DDG rate-limited us).

Same idea as prep3_ddg_serp.py but against bing.com/search: localized
prep/3PL/fulfillment queries, parse organic result URLs, collect business
domains. Resumable via _prep_bing_progress.json; stops after 5 consecutive
failures (rate limit).

Output: outreach/data/prep_r2_bing.jsonl  {domain, country, region, source}

Usage:
    python3 outreach/scripts/prep3b_bing_serp.py --dry-run
    python3 outreach/scripts/prep3b_bing_serp.py --limit 5   # smoke test
    python3 outreach/scripts/prep3b_bing_serp.py
"""
import argparse
import importlib
import json
import random
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ddg = importlib.import_module("prep3_ddg_serp")

DATA = Path(__file__).resolve().parents[1] / "data"
OUT = DATA / "prep_r2_bing.jsonl"
PROGRESS = DATA / "_prep_bing_progress.json"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

PLAN = ddg.PLAN + (
    [("3pl warehouse for amazon sellers %s" % s, "US", s) for s in ddg.US_STATES[::2]] +
    [("order fulfillment services for online sellers %s" % c, "US", c) for c in ddg.US_CITIES[::2]] +
    [("fba prep and fulfillment %s" % s, "US", s) for s in ddg.US_STATES[1::2]]
)


def fetch_serp(q):
    url = "https://www.bing.com/search?q=" + urllib.parse.quote(q) + "&count=30"
    req = urllib.request.Request(url, headers={
        "User-Agent": ddg.UA, "Accept": "text/html",
        "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def parse_domains(html):
    out = []
    # organic results: <li class="b_algo"> ... <h2><a href="URL">
    for m in re.finditer(r'<li class="b_algo".*?<h2[^>]*><a[^>]*href="(https?://[^"]+)"',
                         html, re.S):
        try:
            host = urllib.parse.urlparse(m.group(1)).netloc.lower()
            host = host[4:] if host.startswith("www.") else host
            if host and "." in host and not ddg.JUNK.search(host):
                out.append(host)
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=2.0)
    args = ap.parse_args()

    print(f"plan: {len(PLAN)} queries")
    if args.dry_run:
        return

    store = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    todo = [(q, c, r) for q, c, r in PLAN if q not in store]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(store)} cached, {len(todo)} to fetch")

    fails = 0
    for i, (q, country, region) in enumerate(todo):
        try:
            doms = parse_domains(fetch_serp(q))
            store[q] = {"country": country, "region": region, "domains": doms}
            fails = 0
        except Exception as e:
            print(f"  FAIL [{q}]: {str(e)[:60]}")
            fails += 1
            if fails >= 5:
                print("5 consecutive failures — stopping early")
                break
            time.sleep(30)
            continue
        if (i + 1) % 25 == 0:
            uniq = {d for v in store.values() for d in v["domains"]}
            print(f"  {i+1}/{len(todo)} | {len(uniq)} unique domains")
            PROGRESS.write_text(json.dumps(store))
        time.sleep(args.delay + random.uniform(0, 1.5))

    PROGRESS.write_text(json.dumps(store))
    seen = {}
    for q, v in store.items():
        for d in v["domains"]:
            if d not in seen:
                seen[d] = {"domain": d, "country": v["country"],
                           "region": v["region"], "source": "bing_serp"}
    with OUT.open("w", encoding="utf-8") as f:
        for rec in seen.values():
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"wrote {len(seen)} unique domains to {OUT}")


if __name__ == "__main__":
    main()
