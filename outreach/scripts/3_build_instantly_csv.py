#!/usr/bin/env python3
"""
Merge agency firmographics (step 1) with harvested contacts (step 2) into
Instantly-ready CSVs, segmented by region so each campaign clone gets the right
language / persona.

Output columns match what the Instantly importer expects:
    email, first_name, last_name, company_name, website, country, segment, source

- Drops role-less junk and obvious no-reply / privacy addresses.
- Dedupes by email across the whole set.
- Picks ONE best email per domain when several exist (prefers a named/personal
  local-part over generic info@ / contact@), plus keeps generics as fallback rows
  flagged with first_name="there" so copy fallback {{firstName|there}} still works.

Usage:
    python3 outreach/scripts/3_build_instantly_csv.py             # layer 1 (default, legacy filenames)
    python3 outreach/scripts/3_build_instantly_csv.py --layer 2   # layer 2 only, new files,
                                                                  # emails deduped vs layer-1 master
"""
import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"

# US/UK English go to their own clones; everything else groups by language family.
COUNTRY_SEGMENT = {
    "US": ("EN-US", "en"), "CA": ("EN-US", "en"),
    "GB": ("EN-UK", "en"), "IE": ("EN-UK", "en"),
    "AU": ("APAC-EN", "en"), "NZ": ("APAC-EN", "en"), "SG": ("APAC-EN", "en"),
    "IN": ("INDIA", "en"),
    "DE": ("DACH", "de"), "AT": ("DACH", "de"), "CH": ("DACH", "de"),
    "FR": ("EU-FR", "fr"), "BE": ("EU-FR", "fr"),
    "ES": ("EU-ES", "es"), "MX": ("LATAM", "es"), "BR": ("LATAM", "pt"),
    "IT": ("EU-IT", "it"), "NL": ("EU-EN", "en"), "SE": ("EU-EN", "en"),
    "PL": ("EU-EN", "en"), "AE": ("MENA", "en"), "SA": ("MENA", "en"),
    "TR": ("EU-EN", "en"), "JP": ("APAC-EN", "en"),
}
DEFAULT_SEGMENT = ("EN-INTL", "en")

BAD_LOCAL = re.compile(r"^(no-?reply|noreply|privacy|abuse|postmaster|mailer-daemon|"
                       r"webmaster|dns|hostmaster|do-?not-?reply)$", re.I)
# Role words that must never become a "first name" (checked as whole token,
# including the first token of a hyphen/dot-separated local like "info-grp").
ROLE_WORDS = {
    "info", "contact", "hello", "hi", "team", "office", "sales", "support",
    "admin", "enquiries", "inquiries", "enquiry", "inquiry", "mail", "marketing",
    "help", "questions", "question", "product", "products", "billing", "accounts",
    "account", "finance", "hr", "legal", "privacy", "press", "media", "careers",
    "jobs", "job", "service", "services", "orders", "order", "newsletter",
    "partnerships", "partner", "partners", "hola", "bonjour", "kontakt", "ciao",
    "general", "reception", "welcome", "connect", "getstarted", "start", "grow",
    "growth", "agency", "amazon", "ppc", "ads", "advertising", "no", "noreply",
    "everyone", "all", "biz", "business", "company", "corp", "email", "web",
    "website", "data", "it", "dev", "tech", "studio", "clients", "client",
    "people", "connection", "connect", "letstalk", "hey", "talk", "say",
    "wecan", "yes", "go", "book", "meet", "demo", "trial", "signup",
    # job-title inboxes that are never a person's first name
    "founder", "founders", "cofounder", "ceo", "cto", "coo", "cmo", "cfo",
    "owner", "director", "directors", "president", "vp", "head", "chief",
    "manager", "management", "boss", "hq", "headquarters", "principal",
    "trust", "growthteam", "hires", "hiring", "talent", "wearehiring",
}
GENERIC_LOCAL = re.compile(r"^(" + "|".join(sorted(ROLE_WORDS)) + r")$", re.I)


# Substrings that betray a role/function inbox even when concatenated into one
# token (e.g. "customersupport", "bizdev", "newbusiness", "corporatecomms").
ROLE_SUBSTRINGS = (
    "support", "sales", "market", "admin", "billing", "account", "invoice",
    "finance", "invest", "business", "bizdev", "biz", "corporate", "comms",
    "communication", "customer", "service", "career", "recruit", "press",
    "media", "legal", "privacy", "compliance", "sustain", "newbiz", "partner",
    "enquir", "inquir", "info", "contact", "hello", "office", "team", "help",
    "general", "reception", "newsletter", "subscribe", "unsubscribe", "noreply",
)


def _tok(local):
    return re.split(r"[._\-+]", local.lower())


def has_role_substring(local):
    l = local.lower()
    return any(s in l for s in ROLE_SUBSTRINGS)


def is_generic(local):
    toks = [t for t in _tok(local) if t]
    return bool(toks) and toks[0] in ROLE_WORDS


NAME_LOCAL = re.compile(r"^[a-z]+[._-][a-z]+", re.I)  # firstname.lastname style


def load_jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def domain_of(email):
    return email.split("@", 1)[1].lower() if "@" in email else ""


