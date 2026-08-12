#!/usr/bin/env python3
"""
Scrape UK book-industry directories for the British KDP outreach round (r8).

Sources
  reedsy   Reedsy's GB publisher directory — every genre facet, all pages.
           Server-rendered HTML: name in `h3.text-heavy`, website + location in
           the card body. Gives indie presses that sell their own catalogue
           (the "publishers direct" bucket).

Usage
  python3 outreach/kdp/scrape_uk_directories.py --source reedsy
Output
  data/uk/dir_reedsy.jsonl   {"name","domain","what","country","location","source"}
"""
import argparse
import gzip
import html as htmllib
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

DATA = Path(__file__).resolve().parent / "data" / "uk"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

CARD_RE = re.compile(r'<div class="directory-result panel.*?</div>\s*</div>\s*</div>', re.S)
NAME_RE = re.compile(r'<h3 class="text-heavy">\s*(.*?)\s*</h3>', re.S)
GENRE_RE = re.compile(r'<b>Genres:</b>\s*(.*?)\s*</p>', re.S)
LOC_RE = re.compile(r'<b>Location:</b>\s*(.*?)\s*</p>', re.S)
SITE_RE = re.compile(r'<b>Website:</b>.*?href="([^"]+)"', re.S)
TAG_RE = re.compile(r"<[^>]+>")


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "text/html",
                                                       "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ""
            time.sleep(1 + i)
        except Exception:
            time.sleep(1 + i)
    return ""


def clean(s):
    return htmllib.unescape(TAG_RE.sub("", s or "")).strip()


def norm_domain(url):
    try:
        host = urlparse(url if "//" in url else "https://" + url).netloc.lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def scrape_reedsy():
    root = "https://reedsy.com/resources/publishers/gb/"
    index = fetch(root)
    genres = sorted(set(re.findall(r'href="(/resources/publishers/gb/[a-z0-9\-]+/)"', index)))
    print(f"{len(genres)} genre facets")
    out, seen = [], set()
    for g in genres:
        page = 1
        while True:
            url = f"https://reedsy.com{g}" if page == 1 else f"https://reedsy.com{g}page/{page}/"
            h = fetch(url)
            if not h or "directory-result" not in h:
                break
            cards = CARD_RE.findall(h)
            new = 0
            for c in cards:
                name = clean(NAME_RE.search(c).group(1)) if NAME_RE.search(c) else ""
                site = SITE_RE.search(c)
                dom = norm_domain(site.group(1)) if site else ""
                if not name or not dom or dom in seen:
                    continue
                seen.add(dom)
                new += 1
                out.append({
                    "name": name,
                    "domain": dom,
                    "what": clean(GENRE_RE.search(c).group(1))[:200] if GENRE_RE.search(c) else "",
                    "location": clean(LOC_RE.search(c).group(1)) if LOC_RE.search(c) else "",
                    "country": "GB",
                    "source": "reedsy_gb" + g.rstrip("/").split("/")[-1],
                })
            print(f"  {g}page{page}: {len(cards)} cards, {new} new (total {len(out)})")
            if len(cards) < 10:
                break
            page += 1
            time.sleep(0.3)
    DATA.mkdir(parents=True, exist_ok=True)
    p = DATA / "dir_reedsy.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n")
    print(f"wrote {len(out)} publishers -> {p}")



# ---------------------------------------------------------------- list pages
# Curated listicles / directories. Anchor text is the org name, the href its
# site — extracted mechanically so nothing is transcribed by hand.
LIST_PAGES = [
    ("indiepub_uk", "https://jillsbookcafe.blog/independent-publishers/"),
    ("subs_uk_all", "https://www.jonesnovelediting.com/blog/uk-publishers-accepting-manuscripts"),
    ("subs_uk_crime", "https://www.jonesnovelediting.com/blog/uk-crime-mystery-publishers-accepting-manuscripts"),
    ("subs_romance", "https://www.jonesnovelediting.com/blog/romance-publishers-accepting-manuscripts"),
    ("digitalfirst", "https://jerichowriters.com/digital-first-publishers/"),
    ("publicists_uk", "https://writingtipsoasis.com/book-publicists-in-the-uk/"),
    ("bookmarketing_uk", "https://www.bookeditingservices.co.uk/book-marketing-companies-uk.html"),
    ("blogtours", "https://musingofsouls.wordpress.com/2021/08/06/the-list-of-book-blog-tour/"),
    ("selfpub_uk", "https://www.barnesghostwriting.com/blog/top-10-self-publishing-companies-in-uk/"),
    ("marketing_uk2", "https://ghostwritingsolution.com/blog/top-17-book-marketing-services-in-the-uk/"),
    ("ghostwriters_uk", "https://www.bookwritinginc.com/blog/top-ghostwriting-services-in-the-united-kingdom/"),
    ("promo_uk", "https://www.barnesghostwriting.com/blog/top-10-best-book-marketing-and-promotion-services-in-uk/"),
]

NOISE_HOST = re.compile(
    r"(facebook|twitter|x\.com|instagram|linkedin|pinterest|youtube|tiktok|reddit|"
    r"goodreads|amazon\.|amzn\.|wikipedia|wordpress\.com/tag|gravatar|wp\.com|"
    r"google\.|gstatic|doubleclick|bit\.ly|tinyurl|paypal|patreon|substack\.com/@|"
    r"trustpilot|glassdoor|crunchbase|indeed|apple\.com|spotify|podbean|"
    r"bookshop\.org|waterstones|blackwells|hive\.co\.uk|kobo|barnesandnoble|"
    r"jillsbookcafe|jonesnovelediting|jerichowriters|writingtipsoasis|"
    r"bookeditingservices|musingofsouls|barnesghostwriting|ghostwritingsolution|"
    r"bookwritinginc|reedsy|mailchimp|eventbrite|zoom\.us|calendly)", re.I)
ANCHOR_RE = re.compile(r'<a\b[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)


def scrape_lists(only=None):
    DATA.mkdir(parents=True, exist_ok=True)
    for tag, url in LIST_PAGES:
        if only and tag != only:
            continue
        h = fetch(url)
        if not h:
            print(f"  {tag}: FETCH FAILED {url}")
            continue
        rows, seen = [], set()
        for href, text in ANCHOR_RE.findall(h):
            dom = norm_domain(href)
            name = clean(text)
            if not dom or dom in seen or NOISE_HOST.search(dom):
                continue
            if not name or len(name) > 70 or name.lower().startswith(("http", "www.", "read more", "click")):
                name = ""
            seen.add(dom)
            rows.append({"name": name, "domain": dom, "what": "", "country": "GB",
                         "source": tag})
        p = DATA / f"list_{tag}.jsonl"
        p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
        print(f"  {tag}: {len(rows)} orgs -> {p.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="reedsy", choices=["reedsy", "lists"])
    ap.add_argument("--only")
    args = ap.parse_args()
    if args.source == "reedsy":
        scrape_reedsy()
    elif args.source == "lists":
        scrape_lists(args.only)


if __name__ == "__main__":
    main()
