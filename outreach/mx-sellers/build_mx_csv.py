#!/usr/bin/env python3
"""Build a STRICT, validated Instantly CSV of Mexican Amazon sellers.

Only keeps an email when the site content corroborates the seller — no blind
name-guess sends (protects shared sender reputation). Corroboration =
  - email domain == discovered seller domain (self-hosted), AND
  - local-part is not a template placeholder / tracking junk, AND
  - the domain token overlaps the storefront brand or legal-name token
    (so getac.com.mx for reseller "INDUSTHER" is dropped unless the brand
    token literally matches the domain).
Free gmail/outlook addresses are kept only when the local-part contains the
brand token.

Inputs (scratchpad): mx_sellers_mx.jsonl, mx_domains.jsonl,
  outreach/data/layer1_contacts_raw.json (harvest output)
Output: outreach/mx-sellers/data/instantly_MX_SELLERS.csv  (+ _dropped.csv audit)
Dedupes emails vs every existing Instantly master + suppress list.
"""
import csv, json, re, sys, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent            # outreach/mx-sellers
REPO = HERE.parents[1]                             # repo root
SCR = HERE                                         # sellers/domains jsonl live beside this script
OUTDIR = HERE / "data"
OUTDIR.mkdir(parents=True, exist_ok=True)

FREE = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yahoo.com.mx",
        "hotmail.com.mx", "live.com", "icloud.com", "prodigy.net.mx"}
PLACEHOLDER = re.compile(
    r"^(tuemail|tu|su|example|ejemplo|correo|email|nombre|test|demo|user|"
    r"info@email|youremail|your)$|@email\.com$|@correo|@sentry|wixpress|"
    r"sentry-next", re.I)
JUNK = re.compile(
    r"(no-?reply|noreply|postmaster|mailer-daemon|abuse|hostmaster|dns-admin|"
    r"wixpress|sentry|@sentry|@example|@wix|@squarespace|@godaddy|@shopify|"
    r"@cloudflare|@googlemail|@domain|@email\.com|@correo|@2x|\.png|\.jpg|\.gif)", re.I)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def clean_email(e):
    e = e.strip().lower()
    # strip trailing garbage the harvester sometimes concatenates
    m = re.match(r"([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})", e)
    return m.group(1) if m else None


def brand_tokens(rec):
    toks = set()
    for f in (rec.get("n"), rec.get("biz")):
        t = norm(f)
        if len(t) >= 4:
            toks.add(t)
        # also individual words >=4 chars
        for w in re.split(r"[^a-z0-9]+", (f or "").lower()):
            wn = norm(w)
            if len(wn) >= 4 and wn not in {
                "mexico", "store", "shop", "tienda", "oficial", "comercializadora",
                "distribuidora", "importaciones", "grupo", "corporativo", "sadecv",
                "empresarial", "productos", "innovadores", "supermercado", "importado"}:
                toks.add(wn)
    return toks


def domain_token(dom):
    return norm(dom.split(".")[0])


def load_contacts():
    raw = json.load((REPO / "outreach/data/layer1_contacts_raw.json").open())
    if isinstance(raw, list):
        raw = {r.get("domain"): r for r in raw}
    return raw


def existing_emails():
    seen = set()
    for p in REPO.glob("outreach/**/*.csv"):
        if "instantly_MX_SELLERS" in p.name:
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
    sellers = [json.loads(l) for l in (SCR / "mx_sellers_mx.jsonl").read_text().splitlines() if l.strip()]
    dom_by_seller = {}
    for l in (SCR / "mx_domains.jsonl").read_text().splitlines():
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
                # only if local-part carries a brand token
                if any(t in local or local in t for t in toks if len(t) >= 4):
                    candidates.append((e, "free-brandmatch"))
                continue
            if edom == dom or edom.endswith("." + dom) or dom.endswith("." + edom):
                candidates.append((e, "self-hosted"))
        # corroboration: domain token must overlap a brand token, else drop
        corrob = any(t and (t in dtok or dtok in t) for t in toks) or dtok in {norm(rec.get("n")), norm(rec.get("biz"))}
        if not candidates:
            dropped.append((rec.get("n"), dom, "no-clean-email"))
            continue
        if not corrob:
            dropped.append((rec.get("n"), dom, "brand-collision(domain!=brand)"))
            continue
        # prefer named/role personal over generic
        def rank(pair):
            e = pair[0]; lp = e.split("@")[0]
            if re.match(r"^(info|contacto|contact|ventas|sales|hola|hello|admin|atencion|servicioalcliente|contacto1)$", lp):
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
        state = parts[-2] if len(parts) >= 2 else ""
        kept.append({
            "email": best[0],
            "first_name": "equipo",
            "company_name": rec.get("n") or rec.get("biz") or "",
            "website": "https://" + dom,
            "city": city, "state": state, "country": "MX",
            "seller_id": sid, "legal_name": rec.get("biz") or "",
            "segment": "MX-SELLERS", "source": "amazon.com.mx",
            "match": best[1],
        })

    fields = ["email", "first_name", "company_name", "website", "city", "state",
              "country", "seller_id", "legal_name", "segment", "source", "match"]
    out = OUTDIR / "instantly_MX_SELLERS.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(kept)
    with (OUTDIR / "instantly_MX_SELLERS_dropped.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["name", "domain", "reason"]); w.writerows(dropped)
    print(f"sellers={len(sellers)} kept={len(kept)} dropped={len(dropped)}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
