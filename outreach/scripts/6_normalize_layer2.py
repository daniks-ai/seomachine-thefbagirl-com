#!/usr/bin/env python3
"""
Layer-2 normalizer: Google Maps places (compass/crawler-google-places output).

Reads every outreach/data/layer2_gmaps_raw/gmaps_*.json, keeps places that look
like real agencies with their own website, reduces each to an apex domain, and
dedupes:
  - within layer 2
  - against layer1_domains.txt (already scraped/contacted via the directory)
  - against suppress_domains.txt (live campaigns)

Writes layer2_agencies.jsonl + layer2_domains.txt in the same shape layer 1
uses, so 2b_email_harvest.py and 3_build_instantly_csv.py work unchanged.

Usage:
    python3 outreach/scripts/6_normalize_layer2.py
"""
import json
import re
import sys
from pathlib import Path

# reuse the apex() domain logic from the layer-1 normalizer
sys.path.insert(0, str(Path(__file__).resolve().parent))
normalize_layer1 = __import__("1_normalize_layer1")
apex = normalize_layer1.apex
load_suppress = normalize_layer1.load_suppress

DATA = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA / "layer2_gmaps_raw"

# never lead-worthy hosts: socials, marketplaces, directories, link shorteners
BLOCK_HOSTS = normalize_layer1.GENERIC_HOSTS | {
    "yelp.com", "clutch.co", "designrush.com", "sortlist.com", "g2.com",
    "upwork.com", "fiverr.com", "linktr.ee", "wixsite.com", "business.site",
    "sites.google.com", "medium.com", "godaddysites.com", "wordpress.com",
    "blogspot.com", "notion.site", "calendly.com", "wa.link", "whatsapp.com",
    "t.me", "maps.google.com", "amazon.in", "amazon.de", "amazon.co.uk",
    "amazon.com.br", "amazon.com.mx", "amazon.ae", "amazon.sa", "amazon.fr",
    "amazon.es", "amazon.it", "amazon.nl", "amazon.pl", "amazon.com.au",
    "amazon.sg", "amazon.co.jp", "amazon.com.tr",
}

# a place must match at least one of these in title or categoryName to count
# as an agency/service business (multi-language)
AGENCY_HINT = re.compile(
    r"(agency|agentur|agence|agencia|ag[êe]ncia|agenzia|agencja|ajans|bureau|"
    r"marketing|advertis|publicit|pubblicit|werbe|consult|dan[ıi]şman|"
    r"e-?commerce|ecommerce|digital|media|seo|ppc|amazon|fba|運用|コンサル|"
    r"internet marketing service)", re.I)

# Amazon's own infrastructure shows up for "amazon ..." searches — kill it
AMAZON_INFRA = re.compile(
    r"(amazon (hub|locker|fresh|go|warehouse|delivery|fulfillment|sort|"
    r"logistics|pickup|counter|office|corporate)|whole foods)", re.I)


def main():
    raw_files = sorted(RAW_DIR.glob("gmaps_*.json"))
    if not raw_files:
        sys.exit(f"no raw files in {RAW_DIR} — run 5_gmaps_scrape.py first")

    layer1_domains = set()
    l1 = DATA / "layer1_domains.txt"
    if l1.exists():
        layer1_domains = {d.strip() for d in l1.read_text().splitlines() if d.strip()}
    suppress = load_suppress()

    seen = set()
    out = []
    stats = {"raw": 0, "no_site": 0, "blocked_host": 0, "not_agency": 0,
             "amazon_infra": 0, "dupe_l2": 0, "dupe_l1": 0, "suppressed": 0}

    for rf in raw_files:
        places = json.loads(rf.read_text(encoding="utf-8"))
        for p in places:
            stats["raw"] += 1
            title = (p.get("title") or "").strip()
            category = (p.get("categoryName") or "").strip()
            if AMAZON_INFRA.search(title):
                stats["amazon_infra"] += 1
                continue
            site = p.get("website") or ""
            dom = apex(site)
            if not dom:
                stats["no_site"] += 1
                continue
            if dom in BLOCK_HOSTS or dom.startswith("amazon."):
                stats["blocked_host"] += 1
                continue
            if not AGENCY_HINT.search(f"{title} {category}"):
                stats["not_agency"] += 1
                continue
            if dom in seen:
                stats["dupe_l2"] += 1
                continue
            if dom in layer1_domains:
                stats["dupe_l1"] += 1
                continue
            if dom in suppress:
                stats["suppressed"] += 1
                continue
            seen.add(dom)
            country = (p.get("countryCode") or "").upper() or None
            out.append({
                "domain": dom,
                "company": title,
                "website": site,
                "description": f"{category}. {p.get('address') or ''}".strip(". "),
                "service_model": None,
                "locations": [p.get("city")] if p.get("city") else [],
                "country": country,
                "marketplaces": [],
                "gmaps_url": p.get("url"),
                "total_score": p.get("totalScore"),
                "reviews_count": p.get("reviewsCount"),
                "source": "google_maps",
            })

    out_jsonl = DATA / "layer2_agencies.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    domains_file = DATA / "layer2_domains.txt"
    domains_file.write_text("\n".join(o["domain"] for o in out) + "\n", encoding="utf-8")

    print(f"raw places:          {stats['raw']}")
    print(f"unique new agencies: {len(out)}")
    for k in ("no_site", "blocked_host", "not_agency", "amazon_infra",
              "dupe_l2", "dupe_l1", "suppressed"):
        print(f"  skipped {k:13s}{stats[k]}")
    by_country = {}
    for o in out:
        by_country[o["country"] or "??"] = by_country.get(o["country"] or "??", 0) + 1
    print("by country:", dict(sorted(by_country.items(), key=lambda kv: -kv[1])))
    print(f"wrote: {out_jsonl}")
    print(f"wrote: {domains_file}")


if __name__ == "__main__":
    main()
