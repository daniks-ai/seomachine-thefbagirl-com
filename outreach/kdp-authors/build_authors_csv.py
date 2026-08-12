#!/usr/bin/env python3
"""
Turn crawl output into Instantly-ready lead files for the KDP authors round.

Reads every data/contacts_*.json produced by crawl_authors.py, applies the QA
rules that earlier KDP rounds paid for in wasted sends, and splits the result by
which of the four live campaigns actually fits the recipient.

QA rules (each one exists because a previous round shipped the mistake):
  * role/abuse inboxes dropped (careers@, dmca@, privacy@, webmaster@, …);
  * off-domain corporate addresses dropped — they are the web designer, the
    literary agent or the PR rep, not the lead. Free-mail (gmail/outlook/…) is
    kept, because that genuinely IS how most indie authors publish contact;
  * an address seen on 3+ unrelated sites is a service provider, not an author;
  * at most 2 addresses per domain, name-matching ones first;
  * placeholder/sample addresses and image-filename false positives dropped.

Usage:
    python3 outreach/kdp-authors/build_authors_csv.py
    python3 outreach/kdp-authors/build_authors_csv.py --max-leads 3000
"""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUTDIR = DATA
SUPPRESSION = DATA / "suppression_domains.txt"

FREEMAIL = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com",
            "hotmail.co.uk", "yahoo.com", "yahoo.co.uk", "yahoo.ca",
            "yahoo.com.au", "icloud.com", "me.com", "mac.com", "aol.com",
            "protonmail.com", "proton.me", "live.com", "live.co.uk",
            "msn.com", "comcast.net", "btinternet.com", "sky.com",
            "bigpond.com", "optusnet.com.au", "shaw.ca", "rogers.com",
            "telus.net", "sympatico.ca", "verizon.net", "att.net",
            "outlook.co.uk", "ymail.com", "gmx.com", "zoho.com", "fastmail.com"}

ROLE_BAD = re.compile(
    r"^(careers?|jobs?|hr|recruit\w*|apply|resume|cv|press|media|pr|"
    r"webmaster|postmaster|hostmaster|abuse|dmca|copyright|legal|privacy|"
    r"gdpr|billing|invoices?|accounts?payable|accounting|payroll|"
    r"noreply|no-reply|donotreply|unsubscribe|bounce|mailer|newsletter|"
    r"security|it|admin|root|test|demo|example|sample|your\w*|someone|"
    r"subscri\w*|advertis\w*|sponsor\w*|donate|donation|volunteer|"
    r"email|name|firstname|user|username|domain|company|yourname|"
    r"wordpress|wp|cpanel|ssl|dns)$", re.I)

PLACEHOLDER = re.compile(
    r"(john@doe|jane@doe|example\.|yourdomain|yoursite|mysite|domain\.com|"
    r"email@|name@|test@|sample@|company\.com|website\.com|address@|"
    r"someone@|user@|first\.last|firstname)", re.I)

# a lead whose site is one of these is a service/agency, not an author
SERVICE_SIG = re.compile(
    r"(marketing|agency|agencia|consult|publicity|publicist|pr\b|promo|"
    r"design|studio|editorial|editing|editor|proofread|formatting|"
    r"ghostwrit|copywrit|translation|virtual assistant|\bva\b|audiobook|"
    r"narrat|cover art|book cover|web design|seo|advertis|ads manag)", re.I)
COACH_SIG = re.compile(
    r"(coach|mentor|academy|course|masterclass|training|podcast|blog tour|"
    r"book tour|review service|bookstagram|booktok|influencer|"
    r"newsletter swap|promo site|book deals|bargain books)", re.I)
# book bloggers, reviewers and bookstagrammers are a *partner* audience (they
# promote other people's books), never a direct ads customer
REVIEW_SIG = re.compile(
    r"(book blog|bookblog|book cafe|book club|bookclub|reviews?\b|reviewer|"
    r"bookish|bookworm|reads\b|reading|blogger|bookstagram|booktok|"
    r"book frolic|book nook|book corner|bookshelf|book chat|libr)", re.I)
# newspapers, magazines and business media rank for book queries and are noise
NEWS_SIG = re.compile(
    r"(\bnews\b|newspaper|magazine|\btimes\b|tribune|gazette|herald|"
    r"chronicle|\bdaily\b|\bpost\b|\bwire\b|bulletin|observer|"
    r"broadcast|\btv\b|radio|startup|entrepreneur\b|business innovation)", re.I)
PUBLISHER_SIG = re.compile(
    r"(press\b|publishing|publisher|verlag|books ltd|book company|imprint|"
    r"media group|publications)", re.I)

# The crawl also sweeps up whatever else ranked for a book query — sleep-medicine
# associations, fintech, web studios. A lead has to look like a book business.
BOOK_SIG = re.compile(
    r"(author|writer|novel|book|read|story|stories|publish|press|poet|fiction|"
    r"romance|fantasy|thriller|mystery|kindle|scriv|ink|quill|page|chapter|"
    r"tale|saga|verse|lit\b)", re.I)
