#!/usr/bin/env python3
"""
Prep-center round 2: merge all r2 sources, dedupe against round 1 + agency
layers + suppress list, write the harvest-ready domain list.

Sources (outreach/data/):
  prep_r2_shiphype_domains.txt   one domain per line (ShipHype list, via browser)
  prep_r2_rocketsource.txt       domain|name|state ("XX-COUNTRY" state = country)
  prep_r2_dirs2.jsonl            fbaprepfinder + prepmarketplace detail pages
  prep_r2_ddg.jsonl              DuckDuckGo SERP sweep

Output:
  prep_r2_centers.jsonl  {domain, company, website, country, region, source}
  prep_r2_domains.txt

Usage: python3 outreach/scripts/prep4_normalize_r2.py
"""
import csv
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"

TLD_COUNTRY = {
    ".co.uk": "GB", ".uk": "GB", ".ca": "CA", ".de": "DE", ".fr": "FR",
    ".es": "ES", ".it": "IT", ".nl": "NL", ".pl": "PL", ".com.au": "AU",
    ".com.mx": "MX", ".ae": "AE", ".in": "IN", ".ie": "IE", ".cn": "CN",
    ".jp": "JP", ".pt": "PT", ".cz": "CZ", ".eu": "EU", ".ro": "RO",
    ".at": "AT", ".ch": "CH", ".se": "SE", ".dk": "DK",
}
US_STATE_CODES = {"AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID",
    "IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE",
    "NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN",
    "TX","UT","VT","VA","WA","WV","WI","WY"}

JUNK = re.compile(
    r"(fbaprepfinder|fbaprepcenters\.org|prepmarketplace|fulfill\.com|"
    r"selleressentials|shiphype|rocketsource|hopstack|prepcenter\.com$|"
    r"wixsite\.com|wordpress\.com|blogspot|godaddysites|squarespace|weebly|"
    r"ecomcircles|junglescout|helium10|sellerboard|sellerapp|freeup|"
    r"webretailer|amzscout|zonguru|smartscout|keepa|camelcamelcamel|"
    r"fulfillmentcompanies|warehousingandfulfillment|extensiv|shipstation|"
    r"shipbob\.|deliverr|flexport|freightos|uship|redstagfulfillment\.com/blog|"
    r"tinuiti|feedvisor|teikametrics|perpetua|pacvue|quartile|adbadger|"
    r"sellozo|bqool|aura|repricerexpress|informed\.co|"
    r"gembah|sourcify|leelinesourcing|supplyia|imports?stars|"
    r"udemy|coursera|skillshare|youtube|reddit|discord|slack|"
    r"crunchbase|pitchbook|owler|zoominfo|apollo\.io|"
    r"prnewswire|businesswire|globenewswire|einpresswire|"
    r"dnb\.com|manta\.com|chamberofcommerce|mapquest|foursquare)", re.I)


def domain_root_name(dom):
    root = dom.split(".")[0]
    root = re.sub(r"[-_]+", " ", root)
    return root.title()


def country_from_tld(dom, default="US"):
    for tld, cc in sorted(TLD_COUNTRY.items(), key=lambda kv: -len(kv[0])):
        if dom.endswith(tld):
            return cc
    return default


def load_exclusions():
    ex = set()
    for fname in ("prep_domains.txt", "suppress_domains.txt",
                  "layer1_domains.txt", "layer2_domains.txt", "layer3_domains.txt"):
        p = DATA / fname
        if p.exists():
            ex |= {l.strip().lower() for l in p.read_text().splitlines() if l.strip()}
    m = DATA / "instantly_prep_master.csv"
    if m.exists():
        with m.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ex.add(r["email"].split("@", 1)[1].strip().lower())
    return ex


