#!/usr/bin/env python3
"""
Third-pass harvester: crawl the whole small site instead of guessing paths.

Why: Celebrate Lit published its address on `/19-2/` (a services page) — a URL
no path-guessing heuristic would ever try. So this pass enumerates the site's
own internal links, scores them, and reads the best ~14 pages per domain.

Adds over harvest_deep.py:
  * link enumeration + scoring (contact/about/team/services/pricing/submissions/
    faq/press/work-with) instead of a fixed path list
  * JSON-LD / schema.org parsing — `email`, `contactPoint`, `author` fields
  * inline-JSON scan (__NEXT_DATA__, __NUXT__, wix warmup data)
  * keeps Cloudflare + [at]/[dot] decoding from v2

Usage:
    python3 outreach/kdp/harvest_crawl.py --domains-file outreach/kdp/data/crawl_targets.txt
"""
import argparse
import concurrent.futures as cf
import gzip
import html as htmllib
import json
import re
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
OUT = DATA / "kdp_contacts_crawl.json"
PROGRESS = DATA / "_crawl_progress.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
HREF_RE = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
CF_RE = re.compile(r'data-cfemail=["\']([0-9a-fA-F]+)["\']')
CF_HREF_RE = re.compile(r'/cdn-cgi/l/email-protection#([0-9a-fA-F]+)')
TAG_RE = re.compile(r"<[^>]+>")
JSONLD_RE = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.I | re.S)
INLINE_JSON_RE = re.compile(
    r'(?:__NEXT_DATA__|__NUXT__|__INITIAL_STATE__|warmupData)\s*=\s*(\{.*?\})\s*[;<]', re.S)

# link scoring — higher is fetched first
SCORES = [
    (re.compile(r"(contact|get-in-touch|getintouch|reach-us|connect)", re.I), 100),
    (re.compile(r"(about|our-story|who-we-are|meet)", re.I), 70),
    (re.compile(r"(team|staff|people|founder)", re.I), 65),
    (re.compile(r"(submission|submit|query|pitch)", re.I), 60),
    (re.compile(r"(service|package|pricing|rate|price|work-with|hire)", re.I), 55),
    (re.compile(r"(faq|help|support)", re.I), 45),
    (re.compile(r"(press|media-kit|partner|affiliate|advertis)", re.I), 40),
]
SKIP_LINK = re.compile(
    r"(\.(png|jpe?g|gif|svg|webp|css|js|pdf|zip|mp4|mp3|ico)$|"
    r"^(mailto:|tel:|javascript:|#)|/(cart|checkout|login|signin|account|wp-admin|feed)/?$|"
    r"(facebook|twitter|instagram|linkedin|pinterest|youtube|tiktok)\.com)", re.I)

JUNK_RE = re.compile(
    r"(no-?reply|noreply|postmaster|mailer-daemon|abuse|hostmaster|dns-admin|privacy@|"
    r"sentry|wixpress|@(?:example|wix|squarespace|godaddy|wordpress|shopify|"
    r"cloudflare|googlemail|domain|email|yourdomain|company|sample|test|sentry)\.)", re.I)
IMG_EXT_RE = re.compile(r"\.(png|jpg|jpeg|gif|svg|webp|css|js|ico|woff|ttf)$", re.I)
HEX_LOCAL = re.compile(r"^[0-9a-f]{16,}$")

MAX_PAGES = 14
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html",
                                               "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        ct = r.headers.get("Content-Type", "")
        if "html" not in ct and "text" not in ct:
            return "", r.geturl()
        raw = r.read(1_500_000)
        if r.headers.get("Content-Encoding") == "gzip":
            try:
                raw = gzip.decompress(raw)
            except OSError:
                pass
        return raw.decode("utf-8", "replace"), r.geturl()


def cf_decode(hexstr):
    try:
        data = bytes.fromhex(hexstr)
        key = data[0]
        return "".join(chr(b ^ key) for b in data[1:])
    except Exception:
        return ""


def deobfuscate(text):
    t = htmllib.unescape(text)
    t = re.sub(r"\s*[\[\(\{]\s*at\s*[\]\)\}]\s*", "@", t, flags=re.I)
    t = re.sub(r"\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*", ".", t, flags=re.I)
    t = re.sub(r"\s+\bat\b\s+(?=[a-z0-9.\-]+\.[a-z]{2,})", "@", t, flags=re.I)
    t = re.sub(r"\s+\bdot\b\s+", ".", t, flags=re.I)
    return t


