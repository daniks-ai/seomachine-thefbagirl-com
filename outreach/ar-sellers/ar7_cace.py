#!/usr/bin/env python3
"""
Argentina lead engine, round 2: the CACE member directory.

CACE (Cámara Argentina de Comercio Electrónico) is the country's e-commerce
chamber; its public member directory is ~2,300 Argentine companies that sell
online or service those who do. Two things make it the best free source here:
every member is Argentine by definition (no geo-guessing needed), and the mix is
exactly our two segments — online brands/retailers plus the agencies, platforms
and consultancies that serve them.

The site runs on Shopify, so the member list comes out of
`/collections/socios/products.json` (250 per page) instead of HTML scraping.
Each member's own website only exists on its product page, as an outbound link,
so every member costs one extra fetch.

Output: data/ar_cace.jsonl  {domain, company, tier, source}

Usage:
    python3 outreach/ar-sellers/ar7_cace.py
    python3 outreach/ar-sellers/ar7_cace.py --workers 16
"""
import argparse
import collections
import random
import time
import concurrent.futures as cf
import gzip
import json
import re
import ssl
import threading
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = DATA / "ar_cace.jsonl"
CACHE = DATA / "_cace_members.json"
SITES = DATA / "_cace_sites.json"   # handle -> domain | "" (resume across runs)

BASE = "https://cace.org.ar"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# links present on every product page, or never a member's own site
CHROME = re.compile(
    r"(cace\.org\.ar|shopify|gstatic|googleapis|google\.com|gmpg\.org|w3\.org|"
    r"facebook|instagram|linkedin|twitter|x\.com|youtube|tiktok|whatsapp|"
    r"wa\.me|t\.me|spotify|apple\.com|play\.google|maps\.|lop\.global|"
    r"schema\.org|jquery|cdn\.|fonts\.)", re.I)

AGENCY_RE = re.compile(
    r"(agenc|consultor|estudio|marketing|publicidad|digital|performance|"
    r"media|seo|ads\b|growth|partner|marketplace|ecommerce|e-commerce|"
    r"comercio electr|software|desarrollo|tecnolog|solution|sistemas|"
    r"studio|lab\b|it\b|consulting)", re.I)
# platforms, banks, carriers, marketplaces: members, but never prospects
NOT_A_PROSPECT = re.compile(
    r"(mercado ?libre|mercado ?pago|tienda ?nube|vtex|shopify|woocommerce|"
    r"magento|prestashop|jumpseller|"
    r"banco|santander|galicia|bbva|macro|naranja|visa|mastercard|amex|"
    r"american express|prisma|payway|mobbex|ualá|uala|modo\b|"
    r"andreani|oca\b|correo argentino|urbano|dhl|fedex|ups\b|"
    r"google|meta\b|facebook|amazon web|aws\b|microsoft|salesforce|"
    r"despegar|falabella|garbarino|fravega|coto|carrefour|walmart)", re.I)

_lock = threading.Lock()


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Encoding": "gzip",
        "Accept": "text/html,application/json"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        raw = r.read(1_500_000)
        if r.headers.get("Content-Encoding") == "gzip":
            try:
                raw = gzip.decompress(raw)
            except OSError:
                pass
        return raw.decode("utf-8", "ignore")


def members():
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    out, page = [], 1
    while True:
        data = json.loads(fetch(
            f"{BASE}/collections/socios/products.json?limit=250&page={page}"))
        got = data.get("products") or []
        if not got:
            break
        out += [{"handle": p["handle"], "title": p["title"]} for p in got]
        print(f"  page {page}: +{len(got)} (total {len(out)})")
        page += 1
        if page > 30:
            break
    CACHE.write_text(json.dumps(out, ensure_ascii=False))
    return out


def site_of(handle):
    """Shopify rate-limits hard (429) — back off and retry rather than losing
    the member, which is what silently capped the first run at 261 of 2,393."""
    html = None
    for attempt in range(5):
        try:
            html = fetch(f"{BASE}/products/{handle}")
            break
        except urllib.error.HTTPError as ex:
            if ex.code != 429:
                return None
            time.sleep(2 * (attempt + 1) + random.random())
        except Exception:
            time.sleep(1 + random.random())
    if html is None:
        return None
    cands = [u for u in re.findall(r'href=["\']([^"\']+)["\']', html)
             if u.startswith("http") and not CHROME.search(u)]
    if not cands:
        return None
    hosts = [re.sub(r"^www\.", "", re.match(r"https?://([^/]+)", u).group(1).lower())
             for u in cands]
    hosts = [h for h in hosts if "." in h and not CHROME.search(h)]
    if not hosts:
        return None
    return collections.Counter(hosts).most_common(1)[0][0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--delay", type=float, default=0.7)
    args = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)

    ms = members()
    print(f"{len(ms)} CACE members")
    ms = [m for m in ms if not NOT_A_PROSPECT.search(m["title"])]
    print(f"{len(ms)} after dropping platforms/banks/carriers/marketplaces")

    sites = json.loads(SITES.read_text()) if SITES.exists() else {}
    todo = [m for m in ms if m["handle"] not in sites]
    print(f"{len(sites)} cached, {len(todo)} to fetch")
    done = [0]

    def run(m):
        d = site_of(m["handle"]) or ""
        time.sleep(args.delay)   # Shopify 429s above roughly 2 req/s
        with _lock:
            sites[m["handle"]] = d
            done[0] += 1
            if done[0] % 100 == 0:
                SITES.write_text(json.dumps(sites, ensure_ascii=False))
                got = sum(1 for v in sites.values() if v)
                print(f"  {done[0]}/{len(todo)} | {got} sites resolved")

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(run, todo))
    SITES.write_text(json.dumps(sites, ensure_ascii=False))

    by_handle = {m["handle"]: m for m in ms}
    rows = {}
    for handle, d in sites.items():
        m = by_handle.get(handle)
        if not d or not m or d in rows:
            continue
        rows[d] = {"domain": d, "company": m["title"][:60],
                   "tier": "B" if AGENCY_RE.search(m["title"]) else "C",
                   "source": "cace_directory"}

    with OUT.open("w", encoding="utf-8") as f:
        for r in rows.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    ar = sum(1 for d in rows if d.endswith(".ar"))
    print(f"\n{len(rows)} member websites ({ar} .ar) -> {OUT}")


if __name__ == "__main__":
    main()
