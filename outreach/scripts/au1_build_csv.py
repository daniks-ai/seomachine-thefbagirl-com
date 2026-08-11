#!/usr/bin/env python3
"""
Build the Australia-only Instantly import CSV for the [AU] campaign clone.

Sources:
  1. data/au_agencies.jsonl      — new AU domains found via web research (2026-08-10)
     + emails for them from the shared harvest cache (layer1_contacts_raw.json)
  2. instantly_layer{1,2,3}_master.csv — already-built rows with country == AU

Cleanup on top of the shared builder logic:
  - strips url-encoded junk prefixes like "%20" from emails, then re-dedupes
  - trims company names at "|" / " - " / " – " (Google-Maps titles are page titles)
  - strips utm_* query junk from website URLs
  - caps NEW domains at 3 emails (named first) to keep per-company touches sane

Output: data/instantly_AU.csv  (Instantly column layout, segment=AU, language=en)
"""
import csv
import importlib.util
import json
import re
import urllib.parse
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

spec = importlib.util.spec_from_file_location("builder", HERE / "3_build_instantly_csv.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

FIELDS = ["email", "first_name", "last_name", "company_name", "website",
          "country", "segment", "language", "source"]

# template/placeholder domains that show up in page markup, never real inboxes
PLACEHOLDER_DOMAINS = {
    "company.com", "email.com", "mysite.com", "companymail.com", "brand.co",
    "site.com", "example.com", "domain.com", "yourcompany.com", "yourdomain.com",
}
# site domain -> alternate email apex the brand actually uses
ALT_EMAIL_DOMAIN = {"digitalnomadshq.com.au": "dnhq.com.au"}

# hand-reviewed exclusions (2026-08-10): HR/recruiting inboxes, non-AU office
# inboxes of global agencies, and www.-duplicates of an apex address
EXCLUDE_EMAILS = {
    "hr@dotsquares.com", "talent@uplers.com", "itsupport@clixpert.com.au",
    "ihelp@www.idigitalise.net",
    "hellosingapore@tugagency.com", "hellotoronto@tugagency.com",
    "hellonewyork@tugagency.com", "hellolondon@tugagency.com",
    "helloberlin@tugagency.com",
    # non-AU office inboxes of global holdings
    "communications.china@groupm.com", "contact.thailand@groupm.com",
    "hello.groupmsweden@groupm.com",
    "careers@choosedigital.com.au", "careers@connectedm.com.au",
    "sponsorship@marginmedia.com.au",
}

# whole domains mis-attributed to AU in the layer masters (checked 2026-08-10):
# adage.com = Ad Age magazine journalists; sevenatoms = US agency;
# commerixsystems = SERP artifact; gocake.shop = cake shop, not an agency
DROP_DOMAINS = {"adage.com", "sevenatoms.com", "commerixsystems.com", "gocake.shop",
                "nemred.fr", "ideafusionmedia.com.au"}

# master rows carry SERP/GMaps page titles as company names — fix or blank
# (blank -> Instantly falls back to {{companyName|your agency}})
COMPANY_FIX = {
    "creativecircuit.com.au": "Creative Circuit",
    "merge.com.au": "Merge",
    "them.com.au": "THEM Advertising",
    "amazoniac.agency": "",
}


def email_ok_for_site(email, site_domain):
    """On-domain, brand-stem alternate apex, or whitelisted alternate."""
    if email in EXCLUDE_EMAILS:
        return False
    edom = email.split("@", 1)[1]
    if edom in PLACEHOLDER_DOMAINS:
        return False
    local = email.split("@", 1)[0]
    if len(local) > 20 and "." not in local:   # wewelcometheopportunity@…
        return False
    if edom == site_domain or edom.endswith("." + site_domain):
        return True
    if edom == ALT_EMAIL_DOMAIN.get(site_domain):
        return True
    stem = re.sub(r"[^a-z0-9]", "", site_domain.split(".")[0])
    estem = re.sub(r"[^a-z0-9]", "", edom.split(".")[0])
    return len(estem) >= 5 and (stem.startswith(estem) or estem.startswith(stem))


def clean_email(e):
    e = e.strip().lower()
    e = re.sub(r"^(%[0-9a-f]{2})+", "", e)      # "%20support@x" -> "support@x"
    e = e.lstrip(":;,.- \t")   # leading punctuation glued on by page markup
    return e if re.match(r"^[a-z0-9._+-]+@[a-z0-9.-]+\.[a-z]{2,}$", e) else ""


def clean_company(name, domain):
    n = re.split(r"\s*[|–—]\s*| - ", name or "", 1)[0].strip().rstrip(",")
    return n if len(n) >= 3 else domain


def clean_website(url, domain):
    if not url:
        return f"https://{domain}"
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme or "https", parts.netloc, parts.path.rstrip("/"), "", ""))