def walk_json(obj, found):
    """Pull any string that looks like an email out of a nested JSON blob."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and "@" in v and EMAIL_RE.search(v):
                found.update(EMAIL_RE.findall(v))
            else:
                walk_json(v, found)
    elif isinstance(obj, list):
        for v in obj:
            walk_json(v, found)
    elif isinstance(obj, str) and "@" in obj:
        found.update(EMAIL_RE.findall(obj))


def clean(found):
    out = set()
    for e in found:
        e = e.strip().strip(".,;:\"'<>()").lower()
        e = re.sub(r"^(mailto:|%20|%40|u003e)+", "", e)
        if not EMAIL_RE.fullmatch(e) or len(e) > 80:
            continue
        if IMG_EXT_RE.search(e) or JUNK_RE.search(e):
            continue
        local, host = e.split("@")
        if HEX_LOCAL.match(local) or not local or "." not in host:
            continue
        out.add(e)
    return out


def harvest(domain):
    rec = {"domain": domain, "emails": [], "pages": 0, "via": []}
    base = None
    for scheme in ("https://", "http://"):
        try:
            html, final = fetch(scheme + domain)
            base = final
            first = (final, html)
            break
        except Exception as e:
            rec["error"] = str(e)[:50]
    if base is None:
        return rec
    rec.pop("error", None)

    parsed = urllib.parse.urlparse(base)
    root = f"{parsed.scheme}://{parsed.netloc}"
    host = parsed.netloc.replace("www.", "")

    # score internal links
    cands = {}
    for href, label in HREF_RE.findall(first[1]):
        if SKIP_LINK.search(href):
            continue
        full = urllib.parse.urljoin(root, href.split("#")[0])
        if host not in urllib.parse.urlparse(full).netloc:
            continue
        if full.rstrip("/") == base.rstrip("/"):
            continue
        text = TAG_RE.sub(" ", label)
        blob = href + " " + text
        score = 0
        for rx, pts in SCORES:
            if rx.search(blob):
                score = max(score, pts)
        if score:
            cands[full] = max(cands.get(full, 0), score)

    order = [u for u, _ in sorted(cands.items(), key=lambda kv: -kv[1])][: MAX_PAGES - 1]
    pages = [first]
    for url in order:
        if len(pages) >= MAX_PAGES:
            break
        try:
            html, final = fetch(url)
            if html:
                pages.append((final, html))
        except Exception:
            pass

    emails = set()
    for url, html in pages:
        rec["pages"] += 1
        before = len(emails)
        for hx in CF_RE.findall(html) + CF_HREF_RE.findall(html):
            d = cf_decode(hx)
            if "@" in d:
                emails.add(d)
        plain = deobfuscate(html)
        emails |= set(EMAIL_RE.findall(plain))
        for m in re.findall(r'mailto:([^"\'?>&\s]+)', plain, re.I):
            emails.add(m)
        # structured data
        for blob in JSONLD_RE.findall(html):
            try:
                walk_json(json.loads(blob.strip()), emails)
            except Exception:
                emails |= set(EMAIL_RE.findall(blob))
        for blob in INLINE_JSON_RE.findall(html):
            try:
                walk_json(json.loads(blob), emails)
            except Exception:
                pass
        if len(emails) > before:
            rec["via"].append(url)

    rec["emails"] = sorted(clean(emails))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains-file", default=str(DATA / "crawl_targets.txt"))
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    domains = [d.strip() for d in Path(args.domains_file).read_text().splitlines() if d.strip()]
    cache = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    todo = [d for d in domains if d not in cache]
    print(f"{len(cache)} cached, crawling {len(todo)} domains")

    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(harvest, d): d for d in todo}
        for fut in cf.as_completed(futs):
            d = futs[fut]
            try:
                cache[d] = fut.result()
            except Exception as e:  # noqa
                cache[d] = {"domain": d, "emails": [], "error": str(e)[:50]}
            done += 1
            if done % 25 == 0:
                PROGRESS.write_text(json.dumps(cache, ensure_ascii=False))
                hits = sum(1 for v in cache.values() if v.get("emails"))
                print(f"  {done}/{len(todo)} | {hits} with email")

    PROGRESS.write_text(json.dumps(cache, ensure_ascii=False))
    records = list(cache.values())
    OUT.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    hits = sum(1 for v in records if v.get("emails"))
    print(f"crawled {len(records)} | {hits} with email | wrote {OUT}")


if __name__ == "__main__":
    main()