def guess_name(local):
    # firstname.lastname / firstname_lastname / firstname-lastname
    m = re.match(r"^([a-z]{2,})[._-]([a-z]{2,})$", local, re.I)
    if m:
        first, last = m.group(1), m.group(2)
        if first.lower() in ROLE_WORDS:
            return "", ""
        return first.capitalize(), last.capitalize()
    # single-token human name (jane@, raphael@) — real given names are short and
    # carry no role substring. Reject anything that looks like a function inbox.
    if (re.match(r"^[a-z]{3,14}$", local, re.I)
            and re.search(r"[aeiouy]", local, re.I)  # must have a vowel (skip acronyms)
            and local.lower() not in ROLE_WORDS
            and not has_role_substring(local)):
        return local.capitalize(), ""
    return "", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", choices=["1", "2", "3", "4", "5", "all"], default="1",
                    help="which lead layer(s) to build CSVs for")
    args = ap.parse_args()

    agencies = {}
    layer_files = {
        "1": ["layer1_agencies.jsonl"],
        "2": ["layer2_agencies.jsonl"],
        "3": ["layer3_agencies.jsonl"],
        "4": ["layer4_agencies.jsonl"],
        "5": ["layer5_agencies.jsonl"],
        "all": ["layer1_agencies.jsonl", "layer2_agencies.jsonl",
                "layer3_agencies.jsonl", "layer4_agencies.jsonl"],
    }[args.layer]
    for fname in layer_files:
        p = DATA / fname
        if p.exists():
            for a in load_jsonl(p):
                agencies.setdefault(a["domain"], a)

    # contact records accumulate across layers in the harvest cache/file
    contacts_path = DATA / "layer1_contacts_raw.json"
    contacts = json.loads(contacts_path.read_text(encoding="utf-8")) if contacts_path.exists() else []

    # domain -> set(emails)
    by_domain = defaultdict(set)
    for rec in contacts:
        emails = rec.get("emails") or []
        url = rec.get("url") or rec.get("domain") or ""
        for e in emails:
            e = e.strip().lower()
            if "@" not in e:
                continue
            local = e.split("@", 1)[0]
            if BAD_LOCAL.match(local):
                continue
            by_domain[domain_of(e)].add(e)

    seen_emails = set()
    # when building a later layer alone, never re-emit an email already exported
    # by an earlier layer's master (layer 2 dedups vs 1; layer 3 dedups vs 1 + 2)
    prior_masters = {"2": ["instantly_layer1_master.csv"],
                     "3": ["instantly_layer1_master.csv", "instantly_layer2_master.csv"],
                     "4": ["instantly_layer1_master.csv", "instantly_layer2_master.csv",
                           "instantly_layer3_master.csv"],
                     "5": ["instantly_layer1_master.csv", "instantly_layer2_master.csv",
                           "instantly_layer3_master.csv", "instantly_layer4_master.csv"]}
    for mname in prior_masters.get(args.layer, []):
        m = DATA / mname
        if m.exists():
            with m.open(encoding="utf-8") as f:
                seen_emails.update(r["email"].strip().lower() for r in csv.DictReader(f))
    rows = []
    for dom, agency in agencies.items():
        emails = by_domain.get(dom, set())
        # also try matching contacts whose scraped domain differs but agency site matched
        if not emails:
            continue
        # rank: named > generic
        ranked = sorted(emails, key=lambda e: (0 if NAME_LOCAL.match(e.split("@")[0]) and
                                               not is_generic(e.split("@")[0]) else
                                               1 if not is_generic(e.split("@")[0]) else 2))
        country = agency.get("country")
        segment, lang = COUNTRY_SEGMENT.get(country, DEFAULT_SEGMENT)
        for e in ranked:
            if e in seen_emails:
                continue
            seen_emails.add(e)
            local = e.split("@", 1)[0]
            fn, ln = guess_name(local)
            rows.append({
                "email": e,
                "first_name": fn or "there",
                "last_name": ln,
                "company_name": agency.get("company") or dom,
                "website": agency.get("website") or f"https://{dom}",
                "country": country or "",
                "segment": segment,
                "language": lang,
                "source": agency.get("source") or "amazon_ads_partner_directory",
            })

    # write master + per-segment files (layer 1 keeps its legacy filenames)
    suffix = {"1": "layer1", "2": "layer2", "3": "layer3", "4": "layer4", "5": "layer5", "all": "all"}[args.layer]
    master = DATA / f"instantly_{suffix}_master.csv"
    fields = ["email", "first_name", "last_name", "company_name", "website",
              "country", "segment", "language", "source"]
    with master.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    by_seg = defaultdict(list)
    for r in rows:
        by_seg[r["segment"]].append(r)
    seg_dir = DATA / ("instantly_segments" if args.layer == "1" else f"instantly_segments_{suffix}")
    seg_dir.mkdir(exist_ok=True)
    for seg, rs in sorted(by_seg.items()):
        p = seg_dir / f"instantly_{seg}.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rs)

    print(f"agencies with website:   {len(agencies)}")
    print(f"agencies with >=1 email: {sum(1 for d in agencies if by_domain.get(d))}")
    print(f"total unique contact rows: {len(rows)}")
    print(f"named (personal) rows:   {sum(1 for r in rows if r['first_name'] != 'there')}")
    print("by segment:")
    for seg, rs in sorted(by_seg.items(), key=lambda kv: -len(kv[1])):
        print(f"  {seg:10s} {len(rs)}")
    print(f"wrote {master} + {len(by_seg)} segment files in {seg_dir}")


if __name__ == "__main__":
    main()
