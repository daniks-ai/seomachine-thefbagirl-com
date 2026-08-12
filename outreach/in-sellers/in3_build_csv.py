#!/usr/bin/env python3
"""
India Amazon-seller lead build, stage 3: clean, validate, tier, dedupe.

Turns the raw crawl into an import-ready lead list.

Tiers (highest first) — an Indian D2C brand usually does sell on Amazon but
deliberately does not link to it from its own store, so an explicit Amazon
signal is treated as a ranking boost rather than a hard gate. Amazon.in blocks
bulk lookups and DDG rate-limits, so per-lead verification is not available:
  A  explicit Amazon product/store link or "buy on Amazon" copy
  B  bare amazon.in / amazon.com mention
  C  Indian online store, no Amazon evidence on site

Cleaning: role/junk locals dropped, at most 2 addresses per domain, gmail-style
free addresses kept only when the site publishes no branded address, every email
domain MX-checked, and the whole list deduped against every lead file already in
outreach/ plus the campaign-added logs.

Output: data/instantly_IN_SELLERS.csv   email,first_name,company_name,website,tier
        data/instantly_IN_bulk.txt      "Name" <email> lines for manual paste

Usage:
    python3 outreach/in-sellers/in3_build_csv.py --target 4000
"""
import argparse
import asyncio
import csv
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from in1_dns import build_query  # noqa: E402  (raw UDP DNS query builder)
import random
import struct


class MXProto(asyncio.DatagramProtocol):
    """Hands back the raw DNS response so the answer count can be read.

    in1_dns.Resolver decodes A records and returns None for anything else, so
    an MX query would resolve to None both for "has MX" and for "no such
    domain" — useless as validation. Here the caller checks RCODE + ANCOUNT.
    """

    def __init__(self):
        self.pending = {}

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if len(data) < 8:
            return
        fut = self.pending.pop(struct.unpack(">H", data[:2])[0], None)
        if fut and not fut.done():
            fut.set_result(data)


def has_answer(data):
    rcode = data[3] & 0x0F
    ancount = struct.unpack(">H", data[6:8])[0]
    return rcode == 0 and ancount > 0

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUTREACH = HERE.parent
OUT_CSV = DATA / "instantly_IN_SELLERS.csv"
OUT_BULK = DATA / "instantly_IN_bulk.txt"
MXCACHE = DATA / "_in_mx.tsv"

FREE_MAIL = re.compile(
    r"@(gmail|googlemail|yahoo|ymail|rediffmail|hotmail|outlook|live|icloud|"
    r"protonmail|proton\.me|mailbox\.org|zoho|aol)\.?", re.I)

# The "@"-anchored scan in stage 2 truncates a local part whenever the site
# splits it with markup or an HTML entity ("c<span>are@", "&#105;ndia@"), which
# produced live-looking addresses like are@, ndia@, ternational@, nline@. If the
# local is a strict suffix of a role word, it is one of those, not an address.
ROLE_WORDS = ("care", "customercare", "consumercare", "support", "info",
              "information", "contact", "contactus", "sales", "online",
              "orders", "order", "international", "india", "hello", "help",
              "helpdesk", "enquiry", "enquiries", "inquiry", "service",
              "services", "admin", "office", "shop", "store", "team",
              "connect", "reach", "wecare", "export", "business", "official",
              "email", "mail", "ecommerce", "subscription", "welcome",
              "official1", "customerservice", "customersupport")

# lookalike mail providers — a typo on the site, dead on delivery
TYPO_DOMAIN = re.compile(
    r"^(gmai|gmil|gamil|gmial|gmaill|amail|gnail|hotmial|hotmai|yahho|yaho|"
    r"outlok|rediff|redifmail)\.", re.I)

# default hosting subdomains and staging hosts — never a monitored inbox
HOST_JUNK = re.compile(
    r"\.(hostingersite|myshopify|vercel\.app|netlify\.app|wixsite|"
    r"weeblysite|godaddysites|square\.site|onrender|herokuapp|"
    r"pages\.dev|workers\.dev|web\.app|firebaseapp)\.?", re.I)