def main():
    rows, seen = [], set()

    # --- 1. new AU domains + harvested emails -------------------------------
    agencies = {a["domain"]: a for a in builder.load_jsonl(DATA / "au_agencies.jsonl")}
    contacts = json.loads((DATA / "layer1_contacts_raw.json").read_text(encoding="utf-8"))
    # emails found on each site's own pages (record domain -> emails)
    by_domain = defaultdict(set)
    for rec in contacts:
        for e in rec.get("emails") or []:
            e = clean_email(e)
            if not e or builder.BAD_LOCAL.match(e.split("@", 1)[0]):
                continue
            by_domain[rec.get("domain", "")].add(e)

    new_with_email = 0
    for dom, agency in sorted(agencies.items()):
        emails = {e for e in by_domain.get(dom, set()) if email_ok_for_site(e, dom)}
        if not emails:
            continue
        new_with_email += 1
        ranked = sorted(emails, key=lambda e: (
            0 if builder.NAME_LOCAL.match(e.split("@")[0]) and not builder.is_generic(e.split("@")[0])
            else 1 if not builder.is_generic(e.split("@")[0]) else 2))
        for e in ranked[:3]:
            if e in seen:
                continue
            seen.add(e)
            fn, ln = builder.guess_name(e.split("@", 1)[0])
            rows.append({
                "email": e, "first_name": fn or "there", "last_name": ln,
                "company_name": clean_company(agency.get("name"), dom),
                "website": clean_website(agency.get("website"), dom),
                "country": "AU", "segment": "AU", "language": "en",
                "source": "au_web_research_2026_08",
            })

    # --- 2. existing AU rows from the three layer masters -------------------
    kept_prior = 0
    for m in ("instantly_layer1_master.csv", "instantly_layer2_master.csv",
              "instantly_layer3_master.csv"):
        for r in csv.DictReader((DATA / m).open(encoding="utf-8")):
            if r["country"] != "AU":
                continue
            e = clean_email(r["email"])
            if not e or e in seen or e in EXCLUDE_EMAILS:
                continue
            dom = builder.domain_of(e)
            if dom in DROP_DOMAINS:
                continue
            seen.add(e)
            kept_prior += 1
            company = COMPANY_FIX.get(dom, clean_company(r["company_name"], dom))
            rows.append({
                "email": e, "first_name": r["first_name"] or "there",
                "last_name": r["last_name"],
                "company_name": company,
                "website": clean_website(r["website"], dom),
                "country": "AU", "segment": "AU", "language": "en",
                "source": r["source"],
            })

    out = DATA / "instantly_AU.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    named = sum(1 for r in rows if r["first_name"] != "there")
    print(f"new AU domains researched: {len(agencies)}, with >=1 email: {new_with_email}")
    print(f"rows from new research: {len(rows) - kept_prior}")
    print(f"rows carried from layer masters: {kept_prior}")
    print(f"TOTAL rows: {len(rows)} ({named} named, {len(rows) - named} generic)")
    print(f"unique domains: {len({builder.domain_of(r['email']) for r in rows})}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
