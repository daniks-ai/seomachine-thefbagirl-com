#!/usr/bin/env python3
"""
Build the UK round-2 top-up CSV from the isolated harvest.

  in : data/uk_r2_emails.jsonl   (uk2_isolated_harvest.py output)
       data/uk_r2_meta.json      (domain -> {name, website})
       data/instantly_UK.csv     (round 1, already in the campaign)
  out: data/instantly_UK_r2.csv

Reuses round 1's hygiene rules by importing uk1_build_csv (EXCLUDE_EMAILS,
EXCLUDE_LOCAL, DROP_DOMAINS, verification sets, company/website cleanup) so the
two rounds cannot drift apart. Round-1 emails and domains already represented in
the campaign are excluded here; Instantly's own skip flags are the second net.
"""
import csv
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

spec = importlib.util.spec_from_file_location("uk1", HERE / "uk1_build_csv.py")
uk1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uk1)
builder = uk1.builder

FIELDS = ["email", "first_name", "last_name", "company_name", "website",
          "country", "segment", "language", "source"]

# harvest artifacts seen in round 1: analytics/CDN/vendor addresses that sit in
# page markup on many sites and are never the agency's own inbox
VENDOR_LOCAL = re.compile(
    r"^(hello|info|contact|support|sales|team|hi|enquiries?|admin)$", re.I)
OFF_BRAND_OK = 5   # min stem length to accept an alternate apex


def main():
    checked, passed = uk1.load_verification_sets()
    meta = json.loads((DATA / "uk_r2_meta.json").read_text(encoding="utf-8"))

    prior_emails, prior_domains = set(), set()
    for r in csv.DictReader((DATA / "instantly_UK.csv").open(encoding="utf-8")):
        prior_emails.add(r["email"].lower())
        prior_domains.add(r["email"].split("@")[1].lower())

    rows, seen = [], set()
    stats = {"domains": 0, "with_email": 0, "kept_domains": 0,
             "dropped_verification": 0, "dropped_offdomain": 0,
             "dropped_foreign_office": 0}

    for line in (DATA / "uk_r2_emails.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        dom = rec["domain"]
        stats["domains"] += 1
        if not rec["emails"]:
            continue
        stats["with_email"] += 1
        if dom in uk1.DROP_DOMAINS or dom in prior_domains:
            continue

        good = []
        for e in rec["emails"]:
            e = uk1.clean_email(e)
            if not e or e in prior_emails or e in seen or e in uk1.EXCLUDE_EMAILS:
                continue
            local, edom = e.split("@", 1)
            if uk1.EXCLUDE_LOCAL.match(local):
                continue
            if edom in prior_domains or edom in uk1.DROP_DOMAINS:
                continue
            if not uk1.email_ok_for_site(e, dom):
                stats["dropped_offdomain"] += 1
                continue
            if uk1.FOREIGN_OFFICE_TLD.search(edom) and not dom.endswith(edom):
                stats["dropped_foreign_office"] += 1
                continue
            if e in checked and e not in passed:
                stats["dropped_verification"] += 1
                continue
            good.append(e)
        if not good:
            continue

        good.sort(key=lambda e: (
            0 if builder.NAME_LOCAL.match(e.split("@")[0])
            and not builder.is_generic(e.split("@")[0])
            else 1 if not builder.is_generic(e.split("@")[0]) else 2))
        m = meta.get(dom, {})
        stats["kept_domains"] += 1
        for e in good[:uk1.MAX_PER_DOMAIN]:
            seen.add(e)
            fn, ln = builder.guess_name(e.split("@", 1)[0])
            rows.append({
                "email": e,
                "first_name": uk1.fix_first(fn, ln),
                "last_name": ln,
                "company_name": uk1.COMPANY_FIX.get(dom, uk1.clean_company(m.get("name"), dom)),
                "website": uk1.clean_website(m.get("website"), dom),
                "country": "GB", "segment": "UK", "language": "en",
                "source": "uk_isolated_harvest_r2_2026_08",
            })

    out = DATA / "instantly_UK_r2.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    named = sum(1 for r in rows if r["first_name"] != "there")
    print(f"harvested domains: {stats['domains']} ({stats['with_email']} with >=1 email)")
    print(f"dropped: {stats['dropped_offdomain']} off-domain, "
          f"{stats['dropped_verification']} failed-verification, "
          f"{stats['dropped_foreign_office']} foreign-office TLD")
    print(f"NEW rows: {len(rows)} ({named} named) across {stats['kept_domains']} domains")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
