#!/usr/bin/env python3
"""
Volume engine for the Amazon-course / coaching vertical: YouTube Data API sweep.

Amazon-FBA course sellers, coaches and academies almost always run a YouTube
channel, and a large share publish a business email right in the channel
description ("business inquiries: ...", "Kontakt: ...", "contacto: ...").
This script searches the API across many keyword x language x region combos,
resolves every unique channel, and extracts:
  - emails found in the channel description
  - external website domains (description + branding links) -> fed to
    outreach/scripts/2b_email_harvest.py for the channels that hide their email

Quota: search.list = 100 units, channels.list = 1 unit per 50 ids.
Free daily quota is 10,000 units, so --budget caps the searches (default 90).
Resumable: seen channels and spent queries are cached in data/.

Usage:
    python3 outreach/courses/yt_harvest.py --budget 90
    python3 outreach/courses/yt_harvest.py --budget 90 --lang en,de,es
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(parents=True, exist_ok=True)
CHANNELS = DATA / "yt_channels.jsonl"
QUERY_LOG = DATA / "_yt_queries_done.json"

API = "https://www.googleapis.com/youtube/v3/"

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+\s*@\s*[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
OBFUS_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]+)\s*(?:\[at\]|\(at\)|\{at\}|\sat\s)\s*([a-zA-Z0-9.\-]+)"
    r"\s*(?:\[dot\]|\(dot\)|\{dot\}|\sdot\s)\s*([a-zA-Z]{2,})", re.I)
URL_RE = re.compile(r"https?://[^\s<>\"'\)]+", re.I)

# domains that are never a lead's own site
SOCIAL = re.compile(
    r"(youtube\.com|youtu\.be|instagram\.com|facebook\.com|fb\.me|tiktok\.com|"
    r"twitter\.com|x\.com|linkedin\.com|t\.me|telegram|whatsapp|wa\.me|"
    r"discord\.(gg|com)|patreon\.com|amazon\.[a-z.]+|amzn\.to|linktr\.ee|"
    r"beacons\.ai|bit\.ly|tinyurl|cutt\.ly|shorturl|rb\.gy|geni\.us|"
    r"spotify\.com|apple\.com|paypal\.|venmo\.|cash\.app|gumroad\.com|"
    r"calendly\.com|zoom\.us|skool\.com|udemy\.com|teachable\.com|"
    r"kajabi\.com|thinkific\.com|podia\.com|systeme\.io|clickfunnels|"
    r"google\.com|forms\.gle|docs\.google|drive\.google|notion\.so|"
    r"helium10\.com|junglescout\.com|keepa\.com|sellerboard\.com)", re.I)

# keyword sets per language: (query, regionCode, relevanceLanguage)
QUERIES = {
    "en": ([
        "amazon fba course", "amazon fba coaching", "amazon fba mentor",
        "amazon fba academy", "amazon seller training", "amazon fba masterclass",
        "learn amazon fba", "amazon wholesale course", "amazon private label course",
        "amazon ppc course", "amazon online arbitrage course", "amazon retail arbitrage coaching",
        "kdp publishing course", "amazon fba for beginners full course",
        "amazon fba bootcamp", "amazon seller coach", "amazon fba consultant",
        "amazon fba mentorship program", "amazon business coaching",
        "amazon fba step by step tutorial",
    ], ["US", "GB", "CA", "AU", "IN", "PK", "AE"]),
    "de": ([
        "amazon fba kurs", "amazon fba coaching", "amazon fba mentoring",
        "amazon fba lernen", "amazon seller schulung", "amazon fba akademie",
        "amazon private label kurs", "kdp kurs deutsch",
    ], ["DE", "AT", "CH"]),
    "es": ([
        "curso amazon fba", "mentoria amazon fba", "formacion amazon fba",
        "aprender amazon fba", "curso vender en amazon", "academia amazon fba",
        "asesoria amazon fba",
    ], ["ES", "MX", "AR", "CO", "US"]),
    "pt": ([
        "curso amazon fba", "curso vender na amazon", "mentoria amazon fba",
        "treinamento amazon fba", "amazon fba brasil curso",
    ], ["BR", "PT"]),
    "fr": ([
        "formation amazon fba", "coaching amazon fba", "apprendre amazon fba",
        "vendre sur amazon formation",
    ], ["FR", "CA", "BE"]),
    "it": ([
        "corso amazon fba", "formazione amazon fba", "vendere su amazon corso",
    ], ["IT"]),
    "ru": ([
        "курс amazon fba", "обучение амазон fba", "наставник амазон",
        "как продавать на амазон обучение",
    ], ["RU", "KZ", "UA"]),
    "ar": ([
        "كورس امازون fba", "تعليم البيع على امازون", "دورة امازون fba",
    ], ["EG", "SA", "AE"]),
    "hi": ([
        "amazon fba course hindi", "amazon selling training hindi",
    ], ["IN"]),
    "tr": ([
        "amazon fba egitimi", "amazon fba kursu", "amazonda satis egitimi",
    ], ["TR"]),
    "ja": ([
        "amazon 物販 講座", "amazon せどり 講座", "amazon 物販 コンサル",
    ], ["JP"]),
    "zh": ([
        "亚马逊运营培训", "亚马逊跨境电商课程",
    ], ["TW", "HK"]),
    "pl": (["kurs amazon fba", "sprzedaz na amazon szkolenie"], ["PL"]),
    "nl": (["amazon fba cursus", "verkopen op amazon cursus"], ["NL", "BE"]),
}


def api_key():
    env = (ROOT / "data_sources" / "config" / ".env").read_text()
    m = re.search(r"^YOUTUBE_API_KEY=(.+)$", env, re.M)
    if not m or not m.group(1).strip():
        sys.exit("YOUTUBE_API_KEY missing from data_sources/config/.env")
    return m.group(1).strip()


KEY = None


def call(endpoint, **params):
    params["key"] = KEY
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code == 403 and "quota" in body.lower():
                raise SystemExit("YouTube quota exhausted — rerun tomorrow "
                                 "(progress is cached)")
            if e.code in (429, 500, 503) and attempt < 2:
                time.sleep(2 + attempt * 3)
                continue
            print(f"  ! HTTP {e.code} {endpoint} {body[:120]}", file=sys.stderr)
            return {}
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            print(f"  ! {type(e).__name__} {endpoint}", file=sys.stderr)
            return {}
    return {}


def emails_from(text):
    out = set()
    for e in EMAIL_RE.findall(text or ""):
        out.add(re.sub(r"\s+", "", e).strip(".,;:").lower())
    for a, b, c in OBFUS_RE.findall(text or ""):
        out.add(f"{a}@{b}.{c}".lower())
    return out


def sites_from(text, links):
    out = set()
    for u in list(URL_RE.findall(text or "")) + list(links or []):
        try:
            host = urllib.parse.urlparse(u if "//" in u else "http://" + u).netloc.lower()
        except ValueError:
            continue
        host = host.split(":")[0].removeprefix("www.")
        if not host or "." not in host or SOCIAL.search(host):
            continue
        out.add(host)
    return out


def main():
    global KEY
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=90,
                    help="max search.list calls (100 quota units each)")
    ap.add_argument("--lang", default="", help="comma list, default = all")
    ap.add_argument("--pages", type=int, default=2, help="result pages per query")
    args = ap.parse_args()
    KEY = api_key()

    langs = [l.strip() for l in args.lang.split(",") if l.strip()] or list(QUERIES)
    done_log = json.loads(QUERY_LOG.read_text()) if QUERY_LOG.exists() else {}
    known = {}
    if CHANNELS.exists():
        for line in CHANNELS.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                known[rec["channel_id"]] = rec
    print(f"{len(known)} channels already cached, {len(done_log)} queries spent")

    # build the work list: (lang, query, region) round-robin over languages so a
    # small budget still spreads across markets
    per_lang = {}
    for lang in langs:
        qs, regions = QUERIES[lang]
        per_lang[lang] = [(lang, q, regions[i % len(regions)])
                          for i, q in enumerate(qs)]
    work = []
    for i in range(max(len(v) for v in per_lang.values())):
        for lang in langs:
            if i < len(per_lang[lang]):
                work.append(per_lang[lang][i])

    spent, new_ids = 0, []
    for lang, q, region in work:
        tag = f"{lang}|{q}|{region}"
        if tag in done_log:
            continue
        if spent >= args.budget:
            break
        token, found = None, 0
        for _ in range(args.pages):
            if spent >= args.budget:
                break
            p = dict(part="snippet", type="channel", maxResults=50, q=q,
                     regionCode=region, relevanceLanguage=lang, order="relevance")
            if token:
                p["pageToken"] = token
            res = call("search", **p)
            spent += 1
            for item in res.get("items", []):
                cid = (item.get("id") or {}).get("channelId")
                if cid and cid not in known:
                    known[cid] = None
                    new_ids.append(cid)
                    found += 1
            token = res.get("nextPageToken")
            if not token:
                break
        done_log[tag] = found
        QUERY_LOG.write_text(json.dumps(done_log, ensure_ascii=False))
        print(f"  [{spent}/{args.budget}] {tag} -> +{found} new channels")

    print(f"resolving {len(new_ids)} new channels ...")
    out_lines = []
    for i in range(0, len(new_ids), 50):
        batch = new_ids[i:i + 50]
        res = call("channels", part="snippet,statistics,brandingSettings",
                   id=",".join(batch), maxResults=50)
        for ch in res.get("items", []):
            sn = ch.get("snippet", {})
            st = ch.get("statistics", {})
            bs = (ch.get("brandingSettings") or {}).get("channel", {})
            desc = " ".join(filter(None, [sn.get("description", ""),
                                          bs.get("description", ""),
                                          bs.get("keywords", "")]))
            rec = {
                "channel_id": ch["id"],
                "title": sn.get("title", ""),
                "custom_url": sn.get("customUrl", ""),
                "country": sn.get("country", ""),
                "published_at": sn.get("publishedAt", ""),
                "subs": int(st.get("subscriberCount", 0) or 0),
                "videos": int(st.get("videoCount", 0) or 0),
                "views": int(st.get("viewCount", 0) or 0),
                "emails": sorted(emails_from(desc)),
                "sites": sorted(sites_from(desc, [])),
                "description": desc[:1500],
            }
            known[ch["id"]] = rec
            out_lines.append(json.dumps(rec, ensure_ascii=False))
        if out_lines:
            with CHANNELS.open("a") as f:
                f.write("\n".join(out_lines) + "\n")
            out_lines = []
        print(f"  resolved {min(i + 50, len(new_ids))}/{len(new_ids)}")

    have = [v for v in known.values() if v]
    with_mail = [c for c in have if c["emails"]]
    with_site = [c for c in have if c["sites"]]
    print(f"\ntotal channels: {len(have)}")
    print(f"  with email in description: {len(with_mail)}")
    print(f"  with own website (no email yet): {len([c for c in with_site if not c['emails']])}")
    print(f"  unique emails: {len({e for c in with_mail for e in c['emails']})}")
    print(f"  unique sites: {len({s for c in have for s in c['sites']})}")
    print(f"wrote {CHANNELS}")


if __name__ == "__main__":
    main()
