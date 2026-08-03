#!/usr/bin/env python3
"""
Build Instantly-ready CSVs for the KDP outreach from:
  data/raw_agencies.jsonl        {"name","domain","what","country","email"}
  data/raw_bookmarketing.jsonl   same shape
  data/raw_influencers.jsonl     {"first","last","brand","domain","platform_url","reach","focus","email"}
  data/kdp_contacts_raw.json     harvest_kdp.py output [{"domain","emails",...}]

Dedupes domains/emails against every existing Daniks campaign list
(outreach/data/instantly_layer*_master.csv + influencer CSVs).

Outputs:
  data/kdp_domains.txt                     (pre-harvest domain list; run harvest_kdp.py after step 1)
  data/instantly_import_kdp_services.csv   email,first_name,last_name,company_name,website,country,segment,language,source
  data/instantly_import_kdp_influencers.csv  email,first_name,last_name,company,type,platform_url,reach,focus,email_source

Usage:
  python3 outreach/kdp/build_kdp_csv.py --stage domains   # after agents: writes kdp_domains.txt
  python3 outreach/kdp/build_kdp_csv.py --stage csv       # after harvest: writes final CSVs
"""
import argparse
import csv
import json
import re
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
LEGACY = HERE.parent / "data"
INFL_DIRS = [HERE.parent / d for d in ("influencers-en", "influencers-es", "influencers-de")]

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
GENERIC_LOCAL = ("info", "hello", "contact", "support", "team", "office", "mail", "admin", "hi", "inquiries", "enquiries", "sales", "press", "media", "help")


def norm_domain(s):
    if not s:
        return ""
    s = s.strip().lower()
    if "//" in s:
        s = urlparse(s).netloc or s
    s = s.split("/")[0].strip()
    for p in ("www.",):
        if s.startswith(p):
            s = s[len(p):]
    return s if "." in s else ""


def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        line = line.strip().strip("`")
        if not line or line.startswith(("#", "[", "]")):
            continue
        try:
            rows.append(json.loads(line.rstrip(",")))
        except json.JSONDecodeError:
            continue
    return rows


def existing_suppression():
    """Domains + emails already used in any prior Daniks campaign list."""
    domains, emails = set(), set()
    for f in list(LEGACY.glob("instantly_layer*_master.csv")):
        with f.open() as fh:
            for row in csv.DictReader(fh):
                emails.add(row.get("email", "").lower())
                domains.add(norm_domain(row.get("website", "")))
                if "@" in row.get("email", ""):
                    domains.add(row["email"].split("@")[1].lower())
    for d in INFL_DIRS:
        for f in d.glob("*.csv"):
            with f.open() as fh:
                for row in csv.DictReader(fh):
                    e = (row.get("email") or "").lower()
                    if e:
                        emails.add(e)
                        if "@" in e:
                            domains.add(e.split("@")[1])
    sup = LEGACY / "suppress_domains.txt"
    if sup.exists():
        domains |= {norm_domain(x) for x in sup.read_text().splitlines() if x.strip()}
    # KDP round-1: leads already imported into the live Instantly campaigns
    for f in (DATA / "sent").glob("*.csv"):
        with f.open() as fh:
            for row in csv.DictReader(fh):
                e = (row.get("email") or "").lower()
                if e:
                    emails.add(e)
                    if "@" in e:
                        domains.add(e.split("@")[1])
                domains.add(norm_domain(row.get("website", "") or row.get("platform_url", "")))
    r1 = DATA / "round1_domains.txt"
    if r1.exists():
        domains |= {norm_domain(x) for x in r1.read_text().splitlines() if x.strip()}
    domains.discard("")
    emails.discard("")
    return domains, emails


JUNK_HOST = re.compile(r"(sentry|wixpress|example\.|sentry-next|mastodon\.)", re.I)
# placeholders and third-party addresses scraped off testimonial/client links
BLACKLIST = {"example@mail.com", "you@company.com", "jennifer@jenniferbisbing.com",
             "mary@buythebookmarketing.com", "writeon@bobbyhaas.com"}
HEX_LOCAL = re.compile(r"^[0-9a-f]{16,}$")


def sanitize(c):
    if not c:
        return None
    c = c.strip().lower()
    c = re.sub(r"^(%20|%40|u003e|mailto:)+", "", c)  # strip url-encoded junk prefixes
    if not EMAIL_RE.match(c) or c in BLACKLIST:
        return None
    local, host = c.split("@")
    if JUNK_HOST.search(host) or HEX_LOCAL.match(local):
        return None
    if local == "nfo":  # entity-obfuscated "info" with the leading &#105; eaten
        c = "i" + c
    return c


