#!/usr/bin/env python3
"""
India Amazon-seller lead build, stage 2: crawl + qualify + harvest.

Input is a big universe of Indian websites (CrUX top-1M origins for IN, see
in0_universe.py). For each domain we fetch the homepage, record the signals that
say "Indian online seller", and pull published emails — chasing up to three
contact pages when the homepage shows none (which is where most Indian shops
keep the address).

Signals recorded per domain, none of them a hard gate here:
  amz    2 = Amazon product/store link or "buy on Amazon" copy, 1 = bare
         mention, 0 = none. NOT required: an Indian D2C brand nearly always
         sells on Amazon too but deliberately does not link to it from its own
         store, so this is a ranking input, not a filter (stage 3 tiers on it).
  india  .in TLD, or rupee/GSTIN/+91/"India" on the page.
  comm   cart/shop/product/price markup. Deliberately loose — stages 2b and 2c
         are what actually prove "this is a shop selling physical goods".

Output:   data/in_crawl.jsonl        one record per domain (append, resumable)
State:    data/_in_crawl_done.txt    domains already attempted

Usage:
    python3 outreach/in-sellers/in2_crawl.py --domains-file data/in_universe.txt \
        --limit 2000 --concurrency 120
"""
import argparse
import asyncio
import html as htmllib
import json
import re
import socket
import time
from pathlib import Path

import aiohttp


class DictResolver(aiohttp.abc.AbstractResolver):
    """Serve A records from stage 1 instead of calling getaddrinfo.

    aiohttp's default resolver runs getaddrinfo on the loop's thread pool
    (~14 threads), which throttled the first crawl to under 1 host/s. Stage 1
    already resolved the whole universe, so hand the addresses over directly.
    """

    def __init__(self, mapping):
        self.m = mapping

    async def resolve(self, host, port=0, family=socket.AF_INET):
        ip = self.m.get(host) or self.m.get(host[4:] if host.startswith("www.") else "")
        if not ip:
            raise OSError(f"unresolved {host}")
        return [{"hostname": host, "host": ip, "port": port,
                 "family": socket.AF_INET, "proto": 0, "flags": 0}]

    async def close(self):
        return

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = DATA / "in_crawl.jsonl"
DONE = DATA / "_in_crawl_done.txt"


def set_shard(n):
    """Per-shard files so several processes can crawl in parallel."""
    global OUT, DONE
    if n is not None:
        OUT = DATA / f"in_crawl_{n}.jsonl"
        DONE = DATA / f"_in_crawl_done_{n}.txt"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
MAX_BYTES = 300_000

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]{1,40}@[a-zA-Z0-9.\-]{1,50}\.[a-zA-Z]{2,12}")
# Scanning a whole page with EMAIL_RE.findall is quadratic: the local-part class
# happily eats a 100KB base64 blob before backtracking to look for an "@". Pages
# with inline data URIs cost ~120ms each that way, which was 90% of the crawl's
# CPU. Instead jump to each "@" and only match a short window around it.
EMAIL_AT_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]{1,40})@([a-zA-Z0-9\-]{1,50}(?:\.[a-zA-Z0-9\-]{1,30}){1,3})")
CF_RE = re.compile(r'data-cfemail=["\']([0-9a-fA-F]+)["\']')
# Only the bracketed spellings: a bare " at "/" dot " alternation backtracks
# over every page of English prose and cost more than the rest of the crawl
# combined, for a handful of extra addresses.
MUNGED_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]{1,40})\s?(?:\[at\]|\(at\)|\{at\}|&#64;)\s?"
    r"([a-zA-Z0-9.\-]{1,50})\s?(?:\[dot\]|\(dot\)|\{dot\})\s?([a-zA-Z]{2,12})",
    re.I)
LINK_RE = re.compile(r'href=["\']([^"\']{1,300})["\']', re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)

# these three run against an already-lowercased copy, so no re.I
AMZ_LINK_RE = re.compile(
    r"amazon\.[a-z.]{2,6}/[^\"'\s]{0,120}(?:/dp/|/gp/product/|/stores/|/shops/"
    r"|/sp\?|/s\?k=|/b\?node=)|amzn\.(?:to|in|eu)/|amazon\.in/dp/")
AMZ_TEXT_RE = re.compile(
    r"(?:buy|shop|available|order|purchase)[^<>]{0,24}\bon amazon"
    r"|find us on amazon|our amazon store|amazon storefront"
    r"|we sell on amazon|amazon\.in/dp|buy from amazon")
AMZ_WEAK_RE = re.compile(r"amazon\.in|amazon\.com|amzn\.")

