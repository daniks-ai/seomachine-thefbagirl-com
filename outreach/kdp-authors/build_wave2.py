#!/usr/bin/env python3
"""
Wave-2 target list from the link graph the wave-1 crawl already collected.

Indie authors cross-promote relentlessly — blogrolls, "author friends" pages,
newsletter-swap partners, blog-tour hosts, anthology co-authors. So the outbound
links of a confirmed author site are mostly *other author sites*, and following
them costs nothing (no SERP spend) while reaching authors who rank for nothing.

A candidate is kept when it was linked from at least one page and is not already
crawled, suppressed, or an obvious platform. Candidates linked from confirmed
author sites (author_score > 0) are ranked first.

Usage:
    python3 outreach/kdp-authors/build_wave2.py --out data/wave2.txt --min-refs 1
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

BAD = re.compile(
    r"(^|\.)(gravatar|w3|schema|creativecommons|jquery|bootstrap|fontawesome|"
    r"googleapis|gstatic|cloudfront|akamai|jsdelivr|unpkg|typekit|"
    r"paypal|stripe|amazonaws|azurewebsites|herokuapp|firebaseapp|"
    r"doubleclick|googletagmanager|analytics|hotjar|sentry|cookiebot|"
    r"mailerlite|mailjet|sendinblue|hubspot|salesforce|zendesk|intercom|"
    r"bit|tinyurl|goo|t|ow|buff|linktree|smarturl|geni|books2read|"
    r"amazon|amzn|audible|goodreads|bookbub|kobo|apple|barnesandnoble)\.", re.I)
BAD_TLD = re.compile(r"\.(gov|edu|mil|ac\.uk|gov\.uk|edu\.au|gov\.au|gc\.ca)$", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DATA / "wave2.txt"))
    ap.add_argument("--min-refs", type=int, default=1)
    ap.add_argument("--max", type=int, default=25000)
    args = ap.parse_args()

    crawled, records = set(), []
    for f in list(DATA.glob("_progress_*.json")) + list(DATA.glob("contacts_*.json")):
        try:
            blob = json.loads(f.read_text())
        except Exception:
            continue
        vals = blob.values() if isinstance(blob, dict) else blob
        for v in vals:
            crawled.add(v.get("domain", ""))
            records.append(v)
    sup = {l.strip() for l in (DATA / "suppression_domains.txt").read_text().splitlines()
           if l.strip()} if (DATA / "suppression_domains.txt").exists() else set()

    refs, author_refs = defaultdict(int), defaultdict(int)
    for r in records:
        weight = 1 if r.get("author_score", 0) > 0 else 0
        for item in r.get("ext") or []:
            d, n = item if isinstance(item, (list, tuple)) else (item, 1)
            refs[d] += n
            author_refs[d] += weight

    cands = []
    for d, n in refs.items():
        if not d or d in crawled or d in sup or BAD.search("." + d) or BAD_TLD.search(d):
            continue
        if n < args.min_refs:
            continue
        cands.append((author_refs[d], n, d))
    cands.sort(reverse=True)
    picked = [d for _, _, d in cands][: args.max]
    Path(args.out).write_text("\n".join(picked))
    print(f"{len(refs)} outbound domains seen | {len(picked)} new candidates -> {args.out}")
    print("top:", ", ".join(picked[:12]))


if __name__ == "__main__":
    main()
