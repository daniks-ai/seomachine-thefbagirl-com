#!/usr/bin/env python3
"""
India Amazon-seller lead build, stage 2b: prove the site is actually a shop.

Stage 2's commerce test (cart/checkout/product/sku wording) is far too generous
— it let through a medical college, a football-scores site and a travel agency,
because those words appear on ordinary pages. Sending Amazon-PPC outreach to
them would be spam.

This pass re-fetches only the candidate domains and looks for a *store engine*:
Shopify/WooCommerce/Magento/OpenCart/Dukaan markup, a cart or checkout endpoint,
or several rupee-denominated prices on one page. Cheap — the candidate set is a
tenth of the crawl — and it turns a soft signal into a hard one.

Output: data/in_platform.jsonl  {domain, plat, prices, cart, ok}

Usage:
    python3 outreach/in-sellers/in2b_platform.py --domains-file data/in_candidates.txt
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from in2_crawl import DictResolver, UA  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = DATA / "in_platform.jsonl"
MAX_BYTES = 250_000

PLATFORMS = [
    ("shopify", re.compile(r"cdn\.shopify\.com|myshopify\.com|/cdn/shop/|"
                           r"shopify-features|shopify\.loadfeatures")),
    ("woocommerce", re.compile(r"woocommerce|wp-content/plugins/woocommerce|"
                               r"wc-ajax|add-to-cart=\d")),
    ("magento", re.compile(r"magento|/static/version\d+/frontend/|mage/cookies")),
    ("opencart", re.compile(r"index\.php\?route=product|opencart")),
    ("prestashop", re.compile(r"prestashop")),
    ("bigcommerce", re.compile(r"bigcommerce\.com|stencil-utils")),
    ("wix-stores", re.compile(r"wixstores|wix-stores|ecom-platform")),
    ("dukaan", re.compile(r"mydukaan\.io|dukaan\.app")),
    ("instamojo", re.compile(r"instamojo\.com/\w")),
    ("zoho-commerce", re.compile(r"zohocommerce|zohostatic\.com/commerce")),
]
CART_RE = re.compile(r"/cart\.js|/cart/add|add-to-cart|/checkout\b|"
                     r"cart\.php|/basket\b")
PRICE_RE = re.compile(r"(?:₹|&#8377;|rs\.?\s?|inr\s?)\s?\d[\d,]{1,9}")


async def one(session, host, out, sem):
    async with sem:
        text = None
        for scheme in ("https", "http"):
            try:
                async with session.get(f"{scheme}://{host}/") as r:
                    if r.status >= 400:
                        continue
                    buf = b""
                    async for chunk in r.content.iter_chunked(32768):
                        buf += chunk
                        if len(buf) >= MAX_BYTES:
                            break
                    text = buf.decode("utf-8", "ignore")
                    break
            except Exception:
                continue
        if text is None:
            out.append({"domain": host, "ok": False})
            return
        low = text.lower()
        plat = ""
        for name, rx in PLATFORMS:
            if rx.search(low):
                plat = name
                break
        out.append({"domain": host, "ok": True, "plat": plat,
                    "cart": bool(CART_RE.search(low)),
                    "prices": len(PRICE_RE.findall(low))})


async def run(hosts, concurrency, dnsmap):
    sem = asyncio.Semaphore(concurrency)
    conn = aiohttp.TCPConnector(limit=concurrency, limit_per_host=2, ssl=False,
                                force_close=True, enable_cleanup_closed=True,
                                resolver=DictResolver(dnsmap) if dnsmap else None)
    timeout = aiohttp.ClientTimeout(total=15, connect=6, sock_read=8)
    headers = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
               "Accept-Language": "en-IN,en;q=0.9"}
    out = []
    fh = OUT.open("a", encoding="utf-8")
    done = 0
    async with aiohttp.ClientSession(connector=conn, timeout=timeout,
                                     headers=headers) as s:
        tasks = set()
        it = iter(hosts)
        while True:
            while len(tasks) < concurrency * 2:
                h = next(it, None)
                if h is None:
                    break
                tasks.add(asyncio.create_task(one(s, h, out, sem)))
            if not tasks:
                break
            fin, tasks = await asyncio.wait(tasks,
                                            return_when=asyncio.FIRST_COMPLETED)
            done += len(fin)
            if len(out) >= 500:
                fh.writelines(json.dumps(r) + "\n" for r in out)
                fh.flush()
                out.clear()
                print(f"  {done}/{len(hosts)}", flush=True)
    fh.writelines(json.dumps(r) + "\n" for r in out)
    fh.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains-file", required=True)
    ap.add_argument("--concurrency", type=int, default=200)
    args = ap.parse_args()
    done = set()
    if OUT.exists():
        done = {json.loads(l)["domain"] for l in OUT.open() if l.strip()}
    p = Path(args.domains_file)
    if not p.is_absolute():
        p = HERE / p
    hosts = [h.strip() for h in p.read_text().splitlines()
             if h.strip() and h.strip() not in done]
    dnsmap = {}
    for line in (DATA / "in_dns.tsv").read_text().splitlines():
        h, _, ip = line.partition("\t")
        if ip:
            dnsmap[h] = ip
    print(f"{len(done)} cached | checking {len(hosts)}", flush=True)
    if hosts:
        asyncio.run(run(hosts, args.concurrency, dnsmap))


if __name__ == "__main__":
    main()
