#!/usr/bin/env python3
"""Build the combined INDIA campaign CSV for Instantly.

Merges the three existing INDIA segment CSVs (layers 1-3) with freshly
harvested listicle domains (india_extra_domains.txt + harvest cache),
sanitizes junk emails, dedupes by email, and caps at 2 emails per domain
(named contact first, best generic as fallback).

Output: outreach/data/instantly_INDIA_campaign.csv
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
b = __import__("3_build_instantly_csv")  # reuse filters

DATA = Path(__file__).resolve().parents[1] / "data"
OUT = DATA / "instantly_INDIA_campaign.csv"

EMAIL_OK = re.compile(r"^[a-z0-9][a-z0-9._%+\-]*@[a-z0-9.\-]+\.[a-z]{2,}$")
JUNK_DOMAINS = re.compile(
    r"(example\.|company\.com$|email\.com$|domain\.com$|sentry|wixpress|"
    r"hostingersite\.com$|yourdomain|sitename|godaddy|placeholder)", re.I)
HR_LOCAL = re.compile(r"^(hr|career|careers|jobs|job|recruit(ing|ment)?|talent)$", re.I)

# company names for the listicle domains (from india_candidates.py)
EXTRA_COMPANY = {
    "brandconn.com": "Brandconn Digital", "digidir.com": "DigiDir",
    "digitalasb.com": "Digitalasb Technologies", "digivirus.in": "digiVirus",
    "ecomranker.com": "Ecom Ranker", "entiersoft.com": "Entiersoft",
    "esearchlogix.com": "eSearch Logix", "evoblocs.com": "Evoblocs",
    "globelectra.com": "Globelectra", "iframeweb.com": "iFrameWeb Solutions",
    "jvatec.in": "JVA TEC", "mechwizz.com": "Mechwizz Digital",
    "mediasearchgroup.com": "Media Search Group", "olbuz.com": "OLBUZ",
    "oneclickitsolution.com": "OneClick IT Consultancy",
    "pagetraffic.com": "PageTraffic", "prohed.com": "Prohed",
    "roiminds.com": "ROI Minds", "seojetty.com": "SEO Jetty",
    "seotechexperts.com": "SEO Tech Experts", "seovalley.com": "SEOValley",
    "swiftpropel.com": "SwiftPropel", "themediaant.com": "The Media Ant",
    "whizadvert.com": "Whiz Advert", "wings2sky.com": "Wings2Sky",
    "workingweekends.com": "Working Weekends",
}

FIELDS = ["email", "first_name", "last_name", "company_name", "website",
          "country", "segment", "language", "source"]


def sanitize(email):
    e = email.strip().lower()
    e = re.sub(r"^(%20|mailto:)+", "", e)
    e = e.split("\\")[0].split(",")[0].strip()
    if not EMAIL_OK.match(e):
        return None
    local, host = e.split("@", 1)
    if JUNK_DOMAINS.search(host) or b.BAD_LOCAL.match(local):
        return None
    return e


rows = []

# 1) existing INDIA segment rows (layers 1-3)
for seg_dir in ["instantly_segments", "instantly_segments_layer2", "instantly_segments_layer3"]:
    p = DATA / seg_dir / "instantly_INDIA.csv"
    if not p.exists():
        continue
    with p.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            e = sanitize(r["email"])
            if not e:
                continue
            if HR_LOCAL.match(e.split("@", 1)[0].split(".")[0]):
                continue
            r["email"] = e
            rows.append(r)

# 2) fresh listicle domains from the harvest cache
cache = json.loads((DATA / "_harvest_progress.json").read_text())
for dom in (DATA / "india_extra_domains.txt").read_text().split():
    rec = cache.get(dom) or {}
    for e in rec.get("emails", []):
        e = sanitize(e)
        if not e:
            continue
        local, host = e.split("@", 1)
        # only on-domain emails for listicle leads (drop 3rd-party strays)
        root = dom.split(".")[-2]
        if root not in host:
            continue
        if HR_LOCAL.match(local.split(".")[0]):
            continue
        fn, ln = b.guess_name(local)
        rows.append({
            "email": e, "first_name": fn or "there", "last_name": ln,
            "company_name": EXTRA_COMPANY.get(dom, dom), "website": f"https://{dom}",
            "country": "IN", "segment": "INDIA", "language": "en",
            "source": "india_listicles_2026_08",
        })

# 3) dedupe by email, cap 2 per domain (named first, then non-generic, then generic)
def rank(r):
    local = r["email"].split("@", 1)[0]
    named = r["first_name"] != "there"
    generic = b.is_generic(local)
    return (0 if named else (1 if not generic else 2), r["email"])

seen = set()
by_dom = defaultdict(list)
for r in sorted(rows, key=rank):
    if r["email"] in seen:
        continue
    seen.add(r["email"])
    dom = r["email"].split("@", 1)[1]
    if len(by_dom[dom]) >= 2:
        continue
    by_dom[dom].append(r)

final = [r for rs in by_dom.values() for r in rs]

# company names scraped from <title> carry taglines — cut at separators, cap length
SEP = re.compile(r"\s*[|\-–—:•]\s+")
LEGAL = re.compile(r"\s*(pvt\.?|private)\s+(ltd\.?|limited)\s*$", re.I)
for r in final:
    name = SEP.split(r["company_name"])[0].strip()
    name = LEGAL.sub("", name).strip().rstrip(",.")
    r["company_name"] = (name or r["email"].split("@", 1)[1])[:60]

final.sort(key=lambda r: (r["company_name"].lower(), r["email"]))

with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(final)

named = sum(1 for r in final if r["first_name"] != "there")
print(f"rows: {len(final)} | domains: {len(by_dom)} | named contacts: {named}")
print(f"wrote {OUT}")
