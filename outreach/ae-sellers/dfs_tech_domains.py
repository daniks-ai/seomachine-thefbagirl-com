#!/usr/bin/env python3
"""Pull UAE e-commerce domains from DataForSEO Domain Analytics (domains_by_technology).

The UAE seller list starts from "who runs an online store registered in AE" — that is
the widest free-of-scraping pool DataForSEO exposes. Amazon-seller confirmation happens
later, in the harvest step (site linking to an Amazon storefront = Tier A).

Usage:
  python3 outreach/ae-sellers/dfs_tech_domains.py --dry-run     # counts + cost, $0.018/probe
  python3 outreach/ae-sellers/dfs_tech_domains.py               # full pull
"""
import argparse
import base64
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(parents=True, exist_ok=True)
OUT_JSONL = DATA / "ae_tech_domains.jsonl"
PROGRESS = DATA / "_dfs_tech_progress.json"

# Storefront platforms worth pulling. Ordered widest-first; each is a separate API call
# family (one call per 1000 domains).
TECHNOLOGIES = [
    "Shopify",
    "WooCommerce",
    "Magento",
    "Wix eCommerce",
    "Squarespace Commerce",
    "OpenCart",
    "PrestaShop",
    "BigCommerce",
    "Salla",
    "Zid",
    "Shopify Plus",
    "Ecwid",
    "Shoppy",
    "osCommerce",
    "Zen Cart",
    "CS-Cart",
    "nopCommerce",
    "Odoo",
    "Shopware",
    "Sylius",
]

LIMIT = 1000


def load_env():
    env = {}
    for line in (ROOT / "data_sources/config/.env").read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


class DFS:
    def __init__(self, env):
        self.auth = "Basic " + base64.b64encode(
            f"{env['DATAFORSEO_LOGIN']}:{env['DATAFORSEO_PASSWORD']}".encode()
        ).decode()
        self.cost = 0.0

    def post(self, path, payload, tries=3):
        for attempt in range(tries):
            try:
                req = urllib.request.Request(
                    "https://api.dataforseo.com/v3" + path,
                    data=json.dumps(payload).encode(),
                    headers={"Authorization": self.auth, "Content-Type": "application/json"},
                )
                r = json.load(urllib.request.urlopen(req, timeout=300))
                self.cost += r.get("cost") or 0.0
                return r
            except Exception as exc:  # noqa: BLE001 - network flakiness, retry
                if attempt == tries - 1:
                    raise
                print(f"    retry after {exc}", file=sys.stderr)
                time.sleep(5 * (attempt + 1))
        return None

    def domains(self, tech, offset):
        payload = [{
            "technologies": [tech],
            "filters": [["country_iso_code", "=", "AE"]],
            "limit": LIMIT,
            "offset": offset,
        }]
        r = self.post("/domain_analytics/technologies/domains_by_technology/live", payload)
        task = r["tasks"][0]
        if task.get("status_code") != 20000:
            return None, 0, task.get("status_message")
        res = (task.get("result") or [{}])[0]
        return res.get("items") or [], res.get("total_count") or 0, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="one probe per technology, no pagination")
    args = ap.parse_args()

    dfs = DFS(load_env())
    progress = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    seen = set()
    if OUT_JSONL.exists():
        for line in OUT_JSONL.read_text().splitlines():
            if line.strip():
                seen.add(json.loads(line)["domain"])

    out = OUT_JSONL.open("a")
    grand_new = 0
    for tech in TECHNOLOGIES:
        if progress.get(tech) == "done" and not args.dry_run:
            print(f"{tech}: done earlier, skip")
            continue
        offset, total, new_here = 0, None, 0
        while True:
            items, total, err = dfs.domains(tech, offset)
            if err:
                print(f"{tech}: ERROR {err}")
                break
            if total == 0 or not items:
                break
            for it in items:
                d = (it.get("domain") or "").lower().strip()
                if not d or d in seen:
                    continue
                seen.add(d)
                new_here += 1
                out.write(json.dumps({
                    "domain": d,
                    "tech": tech,
                    "country": it.get("country_iso_code"),
                    "language": it.get("language_code"),
                    "title": it.get("title"),
                    "description": it.get("description"),
                    "last_visited": it.get("last_visited"),
                }, ensure_ascii=False) + "\n")
            out.flush()
            offset += LIMIT
            if args.dry_run or offset >= total:
                break
        print(f"{tech}: total_count={total} new_domains={new_here} (cum cost ${dfs.cost:.2f})")
        grand_new += new_here
        if not args.dry_run:
            progress[tech] = "done"
            PROGRESS.write_text(json.dumps(progress, indent=1))
    out.close()

    print(f"\nNEW domains this run: {grand_new}; unique total: {len(seen)}; cost ${dfs.cost:.2f}")
    (DATA / "ae_domains.txt").write_text("\n".join(sorted(seen)) + "\n")
    print(f"wrote {DATA/'ae_domains.txt'}")


if __name__ == "__main__":
    main()
