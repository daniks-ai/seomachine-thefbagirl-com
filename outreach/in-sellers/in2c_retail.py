#!/usr/bin/env python3
"""
India Amazon-seller lead build, stage 2c: is it a *product* shop?

Stage 2b proves a store engine is installed, which is still not the same as
selling physical goods — Indian coaching institutes, spas, hotels and marketing
agencies all run WooCommerce to take payments, and none of them will ever have
an Amazon Ads account.

So look for the things a physical-goods retailer cannot avoid saying (shipping,
cash on delivery, returns, order tracking), count product URLs, and flag the
service verticals explicitly. Also re-reads the Amazon signal, because a footer
"buy on Amazon" badge is what promotes a lead to tier A.

Output: data/in_retail.jsonl  {domain, ship, prod, service, amz}

Usage:
    python3 outreach/in-sellers/in2c_retail.py --domains-file data/in_stores.txt
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from in2_crawl import DictResolver, UA, AMZ_LINK_RE, AMZ_TEXT_RE, AMZ_WEAK_RE  # noqa

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = DATA / "in_retail.jsonl"
MAX_BYTES = 250_000

SHIP_RE = re.compile(
    r"free shipping|free delivery|cash on delivery|\bcod\b|shipping policy|"
    r"shipping &amp;|shipping and returns|delivery charges|track your order|"
    r"track order|dispatch(?:ed)? within|returns? policy|refund policy|"
    r"exchange policy|ships? within|delivered within|shipping info")
PROD_RE = re.compile(r"/products?/[a-z0-9\-]{3,}")
SERVICE_RE = re.compile(
    r"\b(admission|syllabus|coaching|tuition|entrance exam|upsc|neet|iit-?jee|"
    r"training institute|internship|certification course|enroll now|"
    r"book (?:an )?appointment|consultation fee|salon|\bspa\b|clinic|"
    r"dentist|physiotherap|hotel booking|resort|homestay|tour package|"
    r"travel agency|seo services|digital marketing agency|web design|"
    r"app development|staffing|recruitment agency|real estate|"
    r"insurance plan|mutual fund|loan against)\b")


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
        amz = 0
        if "amazon" in low or "amzn" in low:
            if AMZ_LINK_RE.search(low) or AMZ_TEXT_RE.search(low):
                amz = 2
            elif AMZ_WEAK_RE.search(low):
                amz = 1
        out.append({"domain": host, "ok": True,
                    "ship": len(SHIP_RE.findall(low)),
                    "prod": len(set(PROD_RE.findall(low))),
                    "service": len(set(SERVICE_RE.findall(low))),
                    "amz": amz})


async def run(hosts, concurrency, dnsmap):
    sem = asyncio.Semaphore(concurrency)
    conn = aiohttp.TCPConnector(limit=concurrency, limit_per_host=2, ssl=False,
                                force_close=True, enable_cleanup_closed=True,
                                resolver=DictResolver(dnsmap) if dnsmap else None)
    timeout = aiohttp.ClientTimeout(total=15, connect=6, sock_read=8)
    headers = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
               "Accept-Language": "en-IN,en;q=0.9"}
    out, done = [], 0
    fh = OUT.open("a", encoding="utf-8")
    async with aiohttp.ClientSession(connector=conn, timeout=timeout,
                                     headers=headers) as s:
        tasks, it = set(), iter(hosts)
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
    ap.add_argument("--concurrency", type=int, default=150)
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
