#!/usr/bin/env python3
"""
Confirm that a collected domain really is a marketing/digital agency.

Directory scrapes attach a website field to a listing, and that field is
sometimes wrong — a Yellow Pages row for an agency can point at a charity or a
magazine. Google Maps has the same failure mode with shared-office addresses.
Mailing those a white-label Amazon-PPC pitch is worse than not mailing at all,
so every directory/Maps-sourced domain gets its homepage read before import.

Verdicts:
  agency   — homepage carries agency vocabulary (safe to mail)
  unclear  — reachable but no agency signal (parked page, holding page, JS-only)
  unreachable — did not load

Writes data/au_agency_verdicts.json and prints the non-agency ones for review.

Usage:
    python3 outreach/scripts/au5_verify_agency.py --domains-file <file> [--workers 20]
"""
import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module

h = import_module("2b_email_harvest")          # reuse its fetch + UA handling

DATA = Path(__file__).resolve().parents[1] / "data"
OUT = DATA / "au_agency_verdicts.json"

# Vocabulary that a marketing/digital/creative agency site almost always uses.
AGENCY_TERMS = re.compile(
    r"\b(marketing|advertis\w+|digital agency|seo|search engine optimi[sz]ation|"
    r"ppc|google ads|adwords|social media|branding|brand strategy|web design|"
    r"web development|ecommerce|e-commerce|creative agency|media agency|"
    r"lead generation|conversion|campaign|copywriting|content strategy)\b", re.I)

# Signals the domain is something else entirely — used to explain a rejection.
# Deliberately narrow: single generic words backfire ("menu" matched every
# site's nav bar, "charity" matched agencies listing pro-bono clients). Each
# phrase here has to be one a marketing agency would not put on its homepage.
OTHER_BUSINESS = re.compile(
    r"(donate now|make a donation|tax-deductible gift|not-for-profit organisation|"
    r"church service times|school enrolment|enrol your child|"
    r"subscribe to the magazine|book a table|reserve a table|order online for pickup|"
    r"properties for sale|open for inspection|book an appointment with our dentist|"
    r"medical centre|bulk billing|our solicitors|legal advice today)", re.I)


def verify(domain):
    html = None
    for scheme in ("https://", "http://"):
        try:
            html, _ = h.fetch(scheme + domain)
            break
        except Exception:                              # noqa: BLE001
            continue
    if html is None:
        return {"domain": domain, "verdict": "unreachable"}

    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html,
                  flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    hits = sorted({m.group(0).lower() for m in AGENCY_TERMS.finditer(text)})
    other = sorted({m.group(0).lower() for m in OTHER_BUSINESS.finditer(text)})
    if len(hits) >= 2:
        return {"domain": domain, "verdict": "agency", "signals": hits[:5]}
    return {"domain": domain, "verdict": "unclear",
            "signals": hits, "other_business": other[:3]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains-file", required=True)
    ap.add_argument("--workers", type=int, default=20)
    args = ap.parse_args()

    domains = [d.strip() for d in Path(args.domains_file).read_text().splitlines()
               if d.strip()]
    store = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [d for d in domains if d not in store]
    print(f"{len(store)} cached, verifying {len(todo)} domains")

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for r in ex.map(verify, todo):
            store[r["domain"]] = r
    OUT.write_text(json.dumps(store, indent=1), encoding="utf-8")

    subset = {d: store[d] for d in domains if d in store}
    counts = {}
    for r in subset.values():
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print("verdicts:", counts)
    flagged = [r for r in subset.values()
               if r["verdict"] == "unclear" and r.get("other_business")]
    if flagged:
        print("\nlooks like a DIFFERENT kind of business — do not mail:")
        for r in flagged:
            print(f"  {r['domain']}: {', '.join(r['other_business'])}")


if __name__ == "__main__":
    main()