INDIA_RE = re.compile(
    r"(&#8377;|₹|\bGSTIN?\b|\+91[\s\-]?\d|\bIndia\b|\bBharat\b|\bRs\.?\s?\d|INR)")
COMMERCE_RE = re.compile(
    r"add to cart|add-to-cart|addtocart|/cart|buy now|shop now|woocommerce"
    r"|shopify|/collections/|/product/|/products/|checkout|shop all|\bsku\b")

JUNK_EMAIL_RE = re.compile(
    r"(no-?reply|noreply|donotreply|postmaster|mailer-daemon|abuse@|"
    r"hostmaster|dns-admin|webmaster@localhost|sentry|wixpress|"
    r"@(?:example|test|domain|yourdomain|yoursite|company|email|mail)\.(?:com|in)|"
    r"@(?:sentry|wix|squarespace|godaddy|wordpress|shopify|cloudflare|"
    r"jsdelivr|schema|w3|adobe|placeholder)\.|"
    r"\.(png|jpe?g|gif|svg|webp|css|js|ico|woff2?|ttf|eot|mp4|pdf)$|"
    r"^(?:name|your|user|username|firstname|lastname|someone|somebody|"
    r"email|mail|address|xxx|abc|test|demo|sample)@)", re.I)

CONTACT_HINT = re.compile(
    r"(contact|about|reach|touch|enquir|inquir|support|connect|help|"
    r"customer-care|write-to-us|policies)", re.I)
BAD_PATH = re.compile(
    r"\.(pdf|jpg|jpeg|png|gif|svg|zip|mp4|webp|css|js)$|/cdn-cgi/|"
    r"(facebook|instagram|twitter|linkedin|youtube|whatsapp|pinterest)\.com", re.I)


def cf_decode(hexstr):
    try:
        b = bytes.fromhex(hexstr)
        k = b[0]
        return "".join(chr(c ^ k) for c in b[1:])
    except Exception:
        return ""


def extract_emails(text, host):
    found = set()
    pos = text.find("@")
    n = 0
    while pos != -1 and n < 400:
        n += 1
        m = EMAIL_AT_RE.search(text, max(0, pos - 41), pos + 82)
        if m:
            found.add(m.group(0).strip(".").lower())
        pos = text.find("@", pos + 1)
    if "data-cfemail" in text:
        for hx in CF_RE.findall(text):
            d = cf_decode(hx)
            if d and EMAIL_RE.fullmatch(d):
                found.add(d.lower())
    if ("(at)" in text or "[at]" in text or "{at}" in text or "&#64;" in text):
        for a, b, c in MUNGED_RE.findall(text):
            found.add(f"{a}@{b}.{c}".lower())
    out = []
    for e in found:
        if JUNK_EMAIL_RE.search(e) or len(e) > 70 or e.count("@") != 1:
            continue
        local, dom = e.split("@")
        if not local or len(dom) < 4 or dom.endswith("."):
            continue
        # image sprites / minified junk sometimes look like addresses
        if re.search(r"\d{6,}", local) or len(local) > 40:
            continue
        out.append(e)
    return sorted(set(out))


def score(text, host):
    """Cheap substring guards first — the regexes are the crawl's CPU budget.

    Running every pattern over a few hundred KB of HTML blocked the event loop
    hard enough that healthy hosts timed out, so nothing expensive runs unless a
    plain `in` test says it might match.
    """
    low = text.lower()
    strong = weak = False
    if "amazon" in low or "amzn" in low:
        weak = bool(AMZ_WEAK_RE.search(low))
        strong = bool(AMZ_LINK_RE.search(low)) or bool(AMZ_TEXT_RE.search(low))
    india = host.endswith(".in") or bool(INDIA_RE.search(text))
    comm = bool(COMMERCE_RE.search(low))
    return strong, weak, india, comm


async def fetch(session, url):
    try:
        async with session.get(url, allow_redirects=True) as r:
            if r.status >= 400:
                return None, r.status
            buf = b""
            async for chunk in r.content.iter_chunked(32768):
                buf += chunk
                if len(buf) >= MAX_BYTES:
                    break
            return buf.decode("utf-8", "ignore"), r.status
    except Exception:
        return None, 0


def contact_links(text, host):
    out = []
    for href in LINK_RE.findall(text):
        if BAD_PATH.search(href) or not CONTACT_HINT.search(href):
            continue
        if href.startswith("http"):
            if host not in href:
                continue
            u = href
        elif href.startswith("/"):
            u = f"https://{host}{href}"
        else:
            continue
        if u not in out:
            out.append(u)
        if len(out) >= 3:
            break
    return out