IP_HOST = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
# only markets this round targets (plus the generic TLDs they live on)
OK_TLD = re.compile(
    r"(\.com|\.net|\.org|\.io|\.co|\.me|\.us|\.uk|\.co\.uk|\.au|\.com\.au|"
    r"\.net\.au|\.ca|\.blog|\.ink|\.books|\.shop|\.store|\.online|\.site|"
    r"\.club|\.info|\.press|\.pub|\.art|\.life|\.world|\.xyz|\.love|\.studio)$", re.I)
TYPO_MAIL = re.compile(
    r"@(gmai|gmial|gmal|gmail\.co|gmil|hotmai|yaho|outlok|iclod)\.", re.I)
BAD_MAIL_HOST = re.compile(
    r"(^www\.|facebook|twitter|instagram|linkedin|youtube|tiktok|pinterest|"
    r"wixpress|sentry|shopify|squarespace|godaddy|wordpress\.com|blogspot|"
    r"mailchimp|convertkit|substack|amazon|amazonses|sendgrid|mailgun)", re.I)

TLD_COUNTRY = [(re.compile(r"\.co\.uk$|\.uk$"), "GB"),
               (re.compile(r"\.com\.au$|\.au$|\.net\.au$"), "AU"),
               (re.compile(r"\.ca$"), "CA"),
               (re.compile(r"\.co\.nz$|\.nz$"), "NZ"),
               (re.compile(r"\.ie$"), "IE")]

NAME_TITLE_RE = re.compile(
    r"^([A-Z][a-z'\-]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-zA-Z'\-]+)\b")
STOP_TITLE = re.compile(
    r"^(home|welcome|the |official|books|contact|about|blog|shop|index|"
    r"page not found|404|coming soon|under construction)", re.I)


def load_suppression():
    sup = set()
    if SUPPRESSION.exists():
        sup = {l.strip() for l in SUPPRESSION.read_text().splitlines() if l.strip()}
    return sup


def load_serp_meta():
    meta = {}
    f = DATA / "serp_domains.jsonl"
    if f.exists():
        for line in f.read_text().splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            meta[r["domain"]] = r
    return meta


def load_serp_country_votes():
    """How often each domain ranked in each country's SERP.

    The unique-country list in serp_domains.jsonl is useless for geo (a .com
    author ranks in all four markets), so count the hits instead and let the
    majority win — an author who ranks 12x in the US and once in the UK is
    American.
    """
    votes = defaultdict(Counter)
    f = DATA / "_serp_progress.json"
    if not f.exists():
        return votes
    try:
        store = json.loads(f.read_text())
    except Exception:
        return votes
    for key, v in store.items():
        cc = v.get("country")
        for host, _rank in v.get("hits") or []:
            votes[host][cc] += 1
    return votes


def country_for(domain, votes):
    for rx, cc in TLD_COUNTRY:
        if rx.search(domain):
            return cc
    c = votes.get(domain)
    if c:
        top, n = c.most_common(1)[0]
        runner = c.most_common(2)[1][1] if len(c) > 1 else 0
        # a clear majority is a real signal; a tie between markets is not
        if n > runner:
            return top
    return "US"


def segment_for(rec):
    blob = f"{rec.get('title','')} {rec['domain']}"
    if NEWS_SIG.search(blob) and not re.search(r"author|novel", blob, re.I):
        return "drop"
    if SERVICE_SIG.search(blob):
        return "service"
    if REVIEW_SIG.search(blob) and not re.search(r"author\b", rec["domain"], re.I):
        return "partner"
    if COACH_SIG.search(blob):
        return "partner"
    if PUBLISHER_SIG.search(blob):
        return "publisher"
    return "author"


def person_name(title, domain, email):
    """Best-effort first/last name — used only for {{firstName}} personalisation."""
    t = re.split(r"[|\-–—:•]", title or "", 1)[0].strip()
    if t and not STOP_TITLE.match(t):
        m = NAME_TITLE_RE.match(t)
        if m:
            parts = m.group(1).split()
            return parts[0], parts[-1]
    local = email.split("@")[0]
    m = re.match(r"^([a-z]{3,})[._]([a-z]{3,})$", local, re.I)
    if m and not ROLE_BAD.match(m.group(1)):
        return m.group(1).capitalize(), m.group(2).capitalize()
    return "", ""


