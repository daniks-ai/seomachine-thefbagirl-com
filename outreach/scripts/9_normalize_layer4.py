#!/usr/bin/env python3
"""
Layer 4: normalize Clutch.co scrape (memo23 actor output) into the standard
agencies.jsonl + domains.txt shape, deduped against layers 1-3 + suppress list.

Input:  outreach/data/layer4_clutch_all.jsonl   (one Clutch company per line)
Output: outreach/data/layer4_agencies.jsonl
        outreach/data/layer4_domains.txt
"""
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"

BLOCK_HOSTS = {
    "clutch.co", "facebook.com", "linkedin.com", "instagram.com", "twitter.com",
    "youtube.com", "google.com", "wix.com", "squarespace.com", "godaddy.com",
    "wordpress.com", "shopify.com", "amazon.com", "sellercentral.amazon.com",
}


def apex(url):
    if not url:
        return ""
    u = re.sub(r"^https?://", "", url.strip()).split("/")[0].split("?")[0]
    u = u.lower().lstrip(".")
    if u.startswith("www."):
        u = u[4:]
    return u


def load_prior_domains():
    seen = set()
    for fn in ["layer1_domains.txt", "layer2_domains.txt", "layer3_domains.txt",
               "suppress_domains.txt"]:
        p = DATA / fn
        if p.exists():
            seen.update(d.strip().lower().lstrip("www.") for d in p.read_text().splitlines() if d.strip())
    # also dedupe against already-built master emails' domains
    for m in ["instantly_layer1_master.csv", "instantly_layer2_master.csv",
              "instantly_layer3_master.csv"]:
        pass
    return seen


def main():
    src = DATA / "layer4_clutch_all.jsonl"
    items = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
    prior = load_prior_domains()

    agencies = {}
    stats = {"total": len(items), "no_site": 0, "blocked": 0, "dupe_prior": 0, "dupe_l4": 0}
    for it in items:
        dom = apex(it.get("websiteUrl", ""))
        if not dom or "." not in dom:
            stats["no_site"] += 1
            continue
        if dom in BLOCK_HOSTS or any(dom.endswith("." + b) or dom == b for b in BLOCK_HOSTS):
            stats["blocked"] += 1
            continue
        if dom in prior:
            stats["dupe_prior"] += 1
            continue
        if dom in agencies:
            stats["dupe_l4"] += 1
            continue
        li = ""
        for s in it.get("socialMediaLinks", []) or []:
            if s.get("type") == "linkedin":
                li = s.get("url", "")
        agencies[dom] = {
            "domain": dom,
            "company": it.get("name") or dom,
            "website": it.get("websiteUrl"),
            "country": it.get("country") or "US",
            "city": it.get("city") or "",
            "linkedin": li,
            "source": "clutch",
        }

    out = DATA / "layer4_agencies.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for a in agencies.values():
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    (DATA / "layer4_domains.txt").write_text("\n".join(agencies.keys()), encoding="utf-8")

    print("stats:", stats)
    print(f"new layer-4 agencies (deduped vs L1-3): {len(agencies)}")
    from collections import Counter
    print("by country:", dict(Counter(a["country"] for a in agencies.values()).most_common(8)))
    print(f"wrote {out} + layer4_domains.txt")


if __name__ == "__main__":
    main()
