#!/usr/bin/env python3
"""
Email harvest for the AU wave-3 domains, isolated from the shared cache.

Why this exists: 2b/2c write to one workspace-wide pair of files
(_harvest_progress.json, layer1_contacts_raw.json). When another session runs a
harvest at the same time, whichever process finishes last writes its own
snapshot and silently discards the other's results — this cost a full 2,203-domain
run before the pipeline was isolated. Harvest logic is imported unchanged from
2b; only the cache and output paths are private to this wave.

Usage:
    python3 outreach/scripts/au7_harvest_isolated.py --domains-file <file> [--workers 25]
    python3 outreach/scripts/au7_harvest_isolated.py --domains-file <file> --deep
"""
import argparse
import concurrent.futures as cf
import json
import sys
from importlib import import_module
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
shallow = import_module("2b_email_harvest")
deep = import_module("2c_deep_harvest")

DATA = Path(__file__).resolve().parents[1] / "data"
CACHE = DATA / "_au3_harvest.json"          # private: no other session writes here
OUT = DATA / "au3_contacts.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains-file", required=True)
    ap.add_argument("--workers", type=int, default=25)
    ap.add_argument("--deep", action="store_true",
                    help="use the deep second-pass harvester (contact-page probing)")
    args = ap.parse_args()

    domains = [d.strip() for d in Path(args.domains_file).read_text().splitlines()
               if d.strip()]
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [d for d in domains if not (cache.get(d) or {}).get("emails")]
    fn = deep.harvest if args.deep else shallow.harvest
    print(f"{len(cache)} cached, {len(todo)} to fetch "
          f"({'deep' if args.deep else 'shallow'} pass)")

    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fn, d): d for d in todo}
        for fut in cf.as_completed(futs):
            d = futs[fut]
            try:
                rec = fut.result()
            except Exception as exc:                      # noqa: BLE001
                rec = {"domain": d, "emails": [], "error": str(exc)[:60]}
            if rec.get("emails") or d not in cache:
                cache[d] = rec
            done += 1
            if done % 200 == 0:
                CACHE.write_text(json.dumps(cache, ensure_ascii=False))
                hits = sum(1 for v in cache.values() if v.get("emails"))
                print(f"  {done}/{len(todo)} | {hits} domains with email")

    CACHE.write_text(json.dumps(cache, ensure_ascii=False))
    OUT.write_text(json.dumps(list(cache.values()), ensure_ascii=False),
                   encoding="utf-8")
    hits = sum(1 for v in cache.values() if v.get("emails"))
    print(f"done: {len(cache)} domains cached, {hits} with >=1 email -> {OUT}")


if __name__ == "__main__":
    main()