def company_from(title, domain):
    t = re.split(r"[|\-–—]", title or "", 1)[0].strip()
    if t and not STOP_TITLE.match(t) and 2 < len(t) <= 45:
        return t
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-leads", type=int, default=0)
    ap.add_argument("--min-author-score", type=int, default=1)
    args = ap.parse_args()

    sup = load_suppression()
    votes = load_serp_country_votes()

    records = []
    # contacts_*.json is the finished output; _progress_*.json lets this run
    # mid-crawl on whatever has landed so far
    for f in sorted(DATA.glob("contacts_*.json")) + sorted(DATA.glob("_progress_*.json")):
        try:
            blob = json.loads(f.read_text())
        except Exception as e:
            print(f"  skip {f.name}: {e}")
            continue
        records.extend(blob.values() if isinstance(blob, dict) else blob)
    by_domain = {}
    for r in records:
        if r.get("emails"):
            by_domain.setdefault(r["domain"], r)
    print(f"{len(records)} crawled records | {len(by_domain)} domains with email")

    # an address that appears across many unrelated sites is a vendor
    freq = Counter()
    for d, r in by_domain.items():
        for e in r["emails"]:
            freq[e.lower()] += 1

    leads, dropped = [], Counter()
    seen_emails = set()
    for domain, rec in by_domain.items():
        if domain in sup:
            dropped["suppressed_domain"] += 1
            continue
        if IP_HOST.match(domain) or not OK_TLD.search(domain):
            dropped["bad_host_or_tld"] += 1
            continue
        blob = f"{rec.get('title', '')} {domain}"
        score = rec.get("author_score", 0)
        # a real book business shows up either in the words or in the page signals
        if not BOOK_SIG.search(blob) and score < 8:
            dropped["not_a_book_site"] += 1
            continue
        seg = segment_for(rec)
        if seg == "drop":
            dropped["news_or_media"] += 1
            continue
        if seg == "author" and score < args.min_author_score and \
                not BOOK_SIG.search(domain):
            dropped["not_an_author_site"] += 1
            continue
        picked = []
        cands = []
        for e in rec["emails"]:
            e = e.lower().strip()
            local, host = e.split("@", 1)
            if ROLE_BAD.match(local) or PLACEHOLDER.search(e):
                dropped["role_or_placeholder"] += 1
                continue
            if local == domain or local.replace(".", "") == domain.replace(".", ""):
                dropped["concatenation_artifact"] += 1
                continue
            if TYPO_MAIL.search(e) or BAD_MAIL_HOST.search(host):
                dropped["typo_or_platform_mailhost"] += 1
                continue
            if host in FREEMAIL and score < 3 and not BOOK_SIG.search(domain):
                dropped["freemail_on_unconfirmed_site"] += 1
                continue
            if freq[e] >= 3:
                dropped["vendor_address"] += 1
                continue
            if host in sup:
                dropped["suppressed_email_domain"] += 1
                continue
            same_site = host == domain or host.endswith("." + domain) or \
                domain.endswith("." + host)
            if not same_site and host not in FREEMAIL:
                dropped["off_domain_third_party"] += 1
                continue
            # rank: name-ish local on own domain first, then freemail
            tokens = re.findall(r"[a-z]{3,}", domain.split(".")[0])
            score = 0
            if same_site:
                score += 3
            if any(t[:5] in local for t in tokens):
                score += 2
            if local in ("info", "hello", "contact", "hi", "me", "mail", "books"):
                score += 1
            if local in ("orders", "shop", "store", "returns", "wholesale",
                         "bookings", "enquiries", "inquiries"):
                score -= 1
            cands.append((score, e))
        # one address per solo author (two inboxes = the same human getting the
        # sequence twice); organisations can take a second contact
        cap = 1 if seg == "author" else 2
        for _, e in sorted(cands, reverse=True):
            if e in seen_emails:
                continue
            seen_emails.add(e)
            picked.append(e)
            if len(picked) >= cap:
                break
        if not picked:
            continue
        title = rec.get("title", "")
        for e in picked:
            first, last = person_name(title, domain, e)
            leads.append({
                "email": e,
                "first_name": first,
                "last_name": last,
                "company_name": company_from(title, domain) or "",
                "website": "https://" + domain,
                "country": country_for(domain, votes),
                "segment": seg,
                "author_score": rec.get("author_score", 0),
                "title": title,
                "source": "kdp_authors_r8",
            })

    print("dropped:", dict(dropped))
    # geo focus of this round
    wanted = {"US", "GB", "AU", "CA"}
    leads_geo = [l for l in leads if l["country"] in wanted]
    print(f"{len(leads)} leads | {len(leads_geo)} in US/UK/AU/CA")
    leads = sorted(leads_geo, key=lambda l: -l["author_score"])
    if args.max_leads:
        leads = leads[: args.max_leads]

    (DATA / "leads_all.jsonl").write_text(
        "\n".join(json.dumps(l, ensure_ascii=False) for l in leads))

    buckets = defaultdict(list)
    for l in leads:
        buckets[l["segment"]].append(l)
    cols = ["email", "first_name", "last_name", "company_name", "website",
            "country", "segment", "source"]
    for seg, rows in buckets.items():
        p = OUTDIR / f"instantly_import_kdp_{seg}s_r8.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"  {seg:10s} {len(rows):5d} -> {p.name}")
    by_country = Counter(l["country"] for l in leads)
    print("geo:", dict(by_country))


if __name__ == "__main__":
    main()
