#!/usr/bin/env python3
"""
Prep-center vertical, step 2: merge prep_centers.jsonl with harvested contacts
into Instantly-ready CSVs. Reuses the email-quality filters from
3_build_instantly_csv.py (role-inbox detection, name guessing, ranking).

Segments (the offer is an affiliate/referral pitch, EN copy first):
  PREP-US    — United States
  PREP-INTL  — everywhere else English-reachable (GB/CA/AU/EU/…)
  PREP-CN    — China-based prep/forwarding centers (own CSV; pairs with the
               WeChat/China motion, do NOT drop into the EN campaign blindly)

Dedupes emails against ALL agency masters (layers 1-3) — an address already in
a live agency campaign is never re-mailed.

Usage:
    python3 outreach/scripts/prep2_build_instantly_csv.py
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
B = __import__("3_build_instantly_csv")  # shared filters

SEG_DIR = DATA / "instantly_segments_prep"
MASTER = DATA / "instantly_prep_master.csv"
FIELDS = ["email", "first_name", "last_name", "company_name", "website",
          "country", "region", "segment", "language", "source"]


def segment_of(country):
    if country == "US":
        return "PREP-US"
    if country == "CN":
        return "PREP-CN"
    return "PREP-INTL"


def main():
    preps = {r["domain"]: r for r in
             (json.loads(l) for l in (DATA / "prep_centers.jsonl")
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
                  "instantly_layer3_master.csv"):
        m = DATA / mname
        if m.exists():
            with m.open(encoding="utf-8") as f:
                seen.update(r["email"].strip().lower() for r in csv.DictReader(f))

    rows = []
    for dom, prep in preps.items():
        emails = by_domain.get(dom)
        if not emails:
            continue
        ranked = sorted(emails, key=lambda e: (
            0 if B.NAME_LOCAL.match(e.split("@")[0]) and not B.is_generic(e.split("@")[0])
            else 1 if not B.is_generic(e.split("@")[0]) else 2))
        for e in ranked:
            if e in seen:
                continue
            seen.add(e)
            fn, ln = B.guess_name(e.split("@", 1)[0])
            rows.append({
                "email": e,
                "first_name": fn or "there",
                "last_name": ln,
                "company_name": prep.get("company") or dom,
                "website": prep.get("website") or f"https://{dom}",
                "country": prep.get("country") or "",
                "region": prep.get("region") or "",
                "segment": segment_of(prep.get("country")),
                "language": "en",
                "source": prep.get("source") or "prep_directory",
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

    print(f"prep centers with website: {len(preps)}")
    print(f"with >=1 usable email:     {sum(1 for d in preps if by_domain.get(d))}")
    print(f"total contact rows:        {len(rows)}")
    print(f"named (personal) rows:     {sum(1 for r in rows if r['first_name'] != 'there')}")
    for seg, rs in sorted(by_seg.items(), key=lambda kv: -len(kv[1])):
        print(f"  {seg:10s} {len(rs)}")
    print(f"wrote {MASTER} + {len(by_seg)} segment files in {SEG_DIR}")


if __name__ == "__main__":
    main()
