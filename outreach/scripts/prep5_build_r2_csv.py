#!/usr/bin/env python3
"""
Prep-center round 2: build the Instantly import CSV.

Takes BOTH prep_centers.jsonl (round 1) and prep_r2_centers.jsonl (round 2) —
round-1 domains are included because the deep harvest may have found emails
for domains that yielded nothing before round 1 was imported. Emails already
imported (instantly_prep_master.csv) or used by agency masters are excluded,
so the output contains only NEW addresses.

Output: outreach/data/instantly_prep_r2.csv (+ PREP-CN split kept separate)

Usage: python3 outreach/scripts/prep5_build_r2_csv.py
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
B = __import__("3_build_instantly_csv")

OUT = DATA / "instantly_prep_r2.csv"
OUT_CN = DATA / "instantly_prep_r2_CN.csv"
FIELDS = ["email", "first_name", "last_name", "company_name", "website",
          "country", "region", "segment", "language", "source"]


def main():
    preps = {}
    for fname in ("prep_centers.jsonl", "prep_r2_centers.jsonl"):
        p = DATA / fname
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    preps.setdefault(r["domain"], r)

    contacts = json.loads((DATA / "layer1_contacts_raw.json").read_text(encoding="utf-8"))
    by_domain = defaultdict(set)
    for rec in contacts:
        for e in rec.get("emails") or []:
            e = e.strip().lower()
            if "@" not in e or "%" in e or not e[0].isalnum():
                continue
            if B.BAD_LOCAL.match(e.split("@", 1)[0]):
                continue
            by_domain[B.domain_of(e)].add(e)

    seen = set()
    for mname in ("instantly_prep_master.csv", "instantly_layer1_master.csv",
                  "instantly_layer2_master.csv", "instantly_layer3_master.csv",
                  "instantly_cpa_master.csv"):
        m = DATA / mname
        if m.exists():
            with m.open(encoding="utf-8") as f:
                seen.update(r["email"].strip().lower() for r in csv.DictReader(f))

    rows, rows_cn = [], []
    for dom, prep in preps.items():
        emails = by_domain.get(dom)
        if not emails:
            continue
        ranked = sorted(emails, key=lambda e: (
            0 if B.NAME_LOCAL.match(e.split("@")[0]) and not B.is_generic(e.split("@")[0])
            else 1 if not B.is_generic(e.split("@")[0]) else 2))
        country = prep.get("country") or ""
        for e in ranked[:3]:  # cap 3 per domain
            if e in seen:
                continue
            seen.add(e)
            fn, ln = B.guess_name(e.split("@", 1)[0])
            # Amazon-specific prep centers keep the prep copy; generic
            # 3PL / fulfillment warehouses get their own segment so their
            # Step-1 can open on "your clients sell on Amazon" instead.
            pref = "PREP" if prep.get("kind", "prep") == "prep" else "3PL"
            geo = "CN" if country == "CN" else ("US" if country == "US" else "INTL")
            row = {
                "email": e,
                "first_name": fn or "there",
                "last_name": ln,
                "company_name": prep.get("company") or dom,
                "website": prep.get("website") or f"https://{dom}",
                "country": country,
                "region": prep.get("region") or "",
                "segment": f"{pref}-{geo}",
                "language": "en",
                "source": prep.get("source") or "prep_directory",
            }
            (rows_cn if country == "CN" else rows).append(row)

    for path, rs in ((OUT, rows), (OUT_CN, rows_cn)):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rs)

    named = sum(1 for r in rows if r["first_name"] != "there")
    by_seg = defaultdict(int)
    for r in rows:
        by_seg[r["segment"]] += 1
    print(f"domains considered: {len(preps)} | with usable email: "
          f"{sum(1 for d in preps if by_domain.get(d))}")
    print(f"NEW rows for campaign: {len(rows)} (named {named}) | CN held out: {len(rows_cn)}")
    for s, n in sorted(by_seg.items(), key=lambda kv: -kv[1]):
        print(f"  {s:10s} {n}")
    print(f"wrote {OUT} + {OUT_CN}")


if __name__ == "__main__":
    main()