# large FMCG/electronics groups: these care@ addresses are consumer-support
# queues, not sellers who would ever buy a $49/mo autopilot
ENTERPRISE = re.compile(
    r"(adityabirla|tata|trent-tata|unilever|hul\b|itcportal|dabur|marico|"
    r"godrej|patanjali|zyduswellness|emami|wipro|reliance|nestle|pepsico|"
    r"cocacola|britannia|parle|amul|haldiram|bikaji|balajiwafers|theobroma|"
    r"lakmeindia|ponds\.|dove-india|victorinox|samsung|lg\.com|philips|"
    r"bosch|whirlpool|havells|bajajelectronics|usha\.|prestige|wonderchef|"
    r"milton|borosil|cello|pigeon|decathlon|levi|uspoloassn|puma|adidas|"
    r"nike|titan|fastrack|mamaearth|nykaa|wow|shipway|adityabirla|"
    r"itc\.in|acer\.com|samsonite|imoo\.com|dreame\.tech|sealy\.in|"
    r"vardhman|monin\.com|bluestarindia|colorbarcosmetics|delhipress)", re.I)
ROLE_DROP = re.compile(
    r"^(careers?|jobs?|hr|recruit\w*|press|media|legal|privacy|dpo|grievance|"
    r"compliance|abuse|security|webmaster|admin|noc|billing|invoice|accounts?|"
    r"payments?|finance|returns?|refunds?|warranty|complaints?|nodal|"
    r"unsubscribe|newsletter|marketing|affiliate|wholesale|bulk|"
    r"franchise|investor|ir|vendor|supplier)@", re.I)
# obvious harvester junk seen in earlier rounds
BAD_LOCAL = re.compile(
    r"^(u003e|x3d|x2f|\d+|[a-z]|email|e-?mail|your\w*|my\w*mail|test\d*|"
    r"example|sample|username|user|domain|website|site|www)$", re.I)
BAD_DOMAIN = re.compile(
    r"(\.(png|jpg|jpeg|gif|svg|webp|css|js|json|xml|woff2?)$|"
    r"^(sentry|wix|shopify|godaddy|cloudflare|jsdelivr|gstatic|w3|schema|"
    r"example|domain|yourdomain|localhost)\.|"
    r"^(mastodon\.|mstdn|fosstodon|github\.|gitlab\.|t\.me$|discord)|"
    r"\.(local|invalid|test|example)$|^\d+\.\d+\.\d+\.\d+$)", re.I)

ODD_CHARS = re.compile(r"""[%<>()\[\]{}\\,;:!#$&*+=|~^"']""")

STOP_TITLE = re.compile(
    r"(^home$|^shop$|^welcome|404|page not found|coming soon|under construction|"
    r"^index$|^untitled)", re.I)


def clean_company(title, domain):
    """Page title -> a usable company name, or "" if it is not one."""
    t = re.split(r"\s[|\-–—:]\s|\s\|\s", title or "")[0].strip()
    t = re.sub(r"\s+", " ", t)
    if not t or len(t) < 2 or len(t) > 45 or STOP_TITLE.search(t):
        base = domain.split(".")[0].replace("-", " ")
        return base.title() if 2 < len(base) < 25 else ""
    if re.search(r"(buy|shop|online|best|price|india)\b.*\b(online|india|price)",
                 t, re.I):
        base = domain.split(".")[0].replace("-", " ")
        return base.title() if 2 < len(base) < 25 else ""
    return t


