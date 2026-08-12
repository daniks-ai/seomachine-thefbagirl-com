#!/usr/bin/env python3
"""
Second source for the Amazon-course vertical: podcast owner emails.

Amazon-FBA coaches, course sellers and educators almost all run a podcast, and
podcast RSS is legally required to be public — <itunes:owner><itunes:email> is
present in the large majority of feeds. The iTunes Search API is free and needs
no key, so this is the highest email-yield source we have.

Pipeline: iTunes search (many terms x storefronts) -> feedUrl -> fetch RSS ->
owner email + site link + author name.

Output: data/podcasts.jsonl  {title, author, email, site, feed, country, term}

Usage:
    python3 outreach/courses/podcast_harvest.py
    python3 outreach/courses/podcast_harvest.py --limit-terms 10
"""
import argparse
import concurrent.futures as cf
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(parents=True, exist_ok=True)
OUT = DATA / "podcasts.jsonl"
SEARCH_CACHE = DATA / "_podcast_search.json"
FEED_CACHE = DATA / "_podcast_feeds.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

TERMS = [
    # EN
    ("amazon fba", "US"), ("amazon seller", "US"), ("selling on amazon", "US"),
    ("amazon fba coaching", "US"), ("amazon private label", "US"),
    ("amazon ppc", "US"), ("amazon wholesale", "US"),
    ("online arbitrage", "US"), ("retail arbitrage", "US"),
    ("amazon business", "US"), ("ecommerce coaching amazon", "US"),
    ("kdp publishing", "US"), ("self publishing amazon", "US"),
    ("amazon fba", "GB"), ("amazon seller", "GB"), ("amazon fba", "CA"),
    ("amazon seller", "AU"), ("amazon fba", "IN"), ("amazon seller", "PK"),
    ("amazon fba", "PH"), ("amazon seller", "AE"), ("amazon fba", "NG"),
    # DE
    ("amazon fba", "DE"), ("amazon fba kurs", "DE"), ("amazon seller", "DE"),
    ("amazon verkaufen", "DE"), ("amazon fba", "AT"), ("amazon fba", "CH"),
    # ES / LATAM
    ("amazon fba", "ES"), ("vender en amazon", "ES"), ("amazon fba", "MX"),
    ("vender en amazon", "MX"), ("amazon fba", "AR"), ("amazon fba", "CO"),
    ("amazon fba", "CL"),
    # PT
    ("amazon fba", "BR"), ("vender na amazon", "BR"), ("amazon fba", "PT"),
    # FR / IT / NL / other EU
    ("amazon fba", "FR"), ("vendre sur amazon", "FR"), ("amazon fba", "IT"),
    ("vendere su amazon", "IT"), ("amazon fba", "NL"), ("amazon fba", "PL"),
    ("amazon fba", "TR"), ("amazon fba", "SE"), ("amazon fba", "RO"),
    ("amazon fba", "CZ"), ("amazon fba", "HU"), ("amazon fba", "GR"),
    # RU / JP / KR / CN / SEA
    ("amazon fba", "RU"), ("амазон", "RU"), ("amazon 物販", "JP"),
    ("amazon せどり", "JP"), ("아마존 셀러", "KR"), ("亚马逊", "TW"),
    ("amazon fba", "ID"), ("amazon fba", "MY"), ("amazon fba", "TH"),
    ("amazon fba", "VN"), ("amazon fba", "IL"), ("amazon fba", "SA"),
    ("amazon fba", "EG"),
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
OWNER_RE = re.compile(r"<itunes:owner>(.*?)</itunes:owner>", re.S | re.I)
EMAIL_TAG_RE = re.compile(r"<itunes:email>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</itunes:email>", re.S | re.I)
NAME_TAG_RE = re.compile(r"<itunes:name>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</itunes:name>", re.S | re.I)
MGR_RE = re.compile(r"<(?:managingEditor|webMaster)>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</(?:managingEditor|webMaster)>", re.S | re.I)
LINK_RE = re.compile(r"<link>\s*(?:<!\[CDATA\[)?(https?://[^<\]\s]+)", re.I)
TITLE_RE = re.compile(r"<title>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</title>", re.S | re.I)
JUNK_MAIL = re.compile(
    r"(no-?reply|noreply|podcast@anchor|@anchor\.fm|@spotify|@buzzsprout|"
    r"@libsyn|@podbean|@captivate\.fm|@transistor\.fm|@simplecast|@megaphone|"
    r"@spreaker|@soundon|@ausha|@acast|@redcircle|@podcastone|example\.com|"
    r"@blubrry|@fireside\.fm|@rss\.com|@substack\.com|@podigee)", re.I)


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(1_500_000).decode("utf-8", "replace")


def itunes(term, country, limit=200):
    url = ("https://itunes.apple.com/search?" + urllib.parse.urlencode({
        "media": "podcast", "term": term, "country": country, "limit": limit}))
    for attempt in range(3):
        try:
            return json.loads(fetch(url, 25)).get("results", [])
        except Exception:
            time.sleep(2 + attempt * 3)
    return []


def parse_feed(feed_url):
    rec = {"feed": feed_url, "emails": [], "site": "", "owner": "", "title": ""}
    try:
        xml = fetch(feed_url, 25)
    except Exception as e:
        rec["error"] = f"{type(e).__name__}"
        return rec
    head = xml[:120_000]
    mails = set()
    owner_block = OWNER_RE.search(head)
    if owner_block:
        for m in EMAIL_TAG_RE.findall(owner_block.group(1)):
            mails.add(m.strip())
        nm = NAME_TAG_RE.search(owner_block.group(1))
        if nm:
            rec["owner"] = re.sub(r"<[^>]+>", "", nm.group(1)).strip()[:80]
    for m in MGR_RE.findall(head):
        for e in EMAIL_RE.findall(m):
            mails.add(e)
    if not mails:
        for e in EMAIL_RE.findall(head):
            mails.add(e)
    rec["emails"] = sorted({e.lower() for e in mails
                            if EMAIL_RE.fullmatch(e) and not JUNK_MAIL.search(e)})
    lk = LINK_RE.search(head)
    if lk:
        try:
            rec["site"] = urllib.parse.urlparse(lk.group(1)).netloc.lower().removeprefix("www.")
        except ValueError:
            pass
    tt = TITLE_RE.search(head)
    if tt:
        rec["title"] = re.sub(r"<[^>]+>", "", tt.group(1)).strip()[:120]
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-terms", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    scache = json.loads(SEARCH_CACHE.read_text()) if SEARCH_CACHE.exists() else {}
    terms = TERMS[: args.limit_terms] if args.limit_terms else TERMS
    for term, country in terms:
        key = f"{country}|{term}"
        if key in scache:
            continue
        res = itunes(term, country)
        scache[key] = [{"feed": r.get("feedUrl"), "artist": r.get("artistName", ""),
                        "name": r.get("collectionName", ""),
                        "country": r.get("country", country),
                        "genres": r.get("genres", [])[:3]}
                       for r in res if r.get("feedUrl")]
        SEARCH_CACHE.write_text(json.dumps(scache, ensure_ascii=False))
        print(f"  itunes {key}: {len(scache[key])} feeds")
        time.sleep(1.0)

    # unique feeds
    feeds = {}
    for key, rows in scache.items():
        for r in rows:
            feeds.setdefault(r["feed"], {**r, "term": key})
    print(f"{len(feeds)} unique feeds from {len(scache)} searches")

    fcache = json.loads(FEED_CACHE.read_text()) if FEED_CACHE.exists() else {}
    todo = [f for f in feeds if f not in fcache]
    print(f"fetching {len(todo)} feeds ...")
    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(parse_feed, f): f for f in todo}
        for fut in cf.as_completed(futs):
            f = futs[fut]
            try:
                fcache[f] = fut.result()
            except Exception as e:
                fcache[f] = {"feed": f, "emails": [], "error": str(e)[:50]}
            done += 1
            if done % 100 == 0:
                FEED_CACHE.write_text(json.dumps(fcache, ensure_ascii=False))
                print(f"  {done}/{len(todo)} | "
                      f"{sum(1 for v in fcache.values() if v.get('emails'))} with email")
    FEED_CACHE.write_text(json.dumps(fcache, ensure_ascii=False))

    with OUT.open("w", encoding="utf-8") as fh:
        n = 0
        for feed, meta in feeds.items():
            rec = fcache.get(feed) or {}
            if not rec.get("emails"):
                continue
            fh.write(json.dumps({
                "title": rec.get("title") or meta.get("name", ""),
                "author": rec.get("owner") or meta.get("artist", ""),
                "emails": rec["emails"], "site": rec.get("site", ""),
                "feed": feed, "country": meta.get("country", ""),
                "term": meta.get("term", ""), "genres": meta.get("genres", []),
            }, ensure_ascii=False) + "\n")
            n += 1
    emails = {e for v in fcache.values() for e in v.get("emails", [])}
    print(f"wrote {n} podcasts with email to {OUT} | {len(emails)} unique emails")


if __name__ == "__main__":
    main()
