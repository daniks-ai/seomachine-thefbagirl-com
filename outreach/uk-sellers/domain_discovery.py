#!/usr/bin/env python3
"""Discover websites for UK Amazon sellers.

Input: uk_sellers_uk.jsonl  (records {s, n, biz, country, addr} with country==GB)
Output: uk_domains.jsonl    ({s, n, biz, domain, method})
        uk_domains.txt      (unique domains, feeds 2b_email_harvest.py)

Strategy per seller:
  1. Guess domains from cleaned storefront/brand name: brand.co.uk, brand.uk,
     brand.com — HEAD/GET check (any 2xx/3xx with HTML = candidate).
  2. DuckDuckGo HTML search «"<brand>" UK» — first organic domain not in
     the marketplace/social/registry blocklist.
Stdlib only. Resumable via _domains_progress.json.
"""
import json, random, re, socket, ssl, sys, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
IN = HERE / "uk_sellers_uk.jsonl"
OUT = HERE / "uk_domains.jsonl"
OUT_TXT = HERE / "uk_domains.txt"
PROG = HERE / "_domains_progress.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

BLOCK = re.compile(
    r"(amazon\.|ebay|etsy|facebook|instagram|tiktok|youtube|linkedin|walmart|"
    r"wikipedia|twitter|x\.com|pinterest|shopee|aliexpress|alibaba|temu|shein|"
    r"google\.|apple\.|duckduckgo|yelp|tripadvisor|glassdoor|indeed|linktr\.ee|"
    r"wa\.me|whatsapp|t\.me|bit\.ly|goo\.gl|reddit|quora|medium\.com|blogspot|"
    r"wordpress\.com|wixsite|weebly|jimdo|kompass|cybo|dnb\.com|infobel|"
    r"opencorporates|companieshouse|company-information|gov\.uk|endole|"
    r"companycheck|checkcompanyinfo|bizdb|globaldatabase|yell\.com|"
    r"thomsonlocal|trustpilot|scoot\.co\.uk|192\.com|duedil|companiesintheuk|"
    r"companydirectorcheck|northdata|creditsafe|experian|onmarket|"
    r"ukbusinessforums|argos|tesco|sainsbury|asda|currys|johnlewis|"
    r"boots\.com|screwfix|wickes|diy\.com|wilko|therange|dunelm|"
    r"notonthehighstreet|onbuy|fruugo|manomano|wayfair)", re.I)

LEGAL_RE = re.compile(
    r"\b(ltd\.?|limited|llp|plc|inc\.?|llc|corp\.?|co\.?|company|group|"
    r"holdings?|trading|enterprises?|ventures?|solutions|retail|supplies|"
    r"store|shop|official|uk|gb|london)\b", re.I)


def norm_token(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "", s).lower()
    return s


def clean_brand(rec):
    # prefer storefront name (n) over legal name (biz) for domain guessing
    cands = []
    for raw in [rec.get("n") or "", rec.get("biz") or ""]:
        if not raw:
            continue
        base = LEGAL_RE.sub(" ", raw)
        base = re.sub(r"\s+", " ", base).strip()
        if base:
            cands.append(base)
        tok = norm_token(base)
        if tok and len(tok) >= 4:
            cands.append(tok)
    return cands


def fetch(url, timeout=12, method="GET"):
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": UA, "Accept": "text/html,*/*",
        "Accept-Language": "en-GB,en;q=0.9"})
    return urllib.request.urlopen(req, timeout=timeout, context=CTX)


def try_domain(dom):
    """Return True if domain serves something website-ish."""
    try:
        socket.setdefaulttimeout(6)
        socket.gethostbyname(dom)
    except OSError:
        return False
    for scheme in ("https://", "http://"):
        try:
            r = fetch(scheme + dom, timeout=10)
            ct = r.headers.get("Content-Type", "")
            if r.status < 400 and "html" in ct:
                # parked-domain heuristic
                body = r.read(60_000).decode("utf-8", "ignore").lower()
                if re.search(r"(domain (is )?for sale|sedoparking|parkingcrew|"
                             r"godaddy\.com/domainsearch|this domain)", body):
                    return False
                return True
        except Exception:
            continue
    return False


def ddg_search(q):
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q)
    try:
        r = fetch(url, timeout=15)
        html = r.read(400_000).decode("utf-8", "ignore")
    except Exception as e:
        return None, f"ddg-err:{e}"
    if "anomaly" in html.lower() or r.status != 200:
        return None, "ddg-blocked"
    hrefs = re.findall(r'class="result__a"[^>]*href="([^"]+)"', html)
    if not hrefs:
        hrefs = re.findall(r'href="(https?://[^"]+)"[^>]*class="result__url"', html)
    for h in hrefs[:8]:
        m = re.search(r"uddg=([^&]+)", h)
        target = urllib.parse.unquote(m.group(1)) if m else h
        dom = urllib.parse.urlparse(target).netloc.lower().replace("www.", "")
        if dom and not BLOCK.search(dom) and "." in dom:
            return dom, "ddg"
    return None, "ddg-nores"


def main():
    prog = {}
    if PROG.exists():
        prog = json.loads(PROG.read_text())
    recs = [json.loads(l) for l in IN.read_text().splitlines() if l.strip()]
    out_f = OUT.open("a")
    n_found = 0
    for i, rec in enumerate(recs):
        sid = rec["s"]
        if sid in prog:
            continue
        domain, method = None, None
        brands = clean_brand(rec)
        # 1) direct guesses off the first clean token
        toks = [norm_token(b) for b in brands]
        toks = [t for t in dict.fromkeys(toks) if 4 <= len(t) <= 30]
        for t in toks[:2]:
            for tld in (".co.uk", ".uk", ".com"):
                dom = t + tld
                if try_domain(dom):
                    domain, method = dom, "guess"
                    break
            if domain:
                break
        # 2) DDG
        if not domain and brands:
            q = f'"{brands[0]}" UK'
            domain, method = ddg_search(q)
            time.sleep(2.5 + random.random() * 2)
            if method == "ddg-blocked":
                print("DDG blocked — sleeping 120s", flush=True)
                time.sleep(120)
                domain, method = ddg_search(q)
                time.sleep(2.5)
        prog[sid] = domain or ""
        if domain:
            n_found += 1
            out_f.write(json.dumps({"s": sid, "n": rec.get("n"),
                                    "biz": rec.get("biz"), "domain": domain,
                                    "method": method}, ensure_ascii=False) + "\n")
            out_f.flush()
        if i % 10 == 0:
            PROG.write_text(json.dumps(prog))
            print(f"[{i}/{len(recs)}] found={n_found}", flush=True)
    PROG.write_text(json.dumps(prog))
    doms = sorted({json.loads(l)["domain"] for l in OUT.read_text().splitlines() if l.strip()})
    OUT_TXT.write_text("\n".join(doms) + "\n")
    print(f"DONE sellers={len(recs)} domains={len(doms)}", flush=True)


if __name__ == "__main__":
    main()