def pick_emails(rec):
    """At most two addresses per domain, branded ones preferred."""
    dom = rec["domain"]
    root = dom[4:] if dom.startswith("www.") else dom
    good = []
    for e in rec["emails"]:
        local, _, edom = e.partition("@")
        # scraped from markup as "info@www.brand.in" — the mail domain never has
        # a www label, so drop it before validating
        if edom.startswith("www."):
            edom = edom[4:]
            e = f"{local}@{edom}"
        if ".." in e or edom.endswith("-") or "-." in edom:
            continue
        # URL-encoded fragments ("%20support@", "%3cstrong%3esales@") and
        # plus-addressed crawler traps ("+claude-searchbot@") both come from
        # scraping markup rather than from a real published address
        if ODD_CHARS.search(e):
            continue
        if HOST_JUNK.search(edom) or ENTERPRISE.search(edom):
            continue
        if re.search(r"\.(ac|edu|res|gov|nic)\.in$|\.(edu|gov|ltd)$", edom, re.I):
            continue
        ll = local.lower()
        if any(w != ll and w.endswith(ll) for w in ROLE_WORDS):
            continue
        # a real local part starts with a letter or digit; "u003e" is an escaped
        # ">" that leaked out of JSON-encoded markup
        if not re.match(r"^[a-z0-9]", ll) or "u003e" in ll or "x003e" in ll:
            continue
        if TYPO_DOMAIN.match(edom.lower()):
            continue
        if ROLE_DROP.search(e) or BAD_LOCAL.match(local) or BAD_DOMAIN.search(edom):
            continue
        if len(local) < 2:
            continue
        good.append(e)
    onsite = [e for e in good if e.split("@")[1].endswith(root.split(".", 1)[-1])
              and root.split(".")[0] in e.split("@")[1]]
    branded = [e for e in good if not FREE_MAIL.search(e)]
    free = [e for e in good if FREE_MAIL.search(e)]
    ordered = ([e for e in onsite if e in branded]
               + [e for e in branded if e not in onsite] + free)
    seen, out = set(), []
    for e in ordered:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out[:2]


def existing_emails():
    """Every address already living in an outreach lead file."""
    seen = set()
    pats = ["**/*.csv", "**/*bulk*.txt", "**/*added*.txt", "**/*suppress*.txt"]
    for pat in pats:
        for f in OUTREACH.glob(pat):
            if "in-sellers" in str(f):
                continue
            try:
                txt = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in re.finditer(r"[a-zA-Z0-9._%+\-]{1,40}@[a-zA-Z0-9.\-]{2,50}"
                                 r"\.[a-zA-Z]{2,12}", txt):
                seen.add(m.group(0).lower())
    return seen