async def handle(session, host, sem, results, lock):
    async with sem:
        text, st = await fetch(session, f"https://{host}/")
        if text is None:
            text, st = await fetch(session, f"http://{host}/")
        if text is None:
            rec = {"domain": host, "ok": False, "status": st}
        else:
            strong, weak, india, comm = score(text, host)
            emails = extract_emails(text, host)
            title = ""
            m = TITLE_RE.search(text)
            if m:
                title = htmllib.unescape(re.sub(r"\s+", " ", m.group(1))).strip()[:120]
            pages = 1
            # Indian D2C brands keep the address on a contact page and often
            # never link Amazon from the homepage, so chase contact pages for
            # every commerce site, not just the ones already showing an Amazon
            # link — that is where most of the addresses actually are.
            if india and comm and not emails:
                for u in contact_links(text, host):
                    t2, _ = await fetch(session, u)
                    pages += 1
                    if t2:
                        emails = extract_emails(t2, host)
                        s2, w2, i2, c2 = score(t2, host)
                        strong = strong or s2
                        weak = weak or w2
                        if emails:
                            break
            rec = {"domain": host, "ok": True, "title": title,
                   "amz": 2 if strong else (1 if weak else 0),
                   "india": india, "comm": comm, "emails": emails,
                   "pages": pages}
    async with lock:
        results.append(rec)


async def run(hosts, concurrency, dnsmap, flush_every=200):
    sem = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    results = []
    conn = aiohttp.TCPConnector(limit=concurrency, limit_per_host=2, ssl=False,
                                force_close=True, enable_cleanup_closed=True,
                                resolver=DictResolver(dnsmap) if dnsmap else None)
    timeout = aiohttp.ClientTimeout(total=15, connect=6, sock_read=8)
    headers = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
               "Accept-Language": "en-IN,en;q=0.9"}
    n_qual = 0
    t0 = time.time()
    async with aiohttp.ClientSession(connector=conn, timeout=timeout,
                                     headers=headers) as session:
        tasks = set()
        it = iter(hosts)
        done_count = 0
        while True:
            while len(tasks) < concurrency * 2:
                h = next(it, None)
                if h is None:
                    break
                tasks.add(asyncio.create_task(handle(session, h, sem, results, lock)))
            if not tasks:
                break
            fin, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            done_count += len(fin)
            if len(results) >= flush_every:
                n_qual += flush(results)
                print(f"  {done_count}/{len(hosts)} crawled | {n_qual} qualified "
                      f"| {done_count/max(1e-9, time.time()-t0):.0f}/s", flush=True)
        n_qual += flush(results)
    return n_qual


def flush(results):
    if not results:
        return 0
    q = 0
    with OUT.open("a", encoding="utf-8") as f, DONE.open("a", encoding="utf-8") as d:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            d.write(r["domain"] + "\n")
            if r.get("ok") and r.get("amz", 0) >= 1 and r.get("india") \
                    and r.get("comm") and r.get("emails"):
                q += 1
    results.clear()
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains-file", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=120)
    ap.add_argument("--dns-file", default="data/in_dns.tsv")
    ap.add_argument("--shard", type=int)
    ap.add_argument("--shards", type=int, default=1)
    args = ap.parse_args()
    set_shard(args.shard)

    DATA.mkdir(parents=True, exist_ok=True)
    done = set()
    for f in list(DATA.glob("_in_crawl_done*.txt")):
        done |= {l.strip() for l in f.read_text().splitlines() if l.strip()}
    p = Path(args.domains_file)
    if not p.is_absolute():
        p = HERE / p
    hosts = [h.strip() for h in p.read_text().splitlines() if h.strip()]
    hosts = [h for h in hosts if h not in done]
    if args.shards > 1:
        hosts = [h for i, h in enumerate(hosts) if i % args.shards == args.shard]
    hosts = hosts[args.offset:]
    if args.limit:
        hosts = hosts[: args.limit]
    dnsmap = {}
    dp = Path(args.dns_file)
    if not dp.is_absolute():
        dp = HERE / dp
    if dp.exists():
        for line in dp.read_text().splitlines():
            h, _, ip = line.partition("\t")
            if ip:
                dnsmap[h] = ip
    print(f"{len(done)} already done | crawling {len(hosts)} "
          f"at concurrency {args.concurrency} | dns map {len(dnsmap)}", flush=True)
    if not hosts:
        return
    n = asyncio.run(run(hosts, args.concurrency, dnsmap))
    print(f"done. qualified this run: {n}")


if __name__ == "__main__":
    main()
