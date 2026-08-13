#!/usr/bin/env python3
"""
Argentina lead engine, step 3: merge Maps + SERP, dedupe, tier, emit domain list.

Merge rules
-----------
* one row per registrable domain; the **strongest tier wins** (A > B > C);
* Maps titles beat SERP titles for `company` — a Maps title is the registered
  business name, a SERP title is a page headline ("Las 10 mejores agencias…"),
  which would render as garbage in {{companyName}};
* SERP-only rows whose title looks like a listicle/blog headline get their
  company blanked so the sequence falls back to a neutral phrase;
* anything already sitting in another live campaign is dropped here, not later —
  the shared mailboxes must never send a second cold sequence to the same domain.

Output:
  data/ar_leads.jsonl   merged, tiered records
  data/ar_domains.txt   feed for 2b_email_harvest.py

Usage:
    python3 outreach/ar-sellers/ar3_normalize.py
"""
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SHARED = HERE.parents[0] / "data"

GMAPS = DATA / "ar_gmaps.jsonl"
SERP = DATA / "ar_serp.jsonl"
CACE = DATA / "ar_cace.jsonl"      # round 2, chamber directory (ar7_cace.py)
OUT = DATA / "ar_leads.jsonl"
DOMAINS = DATA / "ar_domains.txt"

# Every CSV we have ever imported into Instantly + the explicit suppress list.
MASTER_GLOBS = ["instantly_*.csv", "instantly_segments*/*.csv",
                "instantly_segments_*/*.csv"]
SUPPRESS = SHARED / "suppress_domains.txt"

JUNK = re.compile(
    r"(^|\.)(amazon|google|facebook|instagram|linkedin|twitter|x|youtube|"
    r"tiktok|pinterest|reddit|quora|medium|wikipedia|w3|schema)\.|"
    r"mercadolibre|tiendanube|shopify|vtex|woocommerce|wix|squarespace|"
    r"jumpseller|bigcommerce|prestashop|magento|mercadoshops|"
    r"clutch\.co|sortlist|designrush|goodfirms|semrush|ahrefs|similarweb|"
    r"agencyspotter|expertise\.com|superbcompanies|topdigital|"
    r"infobae|clarin|lanacion|cronista|ambito|perfil\.com|pagina12|iproup|"
    r"iprofesional|forbesargentina|infotechnology|telam|lmneuquen|"
    r"americaretail|ecommercenews|dossiernet|totalmedios|adlatina|"
    r"gob\.ar|gov\.ar|edu\.ar|mil\.ar|int\.ar|afip|anmat|inti\b|"
    r"computrabajo|indeed|zonajobs|bumeran|glassdoor|linkedin|"
    r"paginasamarillas|cylex|opendi|infoisinfo|guiaempresas|guialocal|"
    r"udemy|coursera|hotmart|domestika|crehana|platzi|edx\.|"
    r"wordpress\.com|blogspot|substack|wixsite|godaddysites|business\.site|"
    r"sites\.google|linktr\.ee|bit\.ly|"
    r"payoneer|paypal|stripe|mercadopago|dhl|fedex|ups\.com|correoargentino|"
    r"helium10|junglescout|sellerapp|perpetua|teikametrics|jungle\.|"
    r"instantly\.ai|apollo\.io|hunter\.io|fiverr|upwork|workana|freelancer",
    re.I)

# SERP titles that are content, not a company identity.
LISTICLE = re.compile(
    r"(^\s*\d+|\btop\b|mejores|guía|guia|cómo |como |qué es|que es|"
    r"paso a paso|ranking|listado|\d{4}\)?$|\| *blog|tutorial|curso)", re.I)

TIER_RANK = {"A": 0, "B": 1, "C": 2}


def load_jsonl(p):
    if not p.exists():
        print(f"  (missing {p.name} — skipped)")
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def registrable(d):
    """Strip www. and lowercase. Keeps full host otherwise (subdomains are rare
    here and collapsing them merges distinct agencies)."""
    d = (d or "").lower().strip().rstrip(".")
    return d[4:] if d.startswith("www.") else d


def known_domains():
    """Domains already contacted anywhere — never re-mail from shared mailboxes."""
    seen = set()
    if SUPPRESS.exists():
        seen |= {registrable(x) for x in SUPPRESS.read_text().split() if x}
    files = []
    for g in MASTER_GLOBS:
        files += list(SHARED.glob(g))
    for f in files:
        try:
            with f.open(newline="", encoding="utf-8", errors="ignore") as fh:
                for row in csv.DictReader(fh):
                    for k in ("email", "Email", "website", "Website", "domain"):
                        v = (row.get(k) or "").strip()
                        if not v:
                            continue
                        if "@" in v:
                            seen.add(registrable(v.split("@")[-1]))
                        else:
                            m = re.search(r"([a-z0-9.\-]+\.[a-z]{2,})", v.lower())
                            if m:
                                seen.add(registrable(m.group(1)))
        except Exception as ex:
            print(f"  warn: {f.name}: {str(ex)[:60]}")
    seen.discard("")
    return seen


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    gm, sp, cc = load_jsonl(GMAPS), load_jsonl(SERP), load_jsonl(CACE)
    print(f"maps rows {len(gm)} | serp rows {len(sp)} | cace rows {len(cc)}")

    merged = {}

    def add(rec, from_maps):
        d = registrable(rec.get("domain"))
        if not d or "." not in d or JUNK.search(d):
            return
        name = (rec.get("company") or "").strip()
        if not from_maps and (LISTICLE.search(name) or len(name) > 60):
            name = ""          # listicle headline -> let the sequence fall back
        cur = merged.get(d)
        if cur is None:
            merged[d] = {"domain": d, "company": name, "tier": rec["tier"],
                         "city": rec.get("city", ""),
                         "category": rec.get("category", ""),
                         "sources": [rec.get("source", "")],
                         "from_maps": from_maps}
            return
        if TIER_RANK[rec["tier"]] < TIER_RANK[cur["tier"]]:
            cur["tier"] = rec["tier"]
        if from_maps and not cur["from_maps"]:
            cur["company"] = name or cur["company"]   # prefer the registry name
            cur["city"] = rec.get("city", "") or cur["city"]
            cur["from_maps"] = True
        elif not cur["company"]:
            cur["company"] = name
        if rec.get("source") not in cur["sources"]:
            cur["sources"].append(rec.get("source", ""))

    for r in gm:
        add(r, True)
    for r in cc:
        add(r, True)      # chamber listings carry the registered company name
    for r in sp:
        add(r, False)

    known = known_domains()
    print(f"suppression set: {len(known)} domains already contacted")
    fresh = {d: r for d, r in merged.items() if d not in known}
    dropped = len(merged) - len(fresh)

    with OUT.open("w", encoding="utf-8") as f:
        for r in fresh.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    DOMAINS.write_text("\n".join(sorted(fresh)) + "\n", encoding="utf-8")

    tiers = {t: sum(1 for r in fresh.values() if r["tier"] == t) for t in "ABC"}
    ar_tld = sum(1 for d in fresh if d.endswith(".ar"))
    print(f"\n{len(merged)} merged - {dropped} already-contacted = {len(fresh)} fresh")
    print(f"tiers {tiers} | .ar TLD {ar_tld} ({ar_tld*100//max(1,len(fresh))}%)")
    print(f"-> {OUT}\n-> {DOMAINS}")
    print("next: python3 outreach/scripts/2b_email_harvest.py "
          f"--domains-file {DOMAINS}")


if __name__ == "__main__":
    sys.exit(main())
