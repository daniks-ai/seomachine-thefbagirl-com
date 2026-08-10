#!/usr/bin/env python3
"""
Prep-center vertical, step 1: harvest prep-center domains from free public
directories (no paid APIs).

Sources:
  A. selleressentials.com/amazon-fba-prep-services/  — tablepress tables,
     entries grouped under bold STATE/COUNTRY markers, direct website links.
  B. hopstack.io FBA-prep-center directory — sitemap lists ~320 subpages;
     each has a "Visit website" anchor (often empty href="#") + a description
     like "... based in Montana, USA ...".
  C. rocketsource.io/amazon-fba-prep-services — single page, best-effort
     (rate-limited; skipped gracefully on 429).

Output (outreach/data/):
  prep_centers.jsonl  — {domain, company, website, country, region, source}
  prep_domains.txt    — one domain per line, deduped vs suppress_domains.txt
                        and agency layers 1-3 (never cross-mail a domain).

Usage:
    python3 outreach/scripts/prep1_directories.py
    python3 outreach/scripts/prep1_directories.py --skip-hopstack   # fast re-run
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
OUT_JSONL = DATA / "prep_centers.jsonl"
OUT_DOMAINS = DATA / "prep_domains.txt"
HOPSTACK_CACHE = DATA / "_prep_hopstack_cache.json"

UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
      "Accept": "text/html"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

US_STATES = {
    "ALABAMA", "ALASKA", "ARIZONA", "ARKANSAS", "CALIFORNIA", "COLORADO",
    "CONNECTICUT", "DELAWARE", "FLORIDA", "GEORGIA", "HAWAII", "IDAHO",
    "ILLINOIS", "INDIANA", "IOWA", "KANSAS", "KENTUCKY", "LOUISIANA", "MAINE",
    "MARYLAND", "MASSACHUSETTS", "MICHIGAN", "MINNESOTA", "MISSISSIPPI",
    "MISSOURI", "MONTANA", "NEBRASKA", "NEVADA", "NEW HAMPSHIRE", "NEW JERSEY",
    "NEW MEXICO", "NEW YORK", "NORTH CAROLINA", "NORTH DAKOTA", "OHIO",
    "OKLAHOMA", "OREGON", "PENNSYLVANIA", "RHODE ISLAND", "SOUTH CAROLINA",
    "SOUTH DAKOTA", "TENNESSEE", "TEXAS", "UTAH", "VERMONT", "VIRGINIA",
    "WASHINGTON", "WEST VIRGINIA", "WISCONSIN", "WYOMING",
}
COUNTRY_MARKERS = {
    "CANADA": "CA", "UNITED KINGDOM": "GB", "UK": "GB", "ENGLAND": "GB",
    "SCOTLAND": "GB", "WALES": "GB", "GERMANY": "DE", "MEXICO": "MX",
    "CHINA": "CN", "AUSTRALIA": "AU", "NETHERLANDS": "NL", "SPAIN": "ES",
    "FRANCE": "FR", "ITALY": "IT", "POLAND": "PL", "UAE": "AE",
    "UNITED ARAB EMIRATES": "AE", "JAPAN": "JP", "INDIA": "IN",
    "VIETNAM": "VN", "TURKEY": "TR", "IRELAND": "IE", "PORTUGAL": "PT",
    "CZECH REPUBLIC": "CZ", "BULGARIA": "BG", "ESTONIA": "EE",
}
TLD_COUNTRY = {
    ".co.uk": "GB", ".uk": "GB", ".ca": "CA", ".de": "DE", ".fr": "FR",
    ".es": "ES", ".it": "IT", ".nl": "NL", ".pl": "PL", ".com.au": "AU",
    ".com.mx": "MX", ".ae": "AE", ".in": "IN", ".ie": "IE", ".cn": "CN",
    ".jp": "JP", ".pt": "PT", ".cz": "CZ", ".bg": "BG", ".ee": "EE",
}
# platforms/marketplaces/SaaS that appear in directory pages but are not leads
JUNK_DOMAINS = {
    "amazon.com", "sellercentral.amazon.com", "shopify.com", "ebay.com",
    "walmart.com", "selleressentials.com", "hopstack.io", "rocketsource.io",
    "prepcenter.com", "google.com", "facebook.com", "youtube.com", "x.com",
    "twitter.com", "linkedin.com", "instagram.com", "wa.me", "whatsapp.com",
    "calendly.com", "bit.ly", "wordpress.com", "wix.com", "godaddy.com",
}


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


def scrape_selleressentials():
    html = fetch("https://selleressentials.com/amazon-fba-prep-services/")
    recs = []
    for table in re.findall(r'<table[^>]*class="[^"]*tablepress[^"]*"[^>]*>(.*?)</table>',
                            html, re.S):
        current = None
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
            marker = re.search(r"<b>([^<]+)</b>", row)
            if marker:
                current = re.sub(r"\s+", " ", marker.group(1)).strip().upper()
                continue
            link = re.search(r'<a\s+href="\s*(https?://[^"\s]+)\s*"[^>]*>(.*?)</a>',
                             row, re.S)
            if not link:
                continue
            url = link.group(1)
            name = htmllib.unescape(re.sub(r"<[^>]+>", "", link.group(2))).strip()
            dom = domain_of(url)
            if not dom or dom in JUNK_DOMAINS:
                continue
            if current in US_STATES:
                country, region = "US", current.title()
            elif current in COUNTRY_MARKERS:
                country, region = COUNTRY_MARKERS[current], current.title()
            else:
                country, region = country_from_tld(dom) or "US", (current or "").title()
            recs.append({"domain": dom, "company": name, "website": url,
                         "country": country, "region": region,
                         "source": "selleressentials_directory"})
    return recs


def _hopstack_page(url):
    html = fetch(url)
    name_m = re.search(
        r'name-website-wrp">\s*<div[^>]*>([^<]+)</div>\s*<a href="([^"]*)"', html)
    if not name_m:
        return None
    name = htmllib.unescape(name_m.group(1)).strip()
    site = name_m.group(2).strip()
    if not site.startswith("http"):
        site = ""
    desc_m = re.search(r"based in ([^,.<]+?),\s*(USA|United States|Canada|UK|"
                       r"United Kingdom|Germany|Mexico|China|Australia|[A-Za-z ]+)[,.<]",
                       html)
    region, country = "", None
    if desc_m:
        region = desc_m.group(1).strip()
        cname = desc_m.group(2).strip().upper()
        if cname in ("USA", "UNITED STATES"):
            country = "US"
        else:
            country = COUNTRY_MARKERS.get(cname)
        if country is None and region.upper() in US_STATES:
            country = "US"
    dom = domain_of(site) if site else ""
    if dom in JUNK_DOMAINS:
        dom, site = "", ""
    return {"domain": dom, "company": name, "website": site,
            "country": country or (country_from_tld(dom) if dom else None) or "US",
            "region": region, "source": "hopstack_directory"}


def scrape_hopstack(workers=16):
    sitemap = fetch("https://www.hopstack.io/sitemap.xml")
    urls = [l for l in re.findall(r"<loc>([^<]+)</loc>", sitemap)
            if "/fba-prep-center-directory/" in l]
    cache = json.loads(HOPSTACK_CACHE.read_text()) if HOPSTACK_CACHE.exists() else {}
    todo = [u for u in urls if u not in cache]
    print(f"  hopstack: {len(urls)} pages ({len(cache)} cached, {len(todo)} to fetch)")
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_hopstack_page, u): u for u in todo}
        for fut in cf.as_completed(futs):
            u = futs[fut]
            try:
                cache[u] = fut.result()
            except Exception as e:  # noqa
                cache[u] = {"error": str(e)[:60]}
    HOPSTACK_CACHE.write_text(json.dumps(cache, ensure_ascii=False))
    return [r for r in cache.values() if r and r.get("domain")]


def scrape_rocketsource():
    try:
        html = fetch("https://www.rocketsource.io/amazon-fba-prep-services")
    except Exception as e:
        print(f"  rocketsource: skipped ({e})")
        return []
    recs = []
    for url in set(re.findall(r'href="(https?://[^"]+)"', html)):
        dom = domain_of(url)
        if not dom or dom in JUNK_DOMAINS or "rocketsource" in dom:
            continue
        if not re.search(r"(prep|fulfil|logistic|ship|3pl|pack|warehouse)", dom):
            continue  # rocketsource page links a lot of non-directory stuff
        recs.append({"domain": dom, "company": dom.split(".")[0].title(),
                     "website": url, "country": country_from_tld(dom) or "US",
                     "region": "", "source": "rocketsource_directory"})
    return recs


def load_suppress():
    sup = set()
    f = DATA / "suppress_domains.txt"
    if f.exists():
        sup |= {l.strip().lower() for l in f.read_text().splitlines() if l.strip()}
    for layer in ("layer1", "layer2", "layer3"):
        p = DATA / f"{layer}_domains.txt"
        if p.exists():
            sup |= {l.strip().lower() for l in p.read_text().splitlines() if l.strip()}
    return sup


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-hopstack", action="store_true")
    args = ap.parse_args()

    print("scraping selleressentials…")
    recs = scrape_selleressentials()
    print(f"  selleressentials: {len(recs)} entries")

    if not args.skip_hopstack:
        print("scraping hopstack directory…")
        recs += scrape_hopstack()

    print("scraping rocketsource…")
    recs += scrape_rocketsource()

    suppress = load_suppress()
    by_dom = {}
    for r in recs:
        d = r["domain"]
        if not d or d in suppress:
            continue
        if r.get("company"):
            r["company"] = htmllib.unescape(r["company"])
        if d not in by_dom:  # first source wins (selleressentials has best names)
            by_dom[d] = r

    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for r in by_dom.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    OUT_DOMAINS.write_text("\n".join(sorted(by_dom)) + "\n")

    by_cc = {}
    for r in by_dom.values():
        by_cc[r["country"]] = by_cc.get(r["country"], 0) + 1
    print(f"\ntotal unique prep-center domains: {len(by_dom)} "
          f"(suppressed {len(recs) - sum(1 for r in recs if r['domain'] in by_dom)} dupes/known)")
    print("by country:", ", ".join(f"{k}:{v}" for k, v in
                                   sorted(by_cc.items(), key=lambda kv: -kv[1])))
    print(f"wrote {OUT_JSONL} + {OUT_DOMAINS}")
    print("next: python3 outreach/scripts/2b_email_harvest.py "
          f"--domains-file {OUT_DOMAINS}")


if __name__ == "__main__":
    main()
