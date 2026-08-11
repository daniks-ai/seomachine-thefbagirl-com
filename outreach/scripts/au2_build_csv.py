#!/usr/bin/env python3
"""
Wave-2 CSV for the [AU] campaign: broad-ICP Australian agencies
(digital marketing / ecommerce / Google Ads / Shopify) from
data/au2_agencies.jsonl (Apify Google Maps + directory sweeps).

Reuses the cleaning helpers of au1_build_csv.py, caps 3 emails/domain,
dedupes against wave 1 (instantly_AU.csv).

Output: data/instantly_AU2.csv
"""
import csv
import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

# HR / press / finance inboxes never reach a decision maker on a cold pitch
ROLE_JUNK = re.compile(r"^(careers?|hr|jobs?|recruit\w*|hiring|talent|apply|"
                       r"internships?|press|media|legal|billing|"
                       r"accounts?|invoices?|payroll|privacy)@", re.I)

# Local parts of overseas-office inboxes: mailing an AU agency's New York desk
# about Australian Amazon PPC lands wrong. Keep AU cities, drop the rest.
FOREIGN_OFFICE = re.compile(
    r"^(usa?|uk|india|singapore|newyork|ny|london|berlin|toronto|dubai|"
    r"manila|auckland|nz|hongkong|shanghai|tokyo|paris|amsterdam|"
    r"losangeles|vancouver|chicago|boston|seattle|dublin|mumbai|delhi)@", re.I)

# Escape sequences that leaked out of page markup and got glued to a local part
# ("u003econtact@", "nhello@" from a literal \n, "u002f@"). The address is wrong,
# not merely ugly — sending to it bounces.
ESCAPE_ARTIFACT = re.compile(
    r"^(u00[0-9a-f]{2}|x[0-9a-f]{2}"
    r"|[nrt](?=hello@|info@|contact@|team@|support@|sales@|enquiries@))", re.I)

# Two-letter ccTLDs that read as "another country's office" for an AU brand.
# .co/.io/.ai/.me/.tv and friends are sold as generic vanity TLDs, so they stay.
GENERIC_SHORT_TLD = {"co", "io", "ai", "me", "tv", "cc", "ly", "sh", "gg", "fm", "au"}


def foreign_cc(domain):
    tld = domain.rsplit(".", 1)[-1].lower()
    return len(tld) == 2 and tld not in GENERIC_SHORT_TLD

# Words that are never a person's given name but pass builder.guess_name's
# "short single token with a vowel" test — greetings, service words, cities.
NOT_A_NAME = {
    "howdy", "hallo", "cheerio", "hiya", "gday", "yo", "oi", "aloha",
    "engage", "solutions", "solution", "campaign", "campaigns", "requests",
    "request", "beheard", "digital", "creative", "studio", "agency", "grow",
    "growth", "bookings", "booking", "quotes", "quote", "leads", "lead",
    "sydney", "melbourne", "brisbane", "perth", "adelaide", "canberra",
    "hobart", "darwin", "cairns", "geelong", "newcastle", "australia",
    "australian", "usa", "india", "singapore", "newyork", "london",
    "ask", "discovery", "ideas", "idea", "ignite", "innovation", "projects",
    "project", "success", "work", "win", "hoot", "oink", "hauskeeping",
    "fiji", "losangeles", "vancouver", "enquire", "apply", "join", "explore",
    # hand-reviewed 2026-08-11: first+last glued together, under the length cap
    "jasonsuli", "lucywang", "margiereid", "taihlaura",
    # hand-reviewed 2026-08-11 (wave 2): initials+surname, greeting+city codes,
    # and plural service words that guess_name reads as a given name
    "design", "humans", "drichards", "jclarke", "kerryw", "maac", "corbs",
    "heyqt", "heysc", "heysyd", "konstans", "chender",
    "proposals", "seo", "thowe",
}


def usable(email, site_domain):
    """Reject addresses that would bounce or land in the wrong country."""
    local, edom = email.split("@", 1)
    if ROLE_JUNK.match(email) or FOREIGN_OFFICE.match(email):
        return False
    if ESCAPE_ARTIFACT.match(email):
        return False
    if edom.startswith("www."):          # www-subdomain twin of the apex address
        return False
    # a .co.nz / .fr twin of an AU brand's inbox is that brand's other market
    if foreign_cc(edom) and not edom.endswith(".au") and not site_domain.endswith(edom.rsplit(".", 1)[-1]):
        return foreign_cc(site_domain) and site_domain.rsplit(".", 1)[-1] == edom.rsplit(".", 1)[-1]
    return True


def plausible_given_name(fn, ln):
    """Reject junk that survived guess_name: service words and locals that are
    a whole name glued together ("jasonsuli", "margiereid") — greeting someone
    by a mashed-up string reads worse than the generic fallback."""
    if not fn:
        return False
    if fn.lower() in NOT_A_NAME:
        return False
    # single-token locals only: a real given name is short; 11+ chars with no
    # separator is almost always first+last concatenated
    return bool(ln) or len(fn) <= 10

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

spec = importlib.util.spec_from_file_location("au1", HERE / "au1_build_csv.py")
au1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(au1)
builder = au1.builder


def main():
    agencies = {a["domain"]: a for a in builder.load_jsonl(DATA / "au2_agencies.jsonl")}
    contacts = json.loads((DATA / "layer1_contacts_raw.json").read_text(encoding="utf-8"))
    by_domain = defaultdict(set)
    for rec in contacts:
        for e in rec.get("emails") or []:
            e = au1.clean_email(e)
            if not e or builder.BAD_LOCAL.match(e.split("@", 1)[0]):
                continue
            by_domain[rec.get("domain", "")].add(e)

    seen = set()
    for r in csv.DictReader((DATA / "instantly_AU.csv").open(encoding="utf-8")):
        seen.add(r["email"].strip().lower())

    rows, dom_hits = [], 0
    for dom, agency in sorted(agencies.items()):
        if dom in au1.DROP_DOMAINS:
            continue
        emails = {e for e in by_domain.get(dom, set())
                  if au1.email_ok_for_site(e, dom) and usable(e, dom)}
        if not emails:
            continue
        dom_hits += 1
        ranked = sorted(emails, key=lambda e: (
            0 if builder.NAME_LOCAL.match(e.split("@")[0]) and not builder.is_generic(e.split("@")[0])
            else 1 if not builder.is_generic(e.split("@")[0]) else 2))
        for e in ranked[:3]:
            if e in seen:
                continue
            seen.add(e)
            fn, ln = builder.guess_name(e.split("@", 1)[0])
            if not plausible_given_name(fn, ln):
                fn, ln = "", ""
            rows.append({
                "email": e, "first_name": fn or "there", "last_name": ln,
                "company_name": au1.clean_company(agency.get("name"), dom),
                "website": au1.clean_website(agency.get("website"), dom),
                "country": "AU", "segment": "AU", "language": "en",
                "source": agency.get("source") or "au_wave2_2026_08",
            })

    out = DATA / "instantly_AU2.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=au1.FIELDS)
        w.writeheader()
        w.writerows(rows)
    named = sum(1 for r in rows if r["first_name"] != "there")
    print(f"agencies: {len(agencies)}, with emails: {dom_hits}")
    print(f"rows: {len(rows)} ({named} named) | wrote {out}")


if __name__ == "__main__":
    main()
