#!/usr/bin/env python3
"""
Wave-3 CSV for the [AU] campaign.

Sources (data/au3_agencies.jsonl): DataForSEO Google-Maps grid over 63 AU
locations, Yellow Pages via browser, industry-vertical specialists, platform
partner directories, award shortlists, suburb sweeps.

Reuses every hygiene filter earned on waves 1-2 (au1/au2 builders) and adds the
wave-3-specific guards:
  - drops domains whose homepage showed no agency vocabulary AND looked like a
    different kind of business (au5_verify_agency.py verdicts), because
    directory listings sometimes attach the wrong website to a business
  - drops domains with no mail route (au3_mx_check.py dead list)
  - dedupes emails against BOTH earlier waves

Output: data/instantly_AU3.csv
"""
import csv
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


au2 = _load("au2", HERE / "au2_build_csv.py")
au1, builder = au2.au1, au2.builder


def main():
    agencies = {a["domain"]: a for a in builder.load_jsonl(DATA / "au3_agencies.jsonl")}
    contacts = json.loads((DATA / "layer1_contacts_raw.json").read_text(encoding="utf-8"))

    verdicts = {}
    vp = DATA / "au_agency_verdicts.json"
    if vp.exists():
        verdicts = json.loads(vp.read_text(encoding="utf-8"))

    by_domain = defaultdict(set)
    for rec in contacts:
        for e in rec.get("emails") or []:
            e = au1.clean_email(e)
            if not e or builder.BAD_LOCAL.match(e.split("@", 1)[0]):
                continue
            by_domain[rec.get("domain", "")].add(e)

    seen = set()
    for prior in ("instantly_AU.csv", "instantly_AU2.csv"):
        p = DATA / prior
        if p.exists():
            for r in csv.DictReader(p.open(encoding="utf-8")):
                seen.add(r["email"].strip().lower())

    rows, skipped_wrong_business = [], []
    for dom, agency in sorted(agencies.items()):
        if dom in au1.DROP_DOMAINS:
            continue
        v = verdicts.get(dom)
        if v and v["verdict"] == "unclear" and v.get("other_business"):
            skipped_wrong_business.append((dom, v["other_business"]))
            continue
        emails = {e for e in by_domain.get(dom, set())
                  if au1.email_ok_for_site(e, dom) and au2.usable(e, dom)}
        if not emails:
            continue
        ranked = sorted(emails, key=lambda e: (
            0 if builder.NAME_LOCAL.match(e.split("@")[0])
            and not builder.is_generic(e.split("@")[0])
            else 1 if not builder.is_generic(e.split("@")[0]) else 2))
        for e in ranked[:2]:            # 2/domain: the list is big enough now
            if e in seen:
                continue
            seen.add(e)
            fn, ln = builder.guess_name(e.split("@", 1)[0])
            if not au2.plausible_given_name(fn, ln):
                fn, ln = "", ""
            rows.append({
                "email": e, "first_name": fn or "there", "last_name": ln,
                "company_name": au1.clean_company(agency.get("name"), dom),
                "website": au1.clean_website(agency.get("website"), dom),
                "country": "AU", "segment": "AU", "language": "en",
                "source": agency.get("source") or "au_wave3_2026_08",
            })

    out = DATA / "instantly_AU3.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=au1.FIELDS)
        w.writeheader()
        w.writerows(rows)

    named = sum(1 for r in rows if r["first_name"] != "there")
    print(f"agencies in wave 3: {len(agencies)}")
    print(f"rows: {len(rows)} ({named} named), "
          f"{len({r['email'].split('@')[1] for r in rows})} domains -> {out}")
    if skipped_wrong_business:
        print(f"skipped {len(skipped_wrong_business)} domains that read as a "
              f"different business:")
        for d, why in skipped_wrong_business[:10]:
            print(f"  {d}: {', '.join(why)}")


if __name__ == "__main__":
    main()
