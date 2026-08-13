#!/usr/bin/env python3
"""
Isolated email harvester for the UK round-2 domain list.

Why not 2b/2c: both share `_deep_harvest_progress.json` +
`layer1_contacts_raw.json` with every other outreach run. On 2026-08-11 a
concurrent CA session grew that cache to 682 MB and rewrote it mid-run, which
hung the merge phase and silently dropped already-harvested UK results. This
script touches NOTHING shared:

  in : data/uk_r2_targets.txt          (one apex domain per line)
  out: data/uk_r2_emails.jsonl         (append-only, one JSON object per domain)

Append-only output means a hang or a kill costs only the in-flight domains —
re-running skips whatever is already in the file. A hard per-domain budget and
a global deadline mean it cannot hang the way 2c did.

Usage:
    python3 outreach/scripts/uk2_isolated_harvest.py [--workers 20] [--deadline 900]
"""
import argparse
import concurrent.futures as cf
import json
import re
import ssl
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
TARGETS = DATA / "uk_r2_targets.txt"
OUT = DATA / "uk_r2_emails.jsonl"

UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-GB,en;q=0.9",
}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
CF_RE = re.compile(r'data-cfemail="([0-9a-f]+)"', re.I)
AT_RE = re.compile(
    r"([a-z0-9._%+\-]+)\s*(?:\[at\]|\(at\)|\{at\}|\sat\s)\s*([a-z0-9.\-]+)"
    r"\s*(?:\[dot\]|\(dot\)|\{dot\}|\sdot\s)\s*([a-z]{2,})", re.I)
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
CONTACT_HINT = re.compile(r"(contact|about|team|company|reach|touch|connect|meet)", re.I)
COMMON_PATHS = ["contact", "contact-us", "about", "about-us", "team", "get-in-touch"]

BAD_LOCAL = re.compile(
    r"^(no-?reply|noreply|donotreply|privacy|abuse|postmaster|mailer-daemon|"
    r"webmaster|hostmaster|dmarc|dkim|spam|bounce|unsubscribe|example|your|"
    r"name|email|user|test|demo|sample)$", re.I)
BAD_DOMAIN = re.compile(
    r"(sentry|wixpress|example\.com|domain\.com|yourdomain|yoursite|mysite\.com|"
    r"companymail|placeholder|email\.com|site\.com|sentry\.io|wordpress|godaddy|"
    r"\.png$|\.jpg$|\.jpeg$|\.gif$|\.webp$|\.svg$)", re.I)

print_lock = threading.Lock()
write_lock = threading.Lock()


def decode_cf(hexstr):
    try:
        b = bytes.fromhex(hexstr)
        key = b[0]
        return "".join(chr(c ^ key) for c in b[1:])
    except Exception:
        return ""


def fetch(url, timeout):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read(500_000).decode("utf-8", "ignore")


def emails_from(html):
    found = set(EMAIL_RE.findall(html))
    for h in CF_RE.findall(html):
        d = decode_cf(h)
        if "@" in d:
            found.add(d)
    for a, b, c in AT_RE.findall(html):
        found.add(f"{a}@{b}.{c}")
    out = set()
    for e in found:
        e = e.strip().lower().strip(".,;:")
        if "@" not in e:
            continue
        local, dom = e.split("@", 1)
        if BAD_LOCAL.match(local) or BAD_DOMAIN.search(dom) or BAD_DOMAIN.search(e):
            continue
        if len(local) > 40 or re.fullmatch(r"[0-9a-f]{16,}", local):
            continue
        out.add(e)
    return out


def harvest(domain, budget):
    """Return (domain, sorted emails, note). Never raises, never exceeds budget."""
    deadline = time.time() + budget
    emails, base, note = set(), None, ""

    def left(cap):
        return max(1.0, min(cap, deadline - time.time()))

    for cand in (f"https://{domain}/", f"https://www.{domain}/", f"http://{domain}/"):
        if time.time() > deadline:
            break
        try:
            html = fetch(cand, left(10))
            base = cand
            emails |= emails_from(html)
            break
        except Exception as e:
            note = str(e)[:60]
    if base is None:
        return domain, [], f"unreachable: {note}"

    # links that look like contact/about pages, plus blind common paths
    try:
        html_links = set()
        for href in HREF_RE.findall(fetch(base, left(8))):
            if CONTACT_HINT.search(href) and not href.startswith(("mailto:", "tel:", "#")):
                html_links.add(urllib.parse.urljoin(base, href))
    except Exception:
        html_links = set()
    targets = list(html_links)[:4] + [urllib.parse.urljoin(base, p) for p in COMMON_PATHS]

    seen_urls = set()
    for url in targets:
        if time.time() > deadline or len(emails) >= 6:
            break
        if url in seen_urls:
            continue
        seen_urls.add(url)
        try:
            emails |= emails_from(fetch(url, left(8)))
        except Exception:
            pass
    return domain, sorted(emails), note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--budget", type=float, default=30.0, help="seconds per domain")
    ap.add_argument("--deadline", type=float, default=900.0, help="total seconds")
    args = ap.parse_args()

    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line)["domain"])
    todo = [d for d in TARGETS.read_text().split() if d not in done]
    print(f"{len(done)} already harvested, {len(todo)} to go")

    stop_at = time.time() + args.deadline
    hits = 0
    with OUT.open("a", encoding="utf-8") as fh:
        with cf.ThreadPoolExecutor(args.workers) as ex:
            futs = {ex.submit(harvest, d, args.budget): d for d in todo}
            for i, fut in enumerate(cf.as_completed(futs), 1):
                if time.time() > stop_at:
                    print("global deadline reached; stopping (partial results kept)")
                    for f in futs:
                        f.cancel()
                    break
                try:
                    dom, emails, note = fut.result(timeout=5)
                except Exception:
                    continue
                if emails:
                    hits += 1
                with write_lock:
                    fh.write(json.dumps({"domain": dom, "emails": emails, "note": note}) + "\n")
                    fh.flush()
                if i % 25 == 0:
                    with print_lock:
                        print(f"  {i}/{len(todo)} | {hits} with email")
    print(f"done: {hits} domains yielded an email -> {OUT}")


if __name__ == "__main__":
    main()