def best_email(cands):
    """Prefer personal-looking locals over generic inboxes."""
    cands = sorted({s for s in (sanitize(c) for c in cands) if s})
    if not cands:
        return None
    personal = [c for c in cands if c.split("@")[0] not in GENERIC_LOCAL and not any(c.split("@")[0].startswith(g) for g in GENERIC_LOCAL)]
    return (personal or cands)[0]


def stage_domains():
    sup_domains, _ = existing_suppression()
    seen, out = set(), []
    for fn in ("raw_agencies.jsonl", "raw_bookmarketing.jsonl", "raw_publishing.jsonl", "raw_directories.jsonl", "raw_influencers.jsonl"):
        for r in load_jsonl(DATA / fn):
            d = norm_domain(r.get("domain", ""))
            if not d or d in seen:
                continue
            seen.add(d)
            if d in sup_domains:
                print(f"  suppressed (already contacted): {d}")
                continue
            out.append(d)
    (DATA / "kdp_domains.txt").write_text("\n".join(out) + "\n")
    print(f"wrote {len(out)} domains -> {DATA/'kdp_domains.txt'}")


def stage_csv():
    sup_domains, sup_emails = existing_suppression()
    harvested = {}
    hp = DATA / "kdp_contacts_raw.json"
    if hp.exists():
        for rec in json.loads(hp.read_text()):
            harvested[norm_domain(rec.get("domain", ""))] = rec.get("emails", [])

    used_emails = set(sup_emails)

    def pick(domain, seed_email):
        cands = list(harvested.get(domain, []))
        if seed_email:
            cands.append(seed_email)
        # keep only on-domain or clearly related emails first
        on_dom = [c for c in cands if c and domain and c.split("@")[-1].lower().endswith(domain)]
        e = best_email(on_dom) or best_email(cands)
        if e and e in used_emails:
            others = [c for c in cands if c.lower() != e and c.lower() not in used_emails]
            e = best_email(others)
        return e

    # services (agencies + book marketing)
    svc_rows, seen_dom = [], set()
    for fn, seg in (("raw_agencies.jsonl", "kdp_ads_agency"), ("raw_bookmarketing.jsonl", "book_marketing"), ("raw_publishing.jsonl", "publishing_services"), ("raw_directories.jsonl", "book_marketing")):
        for r in load_jsonl(DATA / fn):
            d = norm_domain(r.get("domain", ""))
            if not d or d in seen_dom or d in sup_domains:
                continue
            seen_dom.add(d)
            e = pick(d, r.get("email"))
            if not e:
                continue
            used_emails.add(e)
            svc_rows.append({
                "email": e, "first_name": "there", "last_name": "",
                "company_name": r.get("name", ""), "website": f"https://{d}",
                "country": r.get("country", "") or "", "segment": seg,
                "language": "en", "source": "websearch_2026_07",
            })
    f1 = DATA / "instantly_import_kdp_services.csv"
    with f1.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(svc_rows[0].keys()) if svc_rows else ["email"])
        w.writeheader()
        w.writerows(svc_rows)
    print(f"services: {len(svc_rows)} leads -> {f1}")

    # influencers
    inf_rows = []
    for r in load_jsonl(DATA / "raw_influencers.jsonl"):
        d = norm_domain(r.get("domain", ""))
        if d in sup_domains or (d and d in seen_dom):
            continue
        e = pick(d, r.get("email"))
        if not e:
            continue
        used_emails.add(e)
        inf_rows.append({
            "email": e, "first_name": r.get("first", ""), "last_name": r.get("last", ""),
            "company": r.get("brand", ""), "type": "kdp_influencer",
            "platform_url": r.get("platform_url", ""), "reach": r.get("reach", ""),
            "focus": r.get("focus", ""), "email_source": "harvest" if harvested.get(d) else "search",
        })
    f2 = DATA / "instantly_import_kdp_influencers.csv"
    with f2.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(inf_rows[0].keys()) if inf_rows else ["email"])
        w.writeheader()
        w.writerows(inf_rows)
    print(f"influencers: {len(inf_rows)} leads -> {f2}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["domains", "csv"], required=True)
    a = ap.parse_args()
    stage_domains() if a.stage == "domains" else stage_csv()
