#!/usr/bin/env python3
"""
Author-site crawler for the KDP authors round.

Descends from outreach/kdp/harvest_crawl.py (same Cloudflare/[at]/JSON-LD
decoding) with three additions that matter at this scale:

  * **outbound link harvest** — indie authors cross-promote constantly
    (blogrolls, "author friends", newsletter-swap and blog-tour pages), so every
    crawl also returns the external domains it saw. That feeds wave 2 for free
    and is where most of the volume comes from once the SERP list is spent.
  * **author signals** — kindle/amazon/"my books" markers plus a title, so the
    build step can tell a real author site from a bookshop or a review blog.
  * separate output files, so a parallel session working in outreach/kdp/ is
    never touched.

Usage:
    python3 outreach/kdp-authors/crawl_authors.py --domains-file data/wave1.txt \
        --tag wave1 --workers 40
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

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
HREF_RE = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
CF_RE = re.compile(r'data-cfemail=["\']([0-9a-fA-F]+)["\']')
CF_HREF_RE = re.compile(r'/cdn-cgi/l/email-protection#([0-9a-fA-F]+)')
TAG_RE = re.compile(r"<[^>]+>")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
JSONLD_RE = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.I | re.S)
INLINE_JSON_RE = re.compile(
    r'(?:__NEXT_DATA__|__NUXT__|__INITIAL_STATE__|warmupData)\s*=\s*(\{.*?\})\s*[;<]', re.S)

SCORES = [
    (re.compile(r"(contact|get-in-touch|getintouch|reach|connect|email-me)", re.I), 100),
    (re.compile(r"(about|bio|meet|who-i-am|my-story)", re.I), 75),
    (re.compile(r"(media-kit|press|presskit)", re.I), 70),
    (re.compile(r"(newsletter|subscribe|mailing-list)", re.I), 45),
    (re.compile(r"(books|novels|library|catalog|titles|works)", re.I), 40),
    (re.compile(r"(services|rates|hire|work-with)", re.I), 35),
    (re.compile(r"(faq|help|support|imprint|impressum|legal|privacy)", re.I), 30),
]
SKIP_LINK = re.compile(
    r"(\.(png|jpe?g|gif|svg|webp|css|js|pdf|zip|mp4|mp3|ico)$|"
    r"^(mailto:|tel:|javascript:|#)|/(cart|checkout|login|signin|account|wp-admin|feed)/?$)",
    re.I)

JUNK_RE = re.compile(
    r"(no-?reply|noreply|postmaster|mailer-daemon|abuse@|hostmaster|dns-admin|"
    r"sentry|wixpress|@(?:example|wix|squarespace|godaddy|wordpress|shopify|"
    r"cloudflare|googlemail|domain|email|yourdomain|company|sample|test|sentry|"
    r"mysite|yoursite|website|adobe|netlify|vercel|automattic)\.)", re.I)
IMG_EXT_RE = re.compile(r"\.(png|jpg|jpeg|gif|svg|webp|css|js|ico|woff|ttf)$", re.I)
HEX_LOCAL = re.compile(r"^[0-9a-f]{16,}$")

# Domains that are never a lead — same list the SERP filter uses, kept here so
# the outbound-link harvest does not snowball into retailers and socials.
PLATFORM = re.compile(
    r"(^|\.)("
    r"amazon|amzn|goodreads|bookbub|kobo|barnesandnoble|bn|audible|apple|itunes|"
    r"smashwords|draft2digital|books2read|ingramspark|lulu|blurb|bookbaby|payhip|"
    r"gumroad|bookfunnel|storyoriginapp|prolificworks|instafreebie|"
    r"waterstones|booktopia|whsmith|foyles|indigo|chapters|thriftbooks|abebooks|"
    r"alibris|betterworldbooks|bookdepository|wordery|blackwells|hive|"
    r"facebook|fb|instagram|twitter|x|threads|tiktok|youtube|youtu|pinterest|"
    r"linkedin|reddit|tumblr|medium|substack|patreon|kickstarter|indiegogo|"
    r"discord|twitch|spotify|soundcloud|linktr|beacons|carrd|about|"
    r"wikipedia|wikimedia|fandom|quora|yelp|tripadvisor|glassdoor|indeed|"
    r"wordpress|blogspot|blogger|wix|weebly|squarespace|godaddy|shopify|etsy|"
    r"myshopify|bigcartel|ecwid|square|stripe|paypal|venmo|kofi|ko-fi|"
    r"ebay|walmart|target|costco|google|gstatic|bing|yahoo|msn|duckduckgo|"
    r"mailchimp|convertkit|kit|aweber|activecampaign|constantcontact|klaviyo|"
    r"eventbrite|calendly|zoom|canva|adobe|cloudflare|netlify|vercel|"
    r"penguinrandomhouse|penguin|randomhouse|harpercollins|simonandschuster|"
    r"hachette|macmillan|scholastic|bloomsbury|faber|quarto|wiley|pearson|"
    r"publishersweekly|kirkusreviews|booklistonline|libraryjournal|netgalley|"
    r"nytimes|guardian|telegraph|bbc|cnn|forbes|entrepreneur|inc|"
    r"businessinsider|huffpost|buzzfeed|wired|writersdigest|janefriedman|"
    r"reedsy|scribophile|wattpad|inkitt|royalroad|archiveofourown|fanfiction|"
    r"librarything|storygraph|bookshop|bookriot|epicreads|allianceindependentauthors|"
    r"creativecommons|w3|schema|gravatar|wp|jetpack|akismet"
    r")\.",
    re.I)
BAD_TLD = re.compile(r"\.(gov|edu|mil|gov\.uk|ac\.uk|edu\.au|gov\.au|gc\.ca)$", re.I)

AUTHOR_SIG = re.compile(
    r"(kindle|amazon\.|kindle unlimited|my books|my novels|my latest book|"
    r"available on amazon|preorder|pre-order|audiobook|paperback|newsletter|"
    r"arc team|street team|book \d|series)", re.I)
PERSON_SIG = re.compile(r"(author of|i write|i'm an author|my books|my novels|debut novel)", re.I)
FORM_SIG = re.compile(r"<form[^>]*(contact|message|inquiry|enquiry)|wpcf7|gform|formidable|"
                      r"typeform|jotform|hsforms", re.I)

MAX_PAGES = 7
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html",
                                               "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        ct = r.headers.get("Content-Type", "")
        if "html" not in ct and "text" not in ct:
            return "", r.geturl()
        raw = r.read(900_000)
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
    if isinstance(obj, dict):
        for v in obj.values():
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
        e = re.sub(r"^(mailto:|%20|%40|u003e|3e)+", "", e)
        if not EMAIL_RE.fullmatch(e) or len(e) > 80:
            continue
        if IMG_EXT_RE.search(e) or JUNK_RE.search(e):
            continue
        local, host = e.split("@")
        if HEX_LOCAL.match(local) or not local or "." not in host:
            continue
        out.add(e)
    return out


def ext_domain(url):
    try:
        h = urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""
    h = h[4:] if h.startswith("www.") else h
    if not h or "." not in h or h.count(".") > 3:
        return ""
    if BAD_TLD.search(h) or PLATFORM.search("." + h):
        return ""
    return h


def harvest(domain):
    rec = {"domain": domain, "emails": [], "pages": 0, "ext": [],
           "title": "", "author_score": 0, "has_form": False}
    base = None
    first = None
    for scheme in ("https://", "http://"):
        try:
            html, final = fetch(scheme + domain)
            base, first = final, (final, html)
            break
        except Exception as e:
            rec["error"] = str(e)[:40]
    if base is None or not first[1]:
        return rec
    rec.pop("error", None)

    parsed = urllib.parse.urlparse(base)
    root = f"{parsed.scheme}://{parsed.netloc}"
    host = parsed.netloc.replace("www.", "")

    m = TITLE_RE.search(first[1])
    if m:
        rec["title"] = htmllib.unescape(TAG_RE.sub(" ", m.group(1))).strip()[:120]

    cands, ext = {}, {}
    for href, label in HREF_RE.findall(first[1]):
        if SKIP_LINK.search(href):
            continue
        full = urllib.parse.urljoin(root, href.split("#")[0])
        netloc = urllib.parse.urlparse(full).netloc
        if host not in netloc:
            d = ext_domain(full)
            if d and d != host:
                ext[d] = ext.get(d, 0) + 1
            continue
        if full.rstrip("/") == base.rstrip("/"):
            continue
        blob = href + " " + TAG_RE.sub(" ", label)
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

    emails, score = set(), 0
    for url, html in pages:
        rec["pages"] += 1
        for hx in CF_RE.findall(html) + CF_HREF_RE.findall(html):
            d = cf_decode(hx)
            if "@" in d:
                emails.add(d)
        plain = deobfuscate(html)
        emails |= set(EMAIL_RE.findall(plain))
        emails.update(re.findall(r'mailto:([^"\'?>&\s]+)', plain, re.I))
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
        text = TAG_RE.sub(" ", html)
        score += len(AUTHOR_SIG.findall(text)) + 3 * len(PERSON_SIG.findall(text))
        if FORM_SIG.search(html):
            rec["has_form"] = True
        # outbound links from deeper pages too — blogrolls often live on /links
        for href, _ in HREF_RE.findall(html):
            if href.startswith(("http://", "https://")):
                d = ext_domain(href)
                if d and d != host:
                    ext[d] = ext.get(d, 0) + 1

    rec["emails"] = sorted(clean(emails))
    rec["author_score"] = score
    rec["ext"] = sorted(ext.items(), key=lambda kv: -kv[1])[:60]
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains-file", required=True)
    ap.add_argument("--tag", default="wave1")
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    out = DATA / f"contacts_{args.tag}.json"
    progress = DATA / f"_progress_{args.tag}.json"

    domains = [d.strip().lower() for d in Path(args.domains_file).read_text().splitlines()
               if d.strip()]
    cache = json.loads(progress.read_text()) if progress.exists() else {}
    todo = [d for d in domains if d not in cache]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(cache)} cached, crawling {len(todo)} domains -> {out}", flush=True)

    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(harvest, d): d for d in todo}
        for fut in cf.as_completed(futs):
            d = futs[fut]
            try:
                cache[d] = fut.result()
            except Exception as e:
                cache[d] = {"domain": d, "emails": [], "error": str(e)[:40]}
            done += 1
            if done % 100 == 0:
                progress.write_text(json.dumps(cache, ensure_ascii=False))
                hits = sum(1 for v in cache.values() if v.get("emails"))
                print(f"  {done}/{len(todo)} | {hits} domains with email", flush=True)

    progress.write_text(json.dumps(cache, ensure_ascii=False))
    records = list(cache.values())
    out.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    hits = sum(1 for v in records if v.get("emails"))
    print(f"crawled {len(records)} | {hits} with email | wrote {out}")


if __name__ == "__main__":
    main()
