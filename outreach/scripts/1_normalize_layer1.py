#!/usr/bin/env python3
"""
Layer 1 normalizer: Amazon Ads Partner Directory (Apify lexis-solutions actor).

Reads the raw actor dataset, extracts a clean apex domain per partner, dedupes
(by domain, and against already-contacted leads), keeps only entries that look
like real agencies with a website, and writes a tidy JSONL + a bare domain list
that feeds the contact-scraper and Apollo enrichment steps.

Usage:
    python3 outreach/scripts/1_normalize_layer1.py \
        outreach/data/layer1_amazon_partners_raw.json
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# Domains already contacted in the live Instantly campaign (the 29 pilot leads).
# One domain per line; safe to be empty. Populated as campaigns grow.
SUPPRESS_FILE = DATA / "suppress_domains.txt"

GENERIC_HOSTS = {
    "facebook.com", "linkedin.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "amazon.com", "google.com", "bit.ly", "goo.gl", "wa.me",
}


def apex(url: str) -> str:
    """Reduce a URL to a lowercase registrable-ish host (strip www + path)."""
    if not url:
        return ""
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return ""
    host = host.lower().lstrip(".")
    if host.startswith("www."):
        host = host[4:]
    # crude multi-part TLD guard (co.uk, com.br, com.au, co.jp ...)
    parts = host.split(".")
    if len(parts) > 2 and parts[-2] in {"co", "com", "org", "net", "gov", "ac"} and len(parts[-1]) == 2:
        host = ".".join(parts[-3:])
    elif len(parts) > 2:
        host = ".".join(parts[-2:])
    return host


def load_suppress() -> set:
    s = set()
    if SUPPRESS_FILE.exists():
        for line in SUPPRESS_FILE.read_text(encoding="utf-8").splitlines():
            d = apex(line.strip())
            if d:
                s.add(d)
    return s


def main():
    if len(sys.argv) < 2:
        raw_path = DATA / "layer1_amazon_partners_raw.json"
    else:
        raw_path = Path(sys.argv[1])
    rows = json.loads(raw_path.read_text(encoding="utf-8"))
    suppress = load_suppress()

    seen = set()
    out = []
    skipped_no_site = 0
    skipped_dupe = 0
    skipped_suppressed = 0

    for r in rows:
        site = r.get("companyWebsite") or r.get("externalHomeUrl") or r.get("contactUrl") or ""
        dom = apex(site)
        if not dom or dom in GENERIC_HOSTS:
            skipped_no_site += 1
            continue
        if dom in suppress:
            skipped_suppressed += 1
            continue
        if dom in seen:
            skipped_dupe += 1
            continue
        seen.add(dom)
        locations = r.get("locations") or []
        out.append({
            "domain": dom,
            "company": (r.get("companyName") or r.get("name") or "").strip(),
            "website": site,
            "description": (r.get("description") or "").strip()[:600],
            "service_model": r.get("serviceModel"),
            "locations": locations,
            "country": locations[0] if locations else None,
            "marketplaces": r.get("marketplaces") or [],
            "amazon_directory_url": r.get("url"),
            "source": "amazon_ads_partner_directory",
        })

    out_jsonl = DATA / "layer1_agencies.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")

    domains_file = DATA / "layer1_domains.txt"
    domains_file.write_text("\n".join(o["domain"] for o in out) + "\n", encoding="utf-8")

    print(f"raw rows:            {len(rows)}")
    print(f"unique agencies:     {len(out)}")
    print(f"  skipped no-site:   {skipped_no_site}")
    print(f"  skipped dupe:      {skipped_dupe}")
    print(f"  skipped suppressed:{skipped_suppressed}")
    print(f"wrote: {out_jsonl}")
    print(f"wrote: {domains_file}")


if __name__ == "__main__":
    main()
