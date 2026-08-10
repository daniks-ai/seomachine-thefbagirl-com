#!/usr/bin/env python3
"""
Layer-3 normalizer: Google SERP organic results (apify/google-search-scraper).

Reads every outreach/data/layer3_serp_raw/serp_*.json, walks the organicResults
of each SERP page, reduces each result to an apex domain, and keeps the ones
that look like a real agency's own site — dropping directories, listicles,
media, marketplaces, socials, and SaaS tools that dominate these SERPs.

Dedupes:
  - within layer 3
  - against layer1_domains.txt (Amazon partner directory)
  - against layer2_domains.txt (Google Maps), if present
  - against suppress_domains.txt (live campaigns)

Writes layer3_agencies.jsonl + layer3_domains.txt in the same shape layers 1-2
use, so 2b_email_harvest.py and 3_build_instantly_csv.py work unchanged.

Usage:
    python3 outreach/scripts/8_normalize_layer3.py
"""
import json
import re
import sys
from pathlib import Path

# reuse apex() + suppress loader from layer 1, and the agency-hint regex +
# base block-host set from layer 2
sys.path.insert(0, str(Path(__file__).resolve().parent))
normalize_layer1 = __import__("1_normalize_layer1")
normalize_layer2 = __import__("6_normalize_layer2")
apex = normalize_layer1.apex
load_suppress = normalize_layer1.load_suppress
AGENCY_HINT = normalize_layer2.AGENCY_HINT

DATA = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA / "layer3_serp_raw"

# SERP-specific noise on top of layer 2's block set: review directories, B2B
# marketplaces, media/blogs that publish "best agency" roundups, freelancer
# platforms, and Amazon-seller SaaS tools (competitors/tools, not agencies).
SERP_BLOCK = normalize_layer2.BLOCK_HOSTS | {
    # directories / review platforms / marketplaces
    "trustpilot.com", "glassdoor.com", "crunchbase.com", "goodfirms.co",
    "manifest.co", "themanifest.com", "expertise.com", "agencyspotter.com",
    "semrush.com", "similarweb.com", "producthunt.com", "capterra.com",
    "getapp.com", "softwareadvice.com", "trustradius.com", "sortlist.co.uk",
    "designrush.com", "topdevelopers.co", "digitalagencynetwork.com",
    "credo.com", "webflow.com", "wix.com", "squarespace.com", "shopify.com",
    "bark.com", "peopleperhour.com", "toptal.com", "freelancer.com",
    "guru.com", "99designs.com",
    # media / publishers that rank for "best amazon agency" listicles
    "forbes.com", "entrepreneur.com", "inc.com", "businessinsider.com",
    "techradar.com", "pcmag.com", "g2crowd.com", "hubspot.com", "reddit.com",
    "quora.com", "medium.com", "wikipedia.org", "youtube.com", "vimeo.com",
    "influencermarketinghub.com", "cloudwards.net", "ecommercebytes.com",
    "practicalecommerce.com", "searchengineland.com", "searchenginejournal.com",
    # Amazon-seller SaaS tools (not agencies to pitch white-label PPC to)
    "helium10.com", "junglescout.com", "sellerapp.com", "perpetua.io",
    "pacvue.com", "teikametrics.com", "quartile.com", "adbadger.com",
    "sellerlabs.com", "downstreamimpact.com", "intentwise.com", "m19.com",
    "scaleinsights.com", "sellerboard.com", "datahawk.co", "prestozon.com",
    "zonguru.com", "viral-launch.com", "sellics.com", "amazon.com",
    "aboutamazon.com", "sell.amazon.com", "advertising.amazon.com",
}

# Amazon's own infra (reuse layer 2's pattern)
AMAZON_INFRA = normalize_layer2.AMAZON_INFRA

# roundup / listicle titles — these are never a single agency's own homepage
LISTICLE = re.compile(
    r"(\b(top|best)\s+\d+\b|\b\d+\s+best\b|\bbest\s+amazon\b.*\bagenc|"
    r"\blist of\b|\bagencies\b|\bcompanies\b|\branked\b|\bcomparison\b|"
    r"\bvs\.?\b|\breview[s]?\b)", re.I)


