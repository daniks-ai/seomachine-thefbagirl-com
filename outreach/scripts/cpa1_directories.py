#!/usr/bin/env python3
"""
E-commerce accountant / CPA vertical, step 1: harvest accounting-firm domains
from free public directories (no paid APIs). Same offer as prep centers:
25% lifetime affiliate — accountants are trusted advisors whose FBA clients
complain to them about ad spend.

Sources:
  A. a2xaccounting.com/ecommerce-accountant-directory — partnerpage.io
     directory, ~100 firms worldwide. Paginated (?page=N); each partner page
     has one external website link + "Country, Region, City" location text.
  B. linkmybooks.com/experts — ~30 firm profiles (UK-heavy); each profile
     page has one external website link.

Output (outreach/data/):
  cpa_firms.jsonl  — {domain, company, website, country, region, source}
  cpa_domains.txt  — one domain per line, deduped vs suppress_domains.txt,
                     agency layers 1-3 and prep_domains.txt (never cross-mail).

Usage:
    python3 outreach/scripts/cpa1_directories.py
    python3 outreach/scripts/cpa1_directories.py --skip-a2x   # fast re-run
"""
import argparse
import concurrent.futures as cf
import html as htmllib
import json
import re
import ssl
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
OUT_JSONL = DATA / "cpa_firms.jsonl"
OUT_DOMAINS = DATA / "cpa_domains.txt"
A2X_CACHE = DATA / "_cpa_a2x_cache.json"
LMB_CACHE = DATA / "_cpa_lmb_cache.json"

UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
      "Accept": "*/*",
      "Accept-Language": "en-US,en;q=0.9"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

COUNTRY_NAMES = {
    "UNITED STATES": "US", "USA": "US", "UNITED KINGDOM": "GB", "UK": "GB",
    "ENGLAND": "GB", "SCOTLAND": "GB", "WALES": "GB", "AUSTRALIA": "AU",
    "CANADA": "CA", "NEW ZEALAND": "NZ", "IRELAND": "IE", "GERMANY": "DE",
    "NETHERLANDS": "NL", "SPAIN": "ES", "FRANCE": "FR", "ITALY": "IT",
    "POLAND": "PL", "PORTUGAL": "PT", "MEXICO": "MX", "BRAZIL": "BR",
    "INDIA": "IN", "PHILIPPINES": "PH", "SINGAPORE": "SG", "HONG KONG": "HK",
    "UNITED ARAB EMIRATES": "AE", "UAE": "AE", "SOUTH AFRICA": "ZA",
    "PAKISTAN": "PK", "ISRAEL": "IL", "CHINA": "CN", "JAPAN": "JP",
}
TLD_COUNTRY = {
    ".co.uk": "GB", ".uk": "GB", ".ca": "CA", ".com.au": "AU", ".au": "AU",
    ".co.nz": "NZ", ".ie": "IE", ".de": "DE", ".nl": "NL", ".es": "ES",
    ".fr": "FR", ".it": "IT", ".pl": "PL", ".pt": "PT", ".com.mx": "MX",
    ".in": "IN", ".ph": "PH", ".sg": "SG", ".hk": "HK", ".ae": "AE",
    ".org.uk": "GB",
}
# hosts that are never the firm's own website
JUNK_HOSTS = re.compile(
    r"(a2xaccounting|partnerpage|linkmybooks|teachable|xero|intuit|quickbooks|"
    r"google|facebook|linkedin|twitter|x\.com|youtube|youtu\.be|instagram|"
    r"calendly|cal\.com|forms\.gle|spotify|visma|apple|amazon|shopify|ebay|"
    r"walmart|etsy|bigcommerce|wix|squarespace|wordpress|webflow|hubspot|"
    r"mailchimp|typeform|whatsapp|wa\.me|bit\.ly|gstatic|umami|"
    r"website-files|cloudfront|cdn\.|\.cdn|unpkg|jsdelivr|cookiebot|"
    r"finaloop|avask|osome)", re.I)


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def domain_of(url):
    m = re.match(r"https?://([^/\s]+)", url.strip())
    if not m:
        return ""
    d = m.group(1).lower().split(":")[0]
    return d[4:] if d.startswith("www.") else d


def country_from_tld(domain):
    for tld, cc in sorted(TLD_COUNTRY.items(), key=lambda kv: -len(kv[0])):
        if domain.endswith(tld):
            return cc
    return None


def country_from_text(html):
    up = html.upper()
    # longest names first so "UNITED KINGDOM" beats "UK" inside other words
    for name in sorted(COUNTRY_NAMES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(name) + r"\b", up):
            return COUNTRY_NAMES[name]
    return None


def external_site(html):
    """First external href that isn't a platform/social/junk host."""
    for url in re.findall(r'href="(https?://[^"\s]+)"', html):
        dom = domain_of(url)
        if dom and not JUNK_HOSTS.search(dom):
            return url, dom
    return "", ""


# ---------- source A: A2X directory ----------

def a2x_slugs():
    slugs, page = set(), 1
    while page <= 40:
        html = fetch(f"https://www.a2xaccounting.com/ecommerce-accountant-directory?page={page}")
        found = set(re.findall(r"/ecommerce-accountant-directory/partner/([a-z0-9-]+)", html))
        new = found - slugs
        slugs |= found
        # tail pages repeat a handful of promoted partners — stop when dry
        if len(new) <= 1:
            break
        page += 1
    return sorted(slugs)


