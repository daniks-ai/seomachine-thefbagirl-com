#!/usr/bin/env python3
"""
GoodFirms agency harvester (free, via r.jina.ai reader — GoodFirms is
Cloudflare-blocked to direct curl).

Two stages, both resumable via JSON caches:
  1) listing pages  -> company profile slugs
  2) profile pages  -> external website URL ("Visit website](<url>")

Output: outreach/data/gf_agencies.jsonl  ({domain, company, website, country, source})

Usage:
    python3 outreach/scripts/gf_harvest.py --stage listings --max-pages 60
    python3 outreach/scripts/gf_harvest.py --stage profiles --workers 4
    python3 outreach/scripts/gf_harvest.py --stage build
"""
import argparse
import concurrent.futures as cf
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
SLUGS = DATA / "_gf_slugs.json"              # slug -> {company?}
PROFILES = DATA / "_gf_profiles.json"        # slug -> {website|error}
OUT = DATA / "gf_agencies.jsonl"

JINA = "https://r.jina.ai/"
# US listing directories worth crawling (deep pagination ~40/page)
BASE_LISTS = [
    "https://www.goodfirms.co/directory/country/top-digital-marketing-companies/us",
]
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
SLUG_RE = re.compile(r"goodfirms\.co/company/([a-z0-9][a-z0-9\-]+)")
SITE_RE = re.compile(r"[Vv]isit website\]\((https?://[^)\s]+)")
BAD_HOST = re.compile(r"(goodfirms|jina\.ai|linkedin|facebook|twitter|x\.com|instagram|"
                      r"youtube|google\.|schema\.org|clutch\.co|gstatic|cloudflare|"
                      r"gravatar|wp\.com|w\.org|apple\.|microsoft|bing\.|vimeo|"
                      r"youtu\.be|wixstatic|bootstrapcdn|jsdelivr|unpkg)", re.I)
# bare-text domains in the profile body (the site is often only mentioned in prose,
# never as a "Visit website" link because that button is JS-rendered)
BARE_RE = re.compile(r"\b([a-z0-9][a-z0-9\-]{1,40}\.(?:com|io|co|net|agency|digital|"
                     r"marketing|media|ai|dev|design|studio|group|nyc|us|app|tech))\b", re.I)


