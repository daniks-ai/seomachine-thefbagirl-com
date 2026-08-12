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


import re

# Businesses whose own name says they are not a marketing agency. The homepage
# verdict cannot separate these — a print shop's site legitimately says "design"
# and "branding" — but the trading name does.
NOT_AGENCY_NAME = re.compile(
    r"(print|signage|embroidery|promotional products|\b(signs?|"
    r"tradesman|plumbing|electrical|roofing|removalists?|landscap\w+|"
    r"accounting|bookkeep\w+|conveyanc\w+|lawyers?|solicitors?|"
    r"dental|dentist|physio|chiropract\w+|veterinary|"
    r"cafe|restaurant|catering|florist|real estate|realty|pack ?(and|&) ?send|freight|courier|parcel|hosting|promotional product\w*|storage|removals)\b)", re.I)

au2 = _load("au2", HERE / "au2_build_csv.py")
au1, builder = au2.au1, au2.builder


def main():
    agencies = {a["domain"]: a for a in builder.load_jsonl(DATA / "au3_agencies.jsonl")}
    # Private harvest output — the shared layer1_contacts_raw.json is written by
    # any session running 2b/2c and gets clobbered mid-build (see au7).
    contacts = json.loads((DATA / "au3_contacts.json").read_text(encoding="utf-8"))

    verdicts = {}
    vp = DATA / "au_agency_verdicts.json"
    if vp.exists():
        verdicts = json.loads(vp.read_text(encoding="utf-8"))

    # Addresses with no mail route: dead domains plus harvester artifacts where
    # page text got glued onto the domain ("axissocial.com.ausydney").
    dead = set()
    dp = DATA / "au_mx_dead.txt"
    if dp.exists():
        dead = {l.strip().lower() for l in dp.read_text().splitlines() if l.strip()}

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
        # Positive gate, not a negative one. A Maps sweep for "marketing agency"
        # also returns print shops, sign makers, accountants and tradesmen, and
        # no blocklist of "other business" phrases catches them all. Requiring
        # the homepage to actually speak agency does.
        name = agency.get("name") or ""
        if NOT_AGENCY_NAME.search(name) or NOT_AGENCY_NAME.search(dom):
            skipped_wrong_business.append((dom, ["trading name is not an agency"]))
            continue
        v = verdicts.get(dom)
        if v and v["verdict"] != "agency":
            skipped_wrong_business.append((dom, v.get("other_business") or [v["verdict"]]))
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
            if e in seen or e in dead:
                continue
            seen.add(e)
            # Names only from the firstname.lastname pattern. Guessing a name
            # from a single-token local part worked at wave-1/2 scale with a
            # hand-reviewed stop list; across 1,600 domains it produced "Hi
            # Awesome,", "Hi Bangalore," and "Hi Letmework,". A generic
            # greeting costs a little warmth, a wrong name costs the reply.
            fn, ln = builder.guess_name(e.split("@", 1)[0])
            if not ln or not au2.plausible_given_name(fn, ln):
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