# ------------------------------------------------------------------ MX check
async def mx_check(domains, concurrency=300):
    cache = {}
    if MXCACHE.exists():
        for line in MXCACHE.read_text().splitlines():
            d, _, v = line.partition("\t")
            cache[d] = v == "1"
    todo = [d for d in domains if d not in cache]
    if not todo:
        return cache
    loop = asyncio.get_running_loop()
    protos = []
    for r in ["1.1.1.1", "8.8.8.8", "9.9.9.9", "8.8.4.4"]:
        _t, proto = await loop.create_datagram_endpoint(MXProto, remote_addr=(r, 53))
        protos.append((proto, (r, 53)))

    sem = asyncio.Semaphore(concurrency)
    results = {}

    async def one(dom):
        async with sem:
            for _ in range(2):
                proto, addr = random.choice(protos)
                txid = random.randrange(65536)
                while txid in proto.pending:
                    txid = random.randrange(65536)
                fut = loop.create_future()
                proto.pending[txid] = fut
                q = build_query(txid, dom)
                q = q[:-4] + struct.pack(">HH", 15, 1)   # qtype MX
                try:
                    proto.transport.sendto(q, addr)
                    data = await asyncio.wait_for(fut, timeout=4)
                except Exception:
                    proto.pending.pop(txid, None)
                    continue
                if has_answer(data):
                    results[dom] = True
                    return
                results[dom] = False
                return
            results[dom] = False

    await asyncio.gather(*(one(d) for d in todo))
    with MXCACHE.open("a", encoding="utf-8") as f:
        for d, v in results.items():
            f.write(f"{d}\t{1 if v else 0}\n")
    cache.update(results)
    return cache


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=4000)
    ap.add_argument("--min-tier", default="C")
    # Decathlon/Levi's/Mamaearth sit in the first few thousand Indian origins;
    # they are not buying a $49/mo autopilot and their care@ queues would just
    # eat sends, so the head of the traffic list is skipped entirely.
    ap.add_argument("--skip-top", type=int, default=4000)
    args = ap.parse_args()

    recs = {}
    for f in sorted(DATA.glob("in_crawl*.jsonl")):
        for line in f.open(encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("ok") and r.get("emails"):
                recs[r["domain"]] = r
    print(f"{len(recs)} crawled domains with at least one address")

    # stage 2b: only keep domains proven to run a store engine
    store, rupee = {}, {}
    pf = DATA / "in_platform.jsonl"
    if pf.exists():
        for line in pf.open(encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            # a named store engine only: the cart+prices fallback let a
            # government labour-board portal and a tech-news site through
            if r.get("ok") and r.get("plat"):
                store[r["domain"]] = r["plat"]
                rupee[r["domain"]] = r.get("prices", 0)
    print(f"{len(store)} of them are real online stores (stage 2b)")

    # stage 2c: physical-goods retail only, plus a second read of the Amazon
    # signal (a footer "buy on Amazon" badge is what promotes a lead to tier A)
    retail, amz2c = {}, {}
    rf = DATA / "in_retail.jsonl"
    if rf.exists():
        for line in rf.open(encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if not r.get("ok"):
                continue
            amz2c[r["domain"]] = r.get("amz", 0)
            if r.get("ship", 0) >= 1 and r.get("service", 0) == 0:
                retail[r["domain"]] = True
    print(f"{len(retail)} of those sell physical goods (stage 2c)")

    # traffic rank order, used to prefer bigger brands inside a tier
    rank = {}
    for name in ("in_universe.txt", "in_universe_com.txt"):
        p = DATA / name
        if p.exists():
            for i, h in enumerate(p.read_text().splitlines()):
                rank.setdefault(h.strip(), i)

    known = existing_emails()
    print(f"{len(known)} addresses already used elsewhere in outreach/")

    rows = []
    for dom, r in recs.items():
        if not (r.get("india") and r.get("comm")) or dom not in store:
            continue
        if retail and dom not in retail:
            continue
        # a .com in the India CrUX list can still be a foreign shop; require it
        # to be quoting rupees before treating it as an Indian seller
        if not dom.endswith(".in") and rupee.get(dom, 0) < 3:
            continue
        emails = pick_emails(r)
        if not emails:
            continue
        amz = max(r["amz"], amz2c.get(dom, 0))
        tier = "A" if amz >= 2 else ("B" if amz == 1 else "C")
        company = clean_company(r.get("title", ""), dom)
        # one address per company: a second mailbox at the same shop doubles the
        # complaint risk on shared mailboxes for no extra reach
        e = emails[0]
        if e in known:
            continue
        known.add(e)
        rows.append({"email": e, "first_name": "", "company_name": company,
                     "website": f"https://{dom}", "tier": tier,
                     "_branded": 0 if not FREE_MAIL.search(e) else 1,
                     "_rank": rank.get(dom, 10 ** 7),
                     "_plat": store[dom]})
    print(f"{len(rows)} candidate addresses after cleaning + dedupe")

    doms = sorted({r["email"].split("@")[1] for r in rows})
    print(f"MX-checking {len(doms)} email domains...")
    mx = asyncio.run(mx_check(doms))
    rows = [r for r in rows if mx.get(r["email"].split("@")[1], False)]
    print(f"{len(rows)} after MX validation")

    order = {"A": 0, "B": 1, "C": 2}
    # Amazon evidence first; inside a tier prefer a branded address and the
    # better-trafficked shop (bigger catalogue, likelier to be running ads)
    before = len(rows)
    rows = [r for r in rows if r["_rank"] >= args.skip_top]
    print(f"{before - len(rows)} enterprise-scale sites skipped "
          f"(traffic rank inside top {args.skip_top})")
    rows.sort(key=lambda r: (order[r["tier"]], r["_branded"], r["_rank"]))
    cut = order[args.min_tier]
    rows = [r for r in rows if order[r["tier"]] <= cut][: args.target]

    fields = ["email", "first_name", "company_name", "website", "tier"]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with OUT_BULK.open("w", encoding="utf-8") as f:
        for r in rows:
            name = r["company_name"] or "there"
            f.write(f'"{name}" <{r["email"]}>\n')
    from collections import Counter
    print(f"\n{len(rows)} leads -> {OUT_CSV}")
    print("by tier:", Counter(r["tier"] for r in rows).most_common())


if __name__ == "__main__":
    main()
