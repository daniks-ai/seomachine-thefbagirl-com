#!/usr/bin/env python3
"""Build a STRICT, validated Instantly CSV of UK Amazon sellers.

Only keeps an email when the site content corroborates the seller — no blind
name-guess sends (protects shared sender reputation). Corroboration =
  - email domain == discovered seller domain (self-hosted), AND
  - local-part is not a template placeholder / tracking junk, AND
  - the domain token overlaps the storefront brand or legal-name token.
Free gmail/outlook addresses are kept only when the local-part contains the
brand token.

Inputs (beside this script): uk_sellers_uk.jsonl, uk_domains.jsonl,
  outreach/data/layer1_contacts_raw.json (harvest output)
Output: outreach/uk-sellers/data/instantly_UK_SELLERS.csv  (+ _dropped.csv audit)
Dedupes emails vs every existing Instantly master + suppress list.
"""
import csv, json, re, sys, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent            # outreach/uk-sellers
REPO = HERE.parents[1]                             # repo root
SCR = HERE
OUTDIR = HERE / "data"
OUTDIR.mkdir(parents=True, exist_ok=True)

FREE = {"gmail.com", "hotmail.com", "hotmail.co.uk", "outlook.com",
        "yahoo.com", "yahoo.co.uk", "live.com", "live.co.uk", "icloud.com",
        "btinternet.com", "aol.com", "googlemail.com", "sky.com", "talktalk.net"}
PLACEHOLDER = re.compile(
    r"^(youremail|your|example|email|name|test|demo|user|info@email)$"
    r"|@email\.com$|@sentry|wixpress|sentry-next", re.I)
JUNK = re.compile(
    r"(no-?reply|noreply|postmaster|mailer-daemon|abuse|hostmaster|dns-admin|"
    r"wixpress|sentry|@sentry|@example|@wix|@squarespace|@godaddy|@shopify|"
    r"@cloudflare|@googlemail|@domain|@email\.com|@2x|\.png|\.jpg|\.gif)", re.I)

STOPWORDS = {
    "limited", "trading", "company", "store", "shop", "official", "london",
    "united", "kingdom", "group", "holdings", "holding", "retail", "supplies",
    "enterprises", "enterprise", "solutions", "ventures", "products", "brands",
    "international", "global", "online", "direct", "sales"}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def clean_email(e):
    e = e.strip().lower()
    m = re.match(r"([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})", e)
    return m.group(1) if m else None


def brand_tokens(rec):
    toks = set()
    for f in (rec.get("n"), rec.get("biz")):
        t = norm(f)
        if len(t) >= 4:
            toks.add(t)
        for w in re.split(r"[^a-z0-9]+", (f or "").lower()):
            wn = norm(w)
            if len(wn) >= 4 and wn not in STOPWORDS:
                toks.add(wn)
    return toks


def domain_token(dom):
    # strip .co.uk / .uk / .com etc — take the registrable label
    parts = dom.split(".")
    return norm(parts[0])


def load_contacts():
    raw = json.load((REPO / "outreach/data/layer1_contacts_raw.json").open())
    if isinstance(raw, list):
        raw = {r.get("domain"): r for r in raw}
    return raw


def existing_emails():
    seen = set()
    for p in REPO.glob("outreach/**/*.csv"):
        if "instantly_UK_SELLERS" in p.name:
            continue
        try:
            for row in csv.DictReader(p.open(encoding="utf-8", errors="ignore")):
                for k, v in row.items():
                    if k and "email" in k.lower() and v and "@" in v:
                        seen.add(v.strip().lower())
        except Exception:
            pass
    return seen


def main():
    sellers = [json.loads(l) for l in (SCR / "uk_sellers_uk.jsonl").read_text().splitlines() if l.strip()]
    dom_by_seller = {}
    for l in (SCR / "uk_domains.jsonl").read_text().splitlines():
        if l.strip():
            d = json.loads(l)
            dom_by_seller[d["s"]] = d["domain"]
    contacts = load_contacts()
    blocked = existing_emails()

    kept, dropped, used_emails = [], [], set()
    for rec in sellers:
        sid = rec["s"]
        dom = dom_by_seller.get(sid)
        if not dom:
            dropped.append((rec.get("n"), "", "no-domain"))
            continue
        toks = brand_tokens(rec)
        dtok = domain_token(dom)
        emails = (contacts.get(dom) or {}).get("emails") or []
        candidates = []
        for raw in emails:
            e = clean_email(raw)
            if not e or JUNK.search(e) or PLACEHOLDER.search(e.split("@")[0]) or PLACEHOLDER.search(e):
                continue
            local, edom = e.split("@", 1)
            if edom in FREE:
                if any(t in local or local in t for t in toks if len(t) >= 4):
                    candidates.append((e, "free-brandmatch"))
                continue
            if edom == dom or edom.endswith("." + dom) or dom.endswith("." + edom):
                candidates.append((e, "self-hosted"))
            elif domain_token(edom) and domain_token(edom) == dtok:
                # same brand label, different TLD (e.g. rinkit.co.uk guessed but
                # the site redirects to rinkit.com). Corroboration check below
                # still requires the brand token to match, so this stays strict.
                candidates.append((e, "same-brand-alt-tld"))
        corrob = any(t and (t in dtok or dtok in t) for t in toks) or dtok in {norm(rec.get("n")), norm(rec.get("biz"))}
        if not candidates:
            dropped.append((rec.get("n"), dom, "no-clean-email"))
            continue
        if not corrob:
            dropped.append((rec.get("n"), dom, "brand-collision(domain!=brand)"))
            continue

        def rank(pair):
            e = pair[0]; lp = e.split("@")[0]
            if re.match(r"^(info|contact|sales|hello|hi|admin|support|enquiries|"
                        r"customerservice|customerservices|office|shop|team)$", lp):
                return 1
            return 0  # named local-part best
        candidates.sort(key=rank)
        best = None
        for e, method in candidates:
            if e in used_emails or e in blocked:
                continue
            best = (e, method); break
        if not best:
            dropped.append((rec.get("n"), dom, "dup"))
            continue
        used_emails.add(best[0])
        parts = [p.strip() for p in (rec.get("addr") or "").split(",")]
        city = parts[-3] if len(parts) >= 3 else ""
        postcode = parts[-2] if len(parts) >= 2 else ""
        kept.append({
            "email": best[0],
            "first_name": "there",
            "company_name": rec.get("n") or rec.get("biz") or "",
            "website": "https://" + dom,
            "city": city, "postcode": postcode, "country": "GB",
            "seller_id": sid, "legal_name": rec.get("biz") or "",
            "segment": "UK-SELLERS", "source": "amazon.co.uk",
            "match": best[1],
        })

    fields = ["email", "first_name", "company_name", "website", "city",
              "postcode", "country", "seller_id", "legal_name", "segment",
              "source", "match"]
    out = OUTDIR / "instantly_UK_SELLERS.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(kept)
    with (OUTDIR / "instantly_UK_SELLERS_dropped.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["name", "domain", "reason"]); w.writerows(dropped)
    print(f"sellers={len(sellers)} kept={len(kept)} dropped={len(dropped)}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