def iter_results(raw):
    """Yield (organic_result, country) from a saved SERP wrapper file."""
    country = raw.get("country")
    for page in raw.get("items", []):
        for r in (page.get("organicResults") or []):
            yield r, country


def main():
    raw_files = sorted(RAW_DIR.glob("serp_*.json"))
    if not raw_files:
        sys.exit(f"no raw files in {RAW_DIR} — run 7_serp_scrape.py first")

    prior_domains = set()
    for name in ("layer1_domains.txt", "layer2_domains.txt"):
        p = DATA / name
        if p.exists():
            prior_domains |= {d.strip() for d in p.read_text().splitlines() if d.strip()}
    suppress = load_suppress()

    # domain -> aggregated record (first-seen wins; accumulate serp_hits + country votes)
    records = {}
    stats = {"raw": 0, "no_domain": 0, "blocked_host": 0, "amazon_infra": 0,
             "listicle": 0, "not_agency": 0, "dupe_prior": 0, "suppressed": 0}

    for rf in raw_files:
        raw = json.loads(rf.read_text(encoding="utf-8"))
        for r, country in iter_results(raw):
            stats["raw"] += 1
            title = (r.get("title") or "").strip()
            desc = (r.get("description") or "").strip()
            url = r.get("url") or r.get("link") or ""
            dom = apex(url)
            if not dom:
                stats["no_domain"] += 1
                continue
            if dom in SERP_BLOCK or dom.startswith("amazon."):
                stats["blocked_host"] += 1
                continue
            if AMAZON_INFRA.search(title):
                stats["amazon_infra"] += 1
                continue
            # a domain we've already accepted: just count another SERP hit
            if dom in records:
                rec = records[dom]
                rec["serp_hits"] += 1
                if country:
                    rec["_country_votes"][country] = rec["_country_votes"].get(country, 0) + 1
                continue
            if dom in prior_domains:
                stats["dupe_prior"] += 1
                continue
            if dom in suppress:
                stats["suppressed"] += 1
                continue
            if LISTICLE.search(title):
                stats["listicle"] += 1
                continue
            if not AGENCY_HINT.search(f"{title} {desc}"):
                stats["not_agency"] += 1
                continue
            records[dom] = {
                "domain": dom,
                "company": title[:120],
                "website": f"https://{dom}",
                "description": desc[:600],
                "service_model": None,
                "locations": [],
                "country": country,
                "marketplaces": [],
                "serp_url": url,
                "serp_hits": 1,
                "_country_votes": {country: 1} if country else {},
                "source": "google_serp",
            }

    # resolve country to the most-frequent geo that surfaced the domain
    out = []
    for dom, rec in records.items():
        votes = rec.pop("_country_votes")
        if votes:
            rec["country"] = max(votes, key=votes.get)
        out.append(rec)
    out.sort(key=lambda r: -r["serp_hits"])

    out_jsonl = DATA / "layer3_agencies.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    domains_file = DATA / "layer3_domains.txt"
    domains_file.write_text("\n".join(o["domain"] for o in out) + "\n", encoding="utf-8")

    print(f"raw organic results: {stats['raw']}")
    print(f"unique new agencies: {len(out)}")
    for k in ("no_domain", "blocked_host", "amazon_infra", "listicle",
              "not_agency", "dupe_prior", "suppressed"):
        print(f"  skipped {k:13s}{stats[k]}")
    by_country = {}
    for o in out:
        by_country[o["country"] or "??"] = by_country.get(o["country"] or "??", 0) + 1
    print("by country:", dict(sorted(by_country.items(), key=lambda kv: -kv[1])))
    multi = sum(1 for o in out if o["serp_hits"] > 1)
    print(f"surfaced by >1 query (higher-confidence): {multi}")
    print(f"wrote: {out_jsonl}")
    print(f"wrote: {domains_file}")


if __name__ == "__main__":
    main()
