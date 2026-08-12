#!/usr/bin/env python3
"""
Second-pass email harvester for domains the shallow `harvest_kdp.py` missed.

What it adds over v1:
  * decodes Cloudflare email protection (`data-cfemail` / `/cdn-cgi/l/email-protection#`)
  * decodes HTML entities and `[at]` / `(at)` / ` at ` / `[dot]` obfuscation
  * probes common contact paths directly (/contact, /contact-us, /about, /team,
    /submissions, /work-with-me, …) instead of only following homepage hrefs
  * widens the link-hint regex and fetches up to 6 pages per domain
  * records whether a contact FORM was seen, so leads with no email can be
    routed to manual form/LinkedIn follow-up

Output: data/kdp_contacts_deep.json — [{domain, emails, linkedIns, hasForm, scrapedUrls}]

Usage:
    python3 outreach/kdp/harvest_deep.py --domains-file outreach/kdp/data/deep_targets.txt
"""
import argparse
import concurrent.futures as cf
import gzip
import html as htmllib
import json
import re
import ssl
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
OUT = DATA / "kdp_contacts_deep.json"
PROGRESS = DATA / "_deep_harvest_progress.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
CONTACT_HINT = re.compile(
    r"(contact|about|team|kontakt|impressum|company|reach|connect|touch|"
    r"submission|enquir|inquir|hire|work-with|workwith|support|help|staff|"
    r"who-we-are|our-story|meet)", re.I)
CF_RE = re.compile(r'data-cfemail=["\']([0-9a-fA-F]+)["\']')
CF_HREF_RE = re.compile(r'/cdn-cgi/l/email-protection#([0-9a-fA-F]+)')
FORM_RE = re.compile(r'<form[^>]*>|wpcf7|gravity_form|hbspt\.forms|typeform|jotform|'
                     r'formstack|<input[^>]+type=["\']email["\']', re.I)

JUNK_RE = re.compile(
    r"(no-?reply|noreply|postmaster|mailer-daemon|abuse|hostmaster|dns-admin|privacy@|"
    r"@(?:sentry|example|wix|squarespace|godaddy|wordpress|shopify|"
    r"cloudflare|googlemail|domain|email|yourdomain|company|sample|test)\.)", re.I)
IMG_EXT_RE = re.compile(r"\.(png|jpg|jpeg|gif|svg|webp|css|js|ico|woff|ttf|mp4|pdf)$", re.I)
HEX_LOCAL = re.compile(r"^[0-9a-f]{16,}$")

COMMON_PATHS = [
    "/contact", "/contact-us", "/contactus", "/contact-me", "/about", "/about-us",
    "/team", "/our-team", "/get-in-touch", "/connect", "/work-with-me", "/work-with-us",
    "/submissions", "/submit", "/support", "/enquiries", "/hire-us", "/pages/contact",
]
MAX_PAGES = 6

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        raw = r.read(2_000_000)
        if r.headers.get("Content-Encoding") == "gzip":
            try:
                raw = gzip.decompress(raw)
            except OSError:
                pass
        return raw.decode("utf-8", "replace"), r.geturl()


def cf_decode(hexstr):
    """Cloudflare email protection: first byte is the XOR key."""
    try:
        data = bytes.fromhex(hexstr)
        key = data[0]
        return "".join(chr(b ^ key) for b in data[1:])
    except Exception:
        return ""


def deobfuscate(text):
    """Turn `name [at] site [dot] com` style writing back into an address."""
    t = htmllib.unescape(text)
    t = re.sub(r"\s*[\[\(\{]\s*at\s*[\]\)\}]\s*", "@", t, flags=re.I)
    t = re.sub(r"\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*", ".", t, flags=re.I)
    t = re.sub(r"\s+\bat\b\s+(?=[a-z0-9.\-]+\.[a-z]{2,})", "@", t, flags=re.I)
    t = re.sub(r"\s+\bdot\b\s+", ".", t, flags=re.I)
    return t


