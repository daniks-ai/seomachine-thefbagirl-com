#!/usr/bin/env python3
"""
Build Instantly-ready CSVs for the GERMAN (DACH) KDP outreach round.

Inputs (research-agent output, JSONL):
  data/de/raw_agencies.jsonl        {"name","domain","what","country","email"}   -> services
  data/de/raw_services.jsonl        same shape (selfpub dienstleister)           -> services
  data/de/raw_lowcontent_ghost.jsonl same shape; "what" marks lowcontent|ghostwriting
                                     -> lowcontent=publishers, ghostwriting=services
  data/de/raw_publishers.jsonl      same shape (indie presses, own catalog)      -> publishers
  data/de/raw_promo.jsonl           same shape (book PR / promo / deal newsletters) -> partners
  data/de/raw_influencers.jsonl     {"first","last","brand","domain","platform_url","reach","focus","email"} -> partners

Harvest: reuses harvest_deep.py output (data/kdp_contacts_deep.json, keyed by domain).

Outputs:
  data/de/kdp_de_domains.txt                       (pre-harvest domain list)
  data/de/instantly_import_kdp_services_de.csv     white-label letter
  data/de/instantly_import_kdp_partners_de.csv     25% lifetime partner letter
  data/de/instantly_import_kdp_publishers_de.csv   direct offer letter

Usage:
  python3 outreach/kdp/build_kdp_de_csv.py --stage domains
  python3 outreach/kdp/build_kdp_de_csv.py --stage csv
"""
import argparse
import csv
import json
from pathlib import Path

import build_kdp_csv as base  # suppression, sanitize, best_email, norm_domain, load_jsonl

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DE = DATA / "de"
ROUND_SUFFIX = "_r2"

ORG_FILES = [
    ("raw_agencies.jsonl", "kdp_ads_agency_de", "services"),
    ("raw_services.jsonl", "publishing_services_de", "services"),
    ("raw_lowcontent_ghost.jsonl", None, None),  # routed per-row below
    ("raw_publishers.jsonl", "indie_publisher_de", "publishers"),
    ("raw_promo.jsonl", "book_promo_de", "partners"),
    # --- round 2 (2026-08-11) ---
    ("r2_agencies_ghost.jsonl", None, None),     # routed per-row below
    ("r2_publishers.jsonl", "indie_publisher_de", "publishers"),
    ("r2_lowcontent.jsonl", "lowcontent_publisher_de", "publishers"),
    ("r2_freelancers.jsonl", "book_freelancer_de", "partners"),
    ("r2_bloggers.jsonl", "book_blogger_de", "partners"),
    ("r2_directory.jsonl", None, None),          # routed per-row below
    # --- directory scrapes (email already present, no harvest needed) ---
    ("dir_sbvv.jsonl", "ch_publisher_sbvv", "publishers"),
]

# {"first","last","brand",...} shape rather than {"name",...}
PERSON_FILES = [
    ("raw_influencers.jsonl", "kdp_influencer_de", "partners"),
    ("r2_coaches.jsonl", "kdp_coach_de", "partners"),
    ("r2_authors.jsonl", "indie_author_de", "authors"),
    ("dir_lektoren.jsonl", "vfll_lektor_de", "partners"),
    ("dir_spv.jsonl", "selfpublisher_spv_de", "authors"),
]


def route_lowcontent(row):
    """`what` carries a segment marker (lowcontent|ghostwriting|agency|...)."""
    what = (row.get("what") or "").lower()
    if "ghost" in what:
        return "ghostwriting_de", "services"
    if "agency" in what or "agentur" in what:
        return "kdp_ads_agency_de", "services"
    if any(k in what for k in ("blog", "podcast", "coach", "promo", "newsletter")):
        return "book_promo_de", "partners"
    if any(k in what for k in ("lektorat", "cover", "satz", "hörbuch", "freelanc")):
        return "book_freelancer_de", "partners"
    if any(k in what for k in ("verlag", "publisher", "presse")):
        return "indie_publisher_de", "publishers"
    return "lowcontent_publisher_de", "publishers"


def iter_orgs():
    for fn, seg, bucket in ORG_FILES:
        for r in base.load_jsonl(DE / fn):
            s, b = (seg, bucket) if seg else route_lowcontent(r)
            yield r, s, b


