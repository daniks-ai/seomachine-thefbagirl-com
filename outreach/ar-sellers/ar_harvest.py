#!/usr/bin/env python3
"""
Thin wrapper around the shared harvesters (`2b_email_harvest.py`, then
`2c_deep_harvest.py` on whatever came back empty) that redirects their caches
into `outreach/ar-sellers/data/`.

Reason: both shared scripts read-modify-**write the whole** `_harvest_progress.json`
in `outreach/data/`. Other verticals are harvesting in this repo at the same time,
and a full-store rewrite from here would silently drop their concurrent rows.
Same code, private cache.

Usage:
    python3 outreach/ar-sellers/ar_harvest.py                # 2b then 2c
    python3 outreach/ar-sellers/ar_harvest.py --deep-only
    python3 outreach/ar-sellers/ar_harvest.py --workers 32
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SCRIPTS = HERE.parents[0] / "scripts"
DOMAINS = DATA / "ar_domains.txt"
PROGRESS = DATA / "_harvest_progress.json"
CONTACTS = DATA / "ar_contacts_raw.json"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    mod.DATA = DATA
    mod.PROGRESS = PROGRESS
    mod.OUT = CONTACTS
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--deep-only", action="store_true")
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)

    if not args.deep_only:
        m = load(SCRIPTS / "2b_email_harvest.py", "harvest2b")
        sys.argv = ["2b", "--domains-file", str(DOMAINS),
                    "--workers", str(args.workers)]
        if args.limit:
            sys.argv += ["--limit", str(args.limit)]
        m.main()

    store = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    empty = [d for d in DOMAINS.read_text().split()
             if d and not (store.get(d) or {}).get("emails")]
    print(f"\ndeep pass on {len(empty)} domains with no email")
    if not empty:
        return
    todo = DATA / "ar_domains_noemail.txt"
    todo.write_text("\n".join(empty) + "\n")

    m = load(SCRIPTS / "2c_deep_harvest.py", "harvest2c")
    sys.argv = ["2c", "--domains-file", str(todo), "--workers", str(args.workers)]
    m.main()

    store = json.loads(PROGRESS.read_text())
    got = sum(1 for d in DOMAINS.read_text().split()
              if (store.get(d) or {}).get("emails"))
    print(f"\ntotal domains with >=1 email: {got}")


if __name__ == "__main__":
    main()
