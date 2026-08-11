#!/usr/bin/env python3
"""Build Instantly-ready CSVs for the RU round-2 harvest.

Inputs (working files):
  influencers-ru/r2data/yt_r2_with_email.tsv      — YouTube round 2 (emails inline)
  influencers-ru/r2data/services_longtail.tsv     — services/agencies/edu long tail
  ru-sellers/data/raw_ua_brands.tsv               — UA seller brands
  ru-sellers/data/raw_kz_by_balt_emig.tsv         — KZ/BY/Baltic/emigrant brands
  ru-sellers/data/raw_geo_arm_md.tsv              — GE/AM/MD brands
  outreach/data/layer1_contacts_raw.json          — harvester output (domain -> emails)

Outputs:
  influencers-ru/instantly_import_ru_influencers_r2.csv  (partner-program segment)
  ru-sellers/data/instantly_import_ru_sellers.csv        (direct seller segment)
  ru-sellers/data/ru_r2_master.csv                       (everything incl. excluded, with reasons)

Rules:
  - Only published emails (inline from research or harvested from the org's own site).
  - Junk filter: placeholders, error-tracking, amazon.com, encoded artifacts.
  - Prefer email on own domain; branded freemail allowed if research supplied it.
  - Dedup by email AND by org domain vs all prior Instantly masters + r1 RU CSV
    + KDP CSVs + prep segment CSVs + each other.
  - Exclusion flags (kept in master, not imported): distributor-run, reseller-run,
    by-sanctions-risk, ru-roots, ru-focus, big-corp*, amazon-unconfirmed, dup-org-*,
    dead-guest-email-skip, weak-*, template-factory, aggregator, own-research-tool,
    prep-dedup-check (if found in prep lists), origin-verify, verify-domain.
"""
import csv
import json
import re
import sys
from pathlib import Path

OUT_ROOT = Path(__file__).resolve().parents[1]  # outreach/
R2 = OUT_ROOT / "influencers-ru" / "r2data"
RS = OUT_ROOT / "ru-sellers" / "data"

JUNK_RE = re.compile(
    r"(example@|youremail|name@(email|gmail)|@site\.com|@domen\.|@mysite\.|@error-tracking|"
    r"@sentry|sentry-next|ingest\.sentry|@amazon\.com|zipify|@email\.com|rating@mail\.ru|"
    r"%c2%a0|style=|mailto:|@2x|\.(png|jpg|gif|webp)$|comphone|@may-time|@ekszer-ora|"
    r"jobs@|hr@|press@|press-sekretyar@|@thenumber29\.com|mail@gmail\.com|alex@gmail\.com)",
    re.I,
)
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

EXCLUDE_FLAG_RE = re.compile(
    r"(distributor-run|reseller-run|by-sanctions-risk|ru-roots|ru-focus|big-corp|"
    r"amazon-unconfirmed|dup-org-|dead-guest-email-skip|weak-|template-factory|"
    r"aggregator|own-research-tool|origin-verify|verify-domain|neskromnaya-dup-check)",
    re.I,
)


def base_domain(d: str) -> str:
    d = d.lower().strip().rstrip("/")
    d = re.sub(r"^https?://", "", d).split("/")[0]
    d = re.sub(r"^www\.", "", d)
    return d


def email_domain(e: str) -> str:
    return base_domain(e.split("@", 1)[1]) if "@" in e else ""