def iter_people():
    for fn, seg, bucket in PERSON_FILES:
        for r in base.load_jsonl(DE / fn):
            yield r, seg, bucket


def stage_domains():
    sup_domains, _ = base.existing_suppression()
    seen, out = set(), []
    rows = [r for r, _, _ in iter_orgs()] + [r for r, _, _ in iter_people()]
    for r in rows:
        d = base.norm_domain(r.get("domain", ""))
        if not d or d in seen:
            continue
        seen.add(d)
        if d in sup_domains:
            print(f"  suppressed (already contacted): {d}")
            continue
        out.append(d)
    (DE / "kdp_de_domains.txt").write_text("\n".join(out) + "\n")
    print(f"wrote {len(out)} domains -> {DE/'kdp_de_domains.txt'}")


def stage_csv():
    sup_domains, sup_emails = base.existing_suppression()
    # merge every harvester pass; later files win on ties but we union the lists
    harvested = {}
    for fn in ("kdp_contacts_deep.json", "kdp_contacts_crawl.json"):
        hp = DATA / fn
        if not hp.exists():
            continue
        for rec in json.loads(hp.read_text()):
            d = base.norm_domain(rec.get("domain", ""))
            harvested.setdefault(d, [])
            for e in rec.get("emails", []):
                if e not in harvested[d]:
                    harvested[d].append(e)

    used_emails = set(sup_emails)

    def pick(domain, seed_email):
        cands = list(harvested.get(domain, []))
        if seed_email:
            cands.append(seed_email)
        on_dom = [c for c in cands if c and domain and c.split("@")[-1].lower().endswith(domain)]
        e = base.best_email(on_dom) or base.best_email(cands)
        if e and e in used_emails:
            others = [c for c in cands if c.lower() != e and c.lower() not in used_emails]
            e = base.best_email(others)
        return e

    buckets = {"services": [], "partners": [], "publishers": [], "authors": []}
    seen_dom = set()

    for r, seg, bucket in iter_orgs():
        d = base.norm_domain(r.get("domain", ""))
        if not d or d in seen_dom or d in sup_domains:
            continue
        seen_dom.add(d)
        e = pick(d, r.get("email"))
        if not e:
            continue
        used_emails.add(e)
        buckets[bucket].append({
            "email": e, "first_name": "", "last_name": "",
            "company_name": r.get("name", ""), "website": f"https://{d}",
            "country": r.get("country", "") or "DE", "segment": seg,
            "language": "de", "source": "websearch_2026_08",
        })

    for r, seg, bucket in iter_people():
        d = base.norm_domain(r.get("domain", ""))
        if d and (d in seen_dom or d in sup_domains):
            continue
        if d:
            seen_dom.add(d)
        e = pick(d, r.get("email"))
        if not e:
            continue
        used_emails.add(e)
        buckets[bucket].append({
            "email": e, "first_name": r.get("first", ""), "last_name": r.get("last", ""),
            "company_name": r.get("brand", ""),
            "website": r.get("platform_url", "") or (f"https://{d}" if d else ""),
            "country": r.get("country", "") or "DE", "segment": seg,
            "language": "de", "source": "websearch_2026_08",
        })

    fields = ["email", "first_name", "last_name", "company_name", "website",
              "country", "segment", "language", "source"]
    for bucket, rows in buckets.items():
        f = DE / f"instantly_import_kdp_{bucket}_de{ROUND_SUFFIX}.csv"
        with f.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"{bucket}: {len(rows)} leads -> {f}")

    got = {base.norm_domain(r["website"]) for rows in buckets.values() for r in rows}
    no_email = [d for d in seen_dom if d not in got]
    (DE / f"no_email_de{ROUND_SUFFIX}.txt").write_text("\n".join(sorted(no_email)) + "\n")
    print(f"no email: {len(no_email)} domains -> {DE/f'no_email_de{ROUND_SUFFIX}.txt'}")
    print(f"TOTAL: {sum(len(v) for v in buckets.values())} leads")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["domains", "csv"], required=True)
    ap.add_argument("--round", default="_r2",
                    help="suffix for the output files; '' reproduces round 1")
    a = ap.parse_args()
    globals()["ROUND_SUFFIX"] = a.round
    DE.mkdir(exist_ok=True)
    stage_domains() if a.stage == "domains" else stage_csv()
