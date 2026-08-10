#!/usr/bin/env python3
"""
E-commerce accountant / CPA vertical, step 2: merge cpa_firms.jsonl with
harvested contacts into Instantly-ready CSVs. Reuses the email-quality filters
from 3_build_instantly_csv.py (role-inbox detection, name guessing, ranking).

Segments (25%-lifetime affiliate pitch, EN copy):
  CPA-US    — United States
  CPA-GB    — United Kingdom (Link My Books skew; same copy, GB send window)
  CPA-INTL  — AU/CA/NZ + everywhere else English-reachable

Dedupes emails against ALL other masters (agency layers 1-3 + prep centers) —
an address already in a live campaign is never re-mailed.

Usage:
    python3 outreach/scripts/cpa2_build_instantly_csv.py
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
B = __import__("3_build_instantly_csv")  # shared filters

SEG_DIR = DATA / "instantly_segments_cpa"
MASTER = DATA / "instantly_cpa_master.csv"
FIELDS = ["email", "first_name", "last_name", "company_name", "website",
          "country", "region", "segment", "language", "source"]


def segment_of(country):
    if country == "US":
        return "CPA-US"
    if country == "GB":
        return "CPA-GB"
    return "CPA-INTL"


def main():
    firms = {r["domain"]: r for r in
             (json.loads(l) for l in (DATA / "cpa_firms.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip())}

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
    for mname in ("instantly_layer1_master.csv", "instantly_layer2_master.csv",
                  "instantly_layer3_master.csv", "instantly_prep_master.csv"):
        m = DATA / mname
        if m.exists():
            with m.open(encoding="utf-8") as f:
                seen.update(r["email"].strip().lower() for r in csv.DictReader(f))

    rows = []
    for dom, firm in firms.items():
        emails = by_domain.get(dom)
        if not emails:
            continue
        ranked = sorted(emails, key=lambda e: (
            0 if B.NAME_LOCAL.match(e.split("@")[0]) and not B.is_generic(e.split("@")[0])
            else 1 if not B.is_generic(e.split("@")[0]) else 2))
        # partner pitch goes to the firm, not the whole staff page — cap 3/domain
        for e in ranked[:3]:
            if e in seen:
                continue
            seen.add(e)
            fn, ln = B.guess_name(e.split("@", 1)[0])
            rows.append({
                "email": e,
                "first_name": fn or "there",
                "last_name": ln,
                "company_name": firm.get("company") or dom,
                "website": firm.get("website") or f"https://{dom}",
                "country": firm.get("country") or "",
                "region": firm.get("region") or "",
                "segment": segment_of(firm.get("country")),
                "language": "en",
                "source": firm.get("source") or "cpa_directory",
            })

    with MASTER.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    by_seg = defaultdict(list)
    for r in rows:
        by_seg[r["segment"]].append(r)
    SEG_DIR.mkdir(exist_ok=True)
    for seg, rs in sorted(by_seg.items()):
        with (SEG_DIR / f"instantly_{seg}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rs)

    print(f"accounting firms with website: {len(firms)}")
    print(f"with >=1 usable email:         {sum(1 for d in firms if by_domain.get(d))}")
    print(f"total contact rows:            {len(rows)}")
    print(f"named (personal) rows:         {sum(1 for r in rows if r['first_name'] != 'there')}")
    for seg, rs in sorted(by_seg.items(), key=lambda kv: -len(kv[1])):
        print(f"  {seg:10s} {len(rs)}")
    print(f"wrote {MASTER} + {len(by_seg)} segment files in {SEG_DIR}")


if __name__ == "__main__":
    main()