def load_suppression():
    emails, domains = set(), set()
    globs = [
        OUT_ROOT / "influencers-ru" / "ru-amazon-influencers.csv",
        *(OUT_ROOT / "data").glob("instantly_*.csv"),
        *(OUT_ROOT / "data" / "instantly_by_campaign").glob("*.csv"),
        *(OUT_ROOT / "data" / "instantly_segments_prep").glob("*.csv"),
        *(OUT_ROOT / "kdp" / "data").glob("instantly_import_*.csv"),
        *(OUT_ROOT / "kdp" / "data" / "sent").glob("*.csv"),
        *(OUT_ROOT / "mx-sellers" / "data").glob("instantly_*.csv"),
    ]
    for p in globs:
        if not p.exists():
            continue
        try:
            with open(p, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    e = (row.get("email") or row.get("Email") or "").strip().lower()
                    if e:
                        emails.add(e)
                        domains.add(email_domain(e))
        except Exception as ex:
            print(f"  warn: {p.name}: {ex}", file=sys.stderr)
    for p in [OUT_ROOT / "data" / "prep_domains.txt"]:
        if p.exists():
            domains.update(base_domain(x) for x in p.read_text().split() if x.strip())
    return emails, domains


def load_harvest():
    m = {}
    p = OUT_ROOT / "data" / "layer1_contacts_raw.json"
    for r in json.loads(p.read_text()):
        d = base_domain(r.get("domain", ""))
        if d and r.get("emails"):
            m[d] = r["emails"]
    return m


def pick_email(inline: str, domain: str, harvest: dict) -> str:
    cands = []
    if inline:
        cands += [x.strip() for x in re.split(r"[;,]", inline) if x.strip()]
    if domain and base_domain(domain) in harvest:
        cands += harvest[base_domain(domain)]
    cleaned = []
    for c in cands:
        c = c.strip().strip("\\").lower()
        c = re.sub(r"^mailto:", "", c)
        if not EMAIL_RE.match(c) or JUNK_RE.search(c):
            continue
        cleaned.append(c)
    if not cleaned:
        return ""
    dom = base_domain(domain) if domain else ""
    # prefer own-domain, then general inbox names, then anything
    own = [c for c in cleaned if dom and email_domain(c) == dom]
    if own:
        pri = [c for c in own if re.match(r"^(info|hello|contact|office|welcome|support|sales|mail|team|customer)", c)]
        return (pri or own)[0]
    return cleaned[0]


def read_tsv(p: Path):
    rows = []
    lines = p.read_text().splitlines()
    hdr = lines[0].split("\t")
    for l in lines[1:]:
        c = l.split("\t")
        rows.append({hdr[i]: (c[i] if i < len(c) else "") for i in range(len(hdr))})
    return rows


def main():
    harvest = load_harvest()
    sup_emails, sup_domains = load_suppression()
    print(f"suppression: {len(sup_emails)} emails, {len(sup_domains)} domains")

    master, partner, sellers = [], [], []
    seen_emails, seen_domains = set(), set()

    def consider(name, domain, country, segment, inline_email, flag, bucket):
        domain = base_domain(domain) if domain and domain != "-" else ""
        email = pick_email(inline_email, domain, harvest)
        reason = ""
        if EXCLUDE_FLAG_RE.search(flag or ""):
            reason = f"flag:{flag}"
        elif not email:
            reason = "no-valid-email"
        elif email in sup_emails or email in seen_emails:
            reason = "dup-email"
        elif domain and (domain in sup_domains or domain in seen_domains):
            reason = "dup-domain"
        elif email_domain(email) in sup_domains:
            reason = "dup-email-domain"
        row = dict(name=name, domain=domain, country=country, segment=segment,
                   email=email, flag=flag, excluded=reason)
        master.append(row)
        if not reason:
            seen_emails.add(email)
            if domain:
                seen_domains.add(domain)
            (partner if bucket == "partner" else sellers).append(row)

    for r in read_tsv(R2 / "yt_r2_with_email.tsv"):
        consider(r["name"], r.get("domain", ""), r.get("country", ""), r.get("segment", ""),
                 r.get("email", ""), r.get("flag", ""), "partner")
    for r in read_tsv(R2 / "services_longtail.tsv"):
        consider(r["name"], r.get("domain", ""), r.get("country", ""), r.get("format", ""),
                 r.get("email", ""), r.get("flag", ""), "partner")
    for p, cc in [(RS / "raw_ua_brands.tsv", "UA"), (RS / "raw_kz_by_balt_emig.tsv", ""),
                  (RS / "raw_geo_arm_md.tsv", ""), (RS / "raw_sellers_r2.tsv", "")]:
        for r in read_tsv(p):
            consider(r["brand"], r.get("domain", ""), r.get("country", cc) or cc,
                     "seller:" + r.get("category", ""), r.get("email", ""), r.get("flag", ""), "sellers")

    def write_instantly(path, rows):
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["email", "first_name", "last_name", "company_name", "website", "country", "segment"])
            for r in rows:
                w.writerow([r["email"], "", "", r["name"],
                            ("https://" + r["domain"]) if r["domain"] else "", r["country"], r["segment"]])

    write_instantly(OUT_ROOT / "influencers-ru" / "instantly_import_ru_influencers_r2.csv", partner)
    write_instantly(RS / "instantly_import_ru_sellers.csv", sellers)
    with open(RS / "ru_r2_master.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(master[0].keys()))
        w.writeheader()
        w.writerows(master)

    print(f"master: {len(master)} | partner import: {len(partner)} | sellers import: {len(sellers)}")
    from collections import Counter
    print("exclusion reasons:", dict(Counter(r['excluded'] for r in master if r['excluded'])))


if __name__ == "__main__":
    main()