def _a2x_partner(slug):
    html = fetch(f"https://www.a2xaccounting.com/ecommerce-accountant-directory/partner/{slug}")
    site, dom = external_site(html)
    name_m = re.search(r"<title>([^<|]+)", html)
    name = htmllib.unescape(name_m.group(1)).strip() if name_m else slug.replace("-", " ").title()
    # location renders as "Country, Region, City"
    loc_m = re.search(
        r"(United States|United Kingdom|Australia|Canada|New Zealand|Ireland|"
        r"Germany|Netherlands|Spain|France|Italy|Poland|Portugal|Mexico|Brazil|"
        r"India|Philippines|Singapore|Hong Kong|United Arab Emirates|South Africa|"
        r"Pakistan|Israel|China|Japan)\s*,\s*([^,<\"]{2,40})\s*,\s*([^<\"]{2,40})", html)
    country = COUNTRY_NAMES.get(loc_m.group(1).upper()) if loc_m else None
    region = loc_m.group(2).strip() if loc_m else ""
    return {"domain": dom, "company": name, "website": site,
            "country": country or (country_from_tld(dom) if dom else None)
            or country_from_text(html) or "US",
            "region": region, "source": "a2x_directory"}


def scrape_a2x(workers=12):
    slugs = a2x_slugs()
    cache = json.loads(A2X_CACHE.read_text()) if A2X_CACHE.exists() else {}
    todo = [s for s in slugs if s not in cache]
    print(f"  a2x: {len(slugs)} partners ({len(cache)} cached, {len(todo)} to fetch)")
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_a2x_partner, s): s for s in todo}
        for fut in cf.as_completed(futs):
            s = futs[fut]
            try:
                cache[s] = fut.result()
            except Exception as e:  # noqa
                cache[s] = {"error": str(e)[:60]}
    A2X_CACHE.write_text(json.dumps(cache, ensure_ascii=False))
    return [r for r in cache.values() if r and r.get("domain")]


# ---------- source B: Link My Books experts ----------

def _lmb_expert(slug):
    html = fetch(f"https://linkmybooks.com/experts/{slug}")
    site, dom = external_site(html)
    name_m = re.search(r"<title>([^<|]+)", html)
    name = htmllib.unescape(name_m.group(1)).strip() if name_m else slug.replace("-", " ").title()
    name = re.sub(r"\s*(Official partner.*|Approved Partner.*)$", "", name, flags=re.I).strip()
    return {"domain": dom, "company": name, "website": site,
            "country": (country_from_tld(dom) if dom else None)
            or country_from_text(html) or "GB",
            "region": "", "source": "linkmybooks_experts"}


def scrape_lmb(workers=8):
    html = fetch("https://linkmybooks.com/experts")
    slugs = sorted(set(re.findall(r'href="/experts/([a-z0-9-]+)"', html)))
    cache = json.loads(LMB_CACHE.read_text()) if LMB_CACHE.exists() else {}
    todo = [s for s in slugs if s not in cache]
    print(f"  linkmybooks: {len(slugs)} experts ({len(cache)} cached, {len(todo)} to fetch)")
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_lmb_expert, s): s for s in todo}
        for fut in cf.as_completed(futs):
            s = futs[fut]
            try:
                cache[s] = fut.result()
            except Exception as e:  # noqa
                cache[s] = {"error": str(e)[:60]}
    LMB_CACHE.write_text(json.dumps(cache, ensure_ascii=False))
    return [r for r in cache.values() if r and r.get("domain")]


def load_suppress():
    sup = set()
    f = DATA / "suppress_domains.txt"
    if f.exists():
        sup |= {l.strip().lower() for l in f.read_text().splitlines() if l.strip()}
    for stem in ("layer1_domains", "layer2_domains", "layer3_domains", "prep_domains"):
        p = DATA / f"{stem}.txt"
        if p.exists():
            sup |= {l.strip().lower() for l in p.read_text().splitlines() if l.strip()}
    return sup


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-a2x", action="store_true")
    args = ap.parse_args()

    recs = []
    if not args.skip_a2x:
        print("scraping a2x directory…")
        recs += scrape_a2x()

    print("scraping linkmybooks experts…")
    recs += scrape_lmb()

    suppress = load_suppress()
    by_dom = {}
    for r in recs:
        d = r["domain"]
        if not d or d in suppress:
            continue
        if d not in by_dom:  # first source wins (a2x has locations)
            by_dom[d] = r

    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for r in by_dom.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    OUT_DOMAINS.write_text("\n".join(sorted(by_dom)) + "\n")

    by_cc = {}
    for r in by_dom.values():
        by_cc[r["country"]] = by_cc.get(r["country"], 0) + 1
    print(f"\ntotal unique accounting-firm domains: {len(by_dom)}")
    print("by country:", ", ".join(f"{k}:{v}" for k, v in
                                   sorted(by_cc.items(), key=lambda kv: -kv[1])))
    print(f"wrote {OUT_JSONL} + {OUT_DOMAINS}")
    print("next: python3 outreach/scripts/2b_email_harvest.py "
          f"--domains-file {OUT_DOMAINS}")


if __name__ == "__main__":
    main()
