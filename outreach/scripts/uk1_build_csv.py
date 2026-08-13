#!/usr/bin/env python3
"""
Build the UK-only Instantly import CSV for the [UK] campaign clone.

Sources:
  1. data/uk_agencies.jsonl      — new UK domains found via web research (2026-08-11)
     + emails for them from the shared harvest cache (layer1_contacts_raw.json)
  2. instantly_all_master.csv    — already-built rows (layers 1-4) with country == GB

Verification filter: the July run checked the layer-1 english set; GB rows that
FAILED it are dropped (data comes from verified/verified_*.csv vs
emails_to_verify.csv). Rows never checked (layers 2-4) are kept as-is — same
posture as the Aug-10 US upload.

Output: data/instantly_UK.csv  (Instantly column layout, segment=UK, language=en)
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

PLACEHOLDER_DOMAINS = {
    "company.com", "email.com", "mysite.com", "companymail.com", "brand.co",
    "site.com", "example.com", "domain.com", "yourcompany.com", "yourdomain.com",
}
ALT_EMAIL_DOMAIN = {}

# hand-reviewed exclusions (2026-08-11): non-UK office inboxes of multi-office
# agencies (tugagency's London inbox is the RIGHT one here) + harvest artifacts
EXCLUDE_EMAILS = {
    "hellosingapore@tugagency.com", "hellotoronto@tugagency.com",
    "hellonewyork@tugagency.com", "helloberlin@tugagency.com",
    "apac@mcsaatchiperformance.com", "us@mcsaatchiperformance.com",
    "capetown@thiswayup.online", "dubai@thiswayup.online",
    "manila@thiswayup.online",
    "prague@vccp.com", "vccpspain@vccp.com",
    "asia@sociallypowerful.com", "mena@sociallypowerful.com",
    "usa@sociallypowerful.com", "uae@unpackmarketplaces.com",
    "5532info@applewoodmarketing.co.uk",   # harvest artifact; info@ also present
}
EXCLUDE_LOCAL = re.compile(
    r"^(careers?|jobs?|hr|talent|recruit(ing|ment)?|press|sponsorship|joinus|"
    r"peopleandculture|uscareers|accounts?|billing|studio|production|composer|"
    r"music|bookings|briefs|events|pr|publishers)$")

# adtech/SaaS vendors, production studios and global-holdco apex domains whose
# harvested inboxes can't be attributed to the UK office (checked 2026-08-11)
DROP_DOMAINS = {
    "jivox.com", "onaudience.com", "amillionads.com", "elementhuman.com",
    "shimmr.ai", "cavai.com", "creatoriq.com", "usetwirl.com",
    "weareilluma.com", "foreveraudio.com", "packshotsdirect.com",
    "perspectivepictures.com", "beamgroup.co.uk", "whatsales.io",
    "twospouts.com", "havas.com", "cheil.com", "omnicommediagroup.com",
    "pmg.com", "ecomva.com",
    # deep-harvest additions: SaaS tools / non-UK / junk-only inboxes
    "competera.net", "croud.com", "nozzle.ai", "sellertoolkit.co.uk",
    "vyper.global",
    # round 2 (2026-08-11): global holdco networks (same call as havas/omnicom)
    # and a 3PL that belongs to the prep-centre offer, not the agency one
    "inizioevoke.com", "zenithmedia.com", "danum3pl.com",
}

# same brand, foreign office: the UK inbox is already in the list, so mailing
# these would be a second touch to one company aimed at the wrong country
FOREIGN_OFFICE_TLD = re.compile(r"\.(com\.au|co\.nz|in|ae|sg|za|co\.za|ca|us)$")
MAX_PER_DOMAIN = 3

# master rows carry SERP/GMaps page titles as company names — fix or blank
# (blank -> Instantly falls back to {{companyName|your agency}})
COMPANY_FIX = {
    "castle.co.uk": "Castle",
    "helloseed.co.uk": "Seed",
    "fndecommerce.com": "FND Ecommerce",
    "found.co.uk": "Found",
    "bark.london": "Bark London",
    "onlineselleruk.com": "Online Seller UK",
    "amazonppc.co.uk": "",
    "amazon-consultant.co.uk": "",
    "riseup.agency": "RiseUp Agency",
    "swypecreative.com": "Swype Creative",
}


def email_ok_for_site(email, site_domain):
    if email in EXCLUDE_EMAILS:
        return False
    local, edom = email.split("@", 1)
    if edom in PLACEHOLDER_DOMAINS or EXCLUDE_LOCAL.match(local):
        return False
    if len(local) > 20 and "." not in local:
        return False
    if edom == site_domain or edom.endswith("." + site_domain):
        return True
    if edom == ALT_EMAIL_DOMAIN.get(site_domain):
        return True
    stem = re.sub(r"[^a-z0-9]", "", site_domain.split(".")[0])
    estem = re.sub(r"[^a-z0-9]", "", edom.split(".")[0])
    return len(estem) >= 5 and (stem.startswith(estem) or estem.startswith(stem))


# guess_name capitalizes any local part; these are inbox labels, not people
JUNK_FIRST = {"talktouk", "tellmemore", "usa", "letsgo", "amteam", "lift.off",
              "tellme", "newbiz", "salut", "czesc", "hallo"}


def fix_first(fn, ln):
    if fn and not ln and fn.lower() in JUNK_FIRST:
        return "there"
    return fn or "there"


def clean_email(e):
    e = e.strip().lower()
    e = re.sub(r"^(%[0-9a-f]{2})+", "", e)
    e = e.lstrip(":;,. ")
    return e if re.match(r"^[a-z0-9._+-]+@[a-z0-9.-]+\.[a-z]{2,}$", e) else ""


def clean_company(name, domain):
    n = re.split(r"\s*[|–—]\s*| - ", name or "", 1)[0].strip().rstrip(",")
    n = n.strip('"® ').replace("®", "")
    if len(n) < 3 or n.lower() == domain.lower():
        return ""          # -> Instantly {{companyName|your agency}} fallback
    return n


def clean_website(url, domain):
    if not url:
        return f"https://{domain}"
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme or "https", parts.netloc, parts.path.rstrip("/"), "", ""))


def load_verification_sets():
    checked = set()
    with (DATA / "emails_to_verify.csv").open(encoding="utf-8") as f:
        next(f)
        for line in f:
            e = line.strip().lower()
            if "@" in e:
                checked.add(e)
    passed = set()
    for p in (DATA / "verified").glob("verified_*.csv"):
        for r in csv.DictReader(p.open(encoding="utf-8")):
            e = (r.get("email") or "").strip().lower()
            if "@" in e:
                passed.add(e)
    return checked, passed


def main():
    rows, seen = [], set()
    checked, passed = load_verification_sets()

    # --- 1. new UK domains + harvested emails -------------------------------
    agencies = {a["domain"]: a for a in builder.load_jsonl(DATA / "uk_agencies.jsonl")}
    contacts = json.loads((DATA / "layer1_contacts_raw.json").read_text(encoding="utf-8"))
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
                "email": e, "first_name": fix_first(fn, ln), "last_name": ln,
                "company_name": clean_company(agency.get("name"), dom),
                "website": clean_website(agency.get("website"), dom),
                "country": "GB", "segment": "UK", "language": "en",
                "source": "uk_web_research_2026_08",
            })

    # --- 2. existing GB rows from the all-layers master ---------------------
    # collected per domain first so MAX_PER_DOMAIN can rank named inboxes ahead
    dropped_failed = 0
    per_domain = defaultdict(list)
    for r in csv.DictReader((DATA / "instantly_all_master.csv").open(encoding="utf-8")):
        if r["country"] != "GB":
            continue
        e = clean_email(r["email"])
        if not e or e in seen or e in EXCLUDE_EMAILS:
            continue
        if EXCLUDE_LOCAL.match(e.split("@", 1)[0]):
            continue
        if e in checked and e not in passed:
            dropped_failed += 1
            continue
        dom = builder.domain_of(e)
        if dom in DROP_DOMAINS:
            continue
        per_domain[dom].append((e, r))

    def rank(item):
        local = item[0].split("@", 1)[0]
        if builder.NAME_LOCAL.match(local) and not builder.is_generic(local):
            return 0
        return 1 if not builder.is_generic(local) else 2

    kept_prior = 0
    for dom in sorted(per_domain):
        for e, r in sorted(per_domain[dom], key=rank)[:MAX_PER_DOMAIN]:
            if e in seen:
                continue
            seen.add(e)
            kept_prior += 1
            company = COMPANY_FIX.get(dom, clean_company(r["company_name"], dom))
            rows.append({
                "email": e, "first_name": fix_first(r["first_name"], r["last_name"]),
                "last_name": r["last_name"],
                "company_name": company,
                "website": clean_website(r["website"], dom),
                "country": "GB", "segment": "UK", "language": "en",
                "source": r["source"],
            })

    # --- 3. GB layer domains cracked by the deep harvest (2c) ---------------
    # these had no email at master-build time, so they exist only in the
    # contacts cache; layer jsonls supply name/website metadata
    meta = {}
    for lf in ("layer1_agencies.jsonl", "layer2_agencies.jsonl",
               "layer3_agencies.jsonl", "layer4_agencies.jsonl"):
        p = DATA / lf
        if not p.exists():
            continue
        for a in builder.load_jsonl(p):
            if (a.get("country") or "").upper() in ("GB", "UK"):
                meta.setdefault(a["domain"].lower().removeprefix("www."), a)

    deep_added = 0
    deep_doms = (DATA / "uk_domains_noemail.txt").read_text().split()
    for dom in sorted(deep_doms):
        if dom in DROP_DOMAINS:
            continue
        emails = {e for e in by_domain.get(dom, set())
                  if email_ok_for_site(e, dom)
                  and not EXCLUDE_LOCAL.match(e.split("@", 1)[0])
                  and not (e in checked and e not in passed)}
        ranked = sorted(emails, key=lambda e: (
            0 if builder.NAME_LOCAL.match(e.split("@")[0]) and not builder.is_generic(e.split("@")[0])
            else 1 if not builder.is_generic(e.split("@")[0]) else 2))
        m = meta.get(dom, {})
        for e in ranked[:MAX_PER_DOMAIN]:
            if e in seen or e in EXCLUDE_EMAILS:
                continue
            seen.add(e)
            deep_added += 1
            fn, ln = builder.guess_name(e.split("@", 1)[0])
            rows.append({
                "email": e, "first_name": fix_first(fn, ln), "last_name": ln,
                "company_name": COMPANY_FIX.get(dom, clean_company(m.get("name"), dom)),
                "website": clean_website(m.get("website"), dom),
                "country": "GB", "segment": "UK", "language": "en",
                "source": "uk_deep_harvest_2026_08",
            })

    out = DATA / "instantly_UK.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    named = sum(1 for r in rows if r["first_name"] != "there")
    print(f"new UK domains researched: {len(agencies)}, with >=1 email: {new_with_email}")
    print(f"rows from new research: {len(rows) - kept_prior - deep_added}")
    print(f"rows carried from all-layers master: {kept_prior} (dropped {dropped_failed} failed-verification)")
    print(f"rows from deep harvest of no-email GB domains: {deep_added}")
    print(f"TOTAL rows: {len(rows)} ({named} named, {len(rows) - named} generic)")
    print(f"unique domains: {len({builder.domain_of(r['email']) for r in rows})}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