def clean_emails(found):
    out = set()
    for e in found:
        e = e.strip().strip(".,;:\"'<>()").lower()
        e = re.sub(r"^(mailto:|%20|%40|u003e)+", "", e)
        if not EMAIL_RE.fullmatch(e):
            continue
        if IMG_EXT_RE.search(e) or JUNK_RE.search(e) or len(e) > 80:
            continue
        local, host = e.split("@")
        if HEX_LOCAL.match(local) or not local:
            continue
        out.add(e)
    return out


def harvest(domain):
    rec = {"domain": domain, "emails": [], "linkedIns": [], "hasForm": False, "scrapedUrls": []}
    base = None
    pages = []
    for scheme in ("https://", "http://"):
        try:
            html_txt, final = fetch(scheme + domain)
            base = final.rstrip("/")
            pages.append((final, html_txt))
            break
        except Exception as e:
            rec["error"] = str(e)[:60]
    if base is None:
        return rec
    rec.pop("error", None)

    root = base.split("//")[0] + "//" + base.split("//")[1].split("/")[0]
    seen = {pages[0][0]}
    candidates = []

    # 1) links discovered on the homepage
    for href in LINK_RE.findall(pages[0][1]):
        if not CONTACT_HINT.search(href):
            continue
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue
        if href.startswith("http") and domain not in href:
            continue
        url = href if href.startswith("http") else root + "/" + href.lstrip("/")
        if url in seen or IMG_EXT_RE.search(url):
            continue
        seen.add(url)
        candidates.append(url)

    # 2) common paths as a fallback for sites whose nav is JS-rendered
    for p in COMMON_PATHS:
        url = root + p
        if url not in seen:
            seen.add(url)
            candidates.append(url)

    for url in candidates[: MAX_PAGES * 3]:
        if len(pages) >= MAX_PAGES:
            break
        try:
            html_txt, final = fetch(url)
            pages.append((final, html_txt))
        except Exception:
            pass

    emails, lis = set(), set()
    for final, html_txt in pages:
        rec["scrapedUrls"].append(final)
        if FORM_RE.search(html_txt):
            rec["hasForm"] = True
        # cloudflare-protected
        for hx in CF_RE.findall(html_txt) + CF_HREF_RE.findall(html_txt):
            dec = cf_decode(hx)
            if "@" in dec:
                emails.add(dec)
        plain = deobfuscate(html_txt)
        emails |= set(EMAIL_RE.findall(plain))
        for m in re.findall(r'mailto:([^"\'?>&]+)', plain, re.I):
            emails.add(m)
        for li in re.findall(r'https?://[a-z]{0,3}\.?linkedin\.com/(?:company|in)/[^"\'\s<>]+',
                             html_txt, re.I):
            lis.add(li.rstrip("/").split("?")[0])

    rec["emails"] = sorted(clean_emails(emails))
    rec["linkedIns"] = sorted(lis)[:3]
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains-file", default=str(DATA / "deep_targets.txt"))
    ap.add_argument("--workers", type=int, default=24)
    args = ap.parse_args()

    domains = [d.strip() for d in Path(args.domains_file).read_text().splitlines() if d.strip()]
    cache = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    todo = [d for d in domains if d not in cache]
    print(f"{len(cache)} cached, deep-harvesting {len(todo)} domains with {args.workers} workers")

    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(harvest, d): d for d in todo}
        for fut in cf.as_completed(futs):
            d = futs[fut]
            try:
                cache[d] = fut.result()
            except Exception as e:  # noqa
                cache[d] = {"domain": d, "emails": [], "error": str(e)[:60]}
            done += 1
            if done % 40 == 0:
                PROGRESS.write_text(json.dumps(cache, ensure_ascii=False))
                hits = sum(1 for v in cache.values() if v.get("emails"))
                print(f"  {done}/{len(todo)} | {hits} with email")

    PROGRESS.write_text(json.dumps(cache, ensure_ascii=False))
    records = list(cache.values())
    OUT.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    hits = sum(1 for v in records if v.get("emails"))
    forms = sum(1 for v in records if not v.get("emails") and v.get("hasForm"))
    print(f"deep-harvested {len(records)} | {hits} with email | {forms} form-only | wrote {OUT}")


if __name__ == "__main__":
    main()