def fetch(url, timeout=60):
    # r.jina.ai 403s on browser UAs / extra headers; a plain curl-like request works
    req = urllib.request.Request(JINA + url, headers={"User-Agent": "curl/8.4.0",
                                                      "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def apex(url):
    u = re.sub(r"^https?://", "", url.strip()).split("/")[0].split("?")[0].lower().lstrip(".")
    return u[4:] if u.startswith("www.") else u


def stage_listings(max_pages):
    cache = json.loads(SLUGS.read_text()) if SLUGS.exists() else {}
    for base in BASE_LISTS:
        empty_streak = 0
        for p in range(1, max_pages + 1):
            url = base if p == 1 else f"{base}?page={p}"
            try:
                md = fetch(url)
            except Exception as e:
                print(f"  p{p} ERR {str(e)[:50]}", flush=True)
                time.sleep(3)
                continue
            found = set(SLUG_RE.findall(md))
            new = [s for s in found if s not in cache]
            for s in found:
                cache.setdefault(s, {})
            print(f"  {base.split('/')[-1]} p{p}: {len(found)} slugs (+{len(new)} new), total {len(cache)}", flush=True)
            SLUGS.write_text(json.dumps(cache, ensure_ascii=False))
            empty_streak = empty_streak + 1 if not found else 0
            if empty_streak >= 3:
                print("  3 empty pages, stopping this base", flush=True)
                break
            time.sleep(1.5)
    print(f"listings done: {len(cache)} slugs", flush=True)


def _profile(slug):
    md = None
    for attempt in range(4):
        try:
            md = fetch(f"https://www.goodfirms.co/company/{slug}")
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(4 * (attempt + 1))  # backoff on rate limit
                continue
            return slug, {"error": f"http{e.code}"}
        except Exception as e:
            return slug, {"error": str(e)[:50]}
    if md is None:
        return slug, {"error": "http429"}
    # 1) authoritative: the "Visit website" markdown link (when Jina caught it)
    m = SITE_RE.search(md)
    if m and not BAD_HOST.search(m.group(1)):
        return slug, {"website": m.group(1), "via": "link"}
    # 2) any other external markdown link that isn't a bad host
    for u in re.findall(r"\((https?://[a-z0-9.\-]+\.[a-z]{2,}[^)\s]*)\)", md):
        if not BAD_HOST.search(u):
            return slug, {"website": u, "via": "extlink"}
    # 3) bare-text domain that MATCHES the slug root (safe cross-validation:
    #    we only accept a bare domain the profile mentions AND whose registrable
    #    root corresponds to this company's slug — never a blind guess)
    slug_key = re.sub(r"[^a-z0-9]", "", slug.lower())
    bare = [d.lower() for d in BARE_RE.findall(md) if not BAD_HOST.search(d.lower())]
    for d in bare:
        root = re.sub(r"[^a-z0-9]", "", d.rsplit(".", 1)[0])
        if root and (root in slug_key or slug_key in root or
                     _tok_overlap(root, slug_key)):
            return slug, {"website": "https://" + d, "via": "bare-match"}
    return slug, {"error": "no_site"}


def _tok_overlap(a, b):
    # accept when the shorter is a strong prefix/substring signal of the other
    if len(a) < 4 or len(b) < 4:
        return False
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    return short[:6] == long[:6] and len(short) >= 5


def stage_profiles(workers):
    slugs = list((json.loads(SLUGS.read_text()) if SLUGS.exists() else {}).keys())
    cache = json.loads(PROFILES.read_text()) if PROFILES.exists() else {}
    todo = [s for s in slugs if s not in cache]
    print(f"{len(cache)} cached, fetching {len(todo)} profiles with {workers} workers", flush=True)
    done = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_profile, s): s for s in todo}
        for fut in cf.as_completed(futs):
            s, rec = fut.result()
            cache[s] = rec
            done += 1
            if done % 20 == 0:
                PROFILES.write_text(json.dumps(cache, ensure_ascii=False))
                hits = sum(1 for v in cache.values() if v.get("website"))
                print(f"  {done}/{len(todo)} | {hits} with site", flush=True)
    PROFILES.write_text(json.dumps(cache, ensure_ascii=False))
    hits = sum(1 for v in cache.values() if v.get("website"))
    print(f"profiles done: {len(cache)}, {hits} with website", flush=True)


IMG_HOST = re.compile(r"(ytimg|ggpht|googleusercontent|cdn|imgur|cloudfront|"
                      r"\.(?:jpg|jpeg|png|gif|webp|svg)$)", re.I)


def stage_build():
    prof = json.loads(PROFILES.read_text()) if PROFILES.exists() else {}
    seen, rows = set(), []
    for slug, rec in prof.items():
        w = rec.get("website")
        # only trust the authoritative link + cross-validated bare-match;
        # drop the noisy first-external-link fallback (catches ytimg/CDN junk)
        if not w or rec.get("via") == "extlink":
            continue
        d = apex(w)
        if (not d or "." not in d or d in seen or BAD_HOST.search(d)
                or IMG_HOST.search(d) or IMG_HOST.search(w)):
            continue
        seen.add(d)
        rows.append({"domain": d, "company": slug.replace("-", " ").title(),
                     "website": w, "country": "US", "source": "goodfirms"})
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"built {len(rows)} unique GoodFirms agencies -> {OUT}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["listings", "profiles", "build"], required=True)
    ap.add_argument("--max-pages", type=int, default=60)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    if args.stage == "listings":
        stage_listings(args.max_pages)
    elif args.stage == "profiles":
        stage_profiles(args.workers)
    else:
        stage_build()


if __name__ == "__main__":
    main()