def main():
    recs = []

    p = DATA / "prep_r2_shiphype_domains.txt"
    if p.exists():
        for line in p.read_text().splitlines():
            d = line.strip().lower()
            if d:
                recs.append({"domain": d, "company": domain_root_name(d),
                             "country": country_from_tld(d), "region": "",
                             "source": "shiphype_directory"})

    p = DATA / "prep_r2_rocketsource.txt"
    if p.exists():
        for line in p.read_text().splitlines():
            if "|" not in line:
                continue
            d, name, state = (line.split("|") + ["", ""])[:3]
            d = d.strip().lower()
            if not d:
                continue
            state = state.strip()
            if state.endswith("-COUNTRY"):
                country, region = state[:2], ""
            elif state[:2] in US_STATE_CODES:
                country, region = "US", state[:2]
            elif state in ("ON", "BC", "AB", "QC"):
                country, region = "CA", state
            else:
                country, region = country_from_tld(d), state
            recs.append({"domain": d, "company": name.strip() or domain_root_name(d),
                         "country": country, "region": region,
                         "source": "rocketsource_directory"})

    p = DATA / "prep_r2_dirs2.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            r = json.loads(line)
            d = r["domain"].strip().lower()
            recs.append({"domain": d, "company": r.get("company") or domain_root_name(d),
                         "country": country_from_tld(d), "region": r.get("region", ""),
                         "source": r["source"]})

    for fname, src in (("prep_r2_sermondo.jsonl", "sermondo_logistics"),
                       ("prep_r2_gmaps.jsonl", "google_maps_dfs"),
                       ("prep_r2_dfs_serp.jsonl", "dfs_organic")):
        p = DATA / fname
        if p.exists():
            for line in p.read_text().splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                d = (r.get("domain") or "").strip().lower()
                if not d:
                    continue
                name = r.get("company") or domain_root_name(d)
                kind = r.get("kind")
                if not kind:
                    blob = f"{name} {d}".lower()
                    kind = "prep" if re.search(r"(\bprep\b|\bfba\b|amazon)", blob) else "3pl"
                recs.append({"domain": d, "company": name,
                             "country": r.get("country") or country_from_tld(d),
                             "region": r.get("region", ""), "kind": kind,
                             "source": r.get("source") or src})

    p = DATA / "prep_r2_ddg.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            r = json.loads(line)
            d = r["domain"].strip().lower()
            cc = r.get("country") or country_from_tld(d)
            # trust TLD over query geo when they disagree on obvious ccTLDs
            tld_cc = country_from_tld(d, default=cc)
            recs.append({"domain": d, "company": domain_root_name(d),
                         "country": tld_cc, "region": r.get("region", ""),
                         "source": "ddg_serp"})

    exclusions = load_exclusions()
    by_dom = {}
    dropped_junk = dropped_known = 0
    for r in recs:
        d = r["domain"]
        if not d or "." not in d:
            continue
        if JUNK.search(d):
            dropped_junk += 1
            continue
        if d in exclusions:
            dropped_known += 1
            continue
        if d not in by_dom:  # earlier sources (curated directories) win
            r["website"] = f"https://{d}"
            # curated FBA directories are prep by definition
            r.setdefault("kind", "prep")
            by_dom[d] = r

    out_jsonl = DATA / "prep_r2_centers.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in by_dom.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (DATA / "prep_r2_domains.txt").write_text("\n".join(sorted(by_dom)) + "\n")

    by_cc = {}
    for r in by_dom.values():
        by_cc[r["country"]] = by_cc.get(r["country"], 0) + 1
    by_src = {}
    for r in by_dom.values():
        by_src[r["source"]] = by_src.get(r["source"], 0) + 1
    print(f"unique NEW domains: {len(by_dom)} "
          f"(junk dropped {dropped_junk}, already-known dropped {dropped_known})")
    print("by country:", ", ".join(f"{k}:{v}" for k, v in sorted(by_cc.items(), key=lambda kv: -kv[1])))
    print("by source: ", ", ".join(f"{k}:{v}" for k, v in sorted(by_src.items(), key=lambda kv: -kv[1])))
    print(f"wrote {out_jsonl} + prep_r2_domains.txt")


if __name__ == "__main__":
    main()
