#!/usr/bin/env python3
"""
Argentina lead engine, layer A: Google Maps via DataForSEO.

WHY MAPS AND NOT AN AMAZON SCRAPE (read before "fixing" this):
Argentina has **no Amazon marketplace** — there is no amazon.com.ar. So the
MX/UK playbook (scrape the local marketplace, keep sellers whose seller-profile
address country == XX) has no Argentine analogue. Argentine businesses that
touch Amazon do it as exporters/brands on amazon.com, or as agencies serving
US-market clients. Neither is discoverable from a marketplace crawl.

What IS discoverable at volume: the Argentine e-commerce economy itself —
performance/e-commerce agencies, marketplace consultancies, importers and
online retailers — via Google Maps, which is business-registry-grade coverage
for AR and costs ~$0.002 per 20 places.

Each place is tiered on its title/category/domain so the CSV builder can send
the right offer:
  tier A  amazon-explicit (agency or seller)     -> Amazon copy, highest intent
  tier B  ecommerce / marketplace / performance  -> agency + affiliate copy
  tier C  online retailer / importer / exporter  -> seller copy, lowest intent

Output: outreach/ar-sellers/data/ar_gmaps.jsonl {domain, company, tier, city, ...}
Resumable cache: data/_ar_dfs_maps_progress.json

Usage:
    python3 outreach/ar-sellers/ar1_dfs_maps.py --dry-run
    python3 outreach/ar-sellers/ar1_dfs_maps.py --limit 10
    python3 outreach/ar-sellers/ar1_dfs_maps.py
    python3 outreach/ar-sellers/ar1_dfs_maps.py --retry-empty
"""
import argparse
import base64
import concurrent.futures as cf
import json
import re
import sys
import threading
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = HERE / "data"
ENV = ROOT / "data_sources" / "config" / ".env"
OUT = DATA / "ar_gmaps.jsonl"
PROGRESS = DATA / "_ar_dfs_maps_progress.json"

API = "https://api.dataforseo.com/v3"
COST_PER_SEARCH = 0.002
DEPTH = 20

# Tier A — anything that names Amazon. Tiny pool in AR, highest intent.
QUERIES_A = [
    "agencia amazon",
    "consultor amazon fba",
    "vender en amazon",
    "amazon ads agencia",
]
# Tier B — the volume tier: agencies that already run paid media / marketplaces.
QUERIES_B = [
    "agencia de ecommerce",
    "agencia de marketing digital",
    "agencia mercado libre",
    "consultora ecommerce",
    "agencia de publicidad digital",
    "agencia performance marketing",
    "desarrollo tienda online",
    "agencia marketplace",
]
# Tier C — brands/retailers/importers that could sell on Amazon US themselves.
QUERIES_C = [
    "venta online mayorista",
    "importador mayorista",
    "distribuidora mayorista",
    "tienda online",
    "empresa de exportacion",
    "fabrica de productos",
]

# 44 AR cities: every provincial capital + the industrial/AMBA belt where the
# e-commerce and export firms actually sit.
CITIES = [
    "Buenos Aires", "Palermo, Buenos Aires", "Belgrano, Buenos Aires",
    "Microcentro, Buenos Aires", "Villa Crespo, Buenos Aires",
    "Vicente Lopez", "San Isidro", "Martinez", "Olivos", "Tigre",
    "San Fernando", "Quilmes", "Avellaneda", "Lanus", "Lomas de Zamora",
    "Moron", "San Martin", "Ramos Mejia", "La Plata", "Pilar",
    "Cordoba", "Villa Carlos Paz", "Rio Cuarto", "Rosario",
    "Santa Fe", "Rafaela", "Mendoza", "Godoy Cruz", "San Rafael",
    "Mar del Plata", "Bahia Blanca", "Tandil", "Tucuman", "Salta",
    "Jujuy", "Santiago del Estero", "Resistencia", "Corrientes",
    "Posadas", "Parana", "Neuquen", "Bariloche", "Rio Gallegos",
    "Ushuaia", "San Juan", "San Luis", "La Rioja", "Catamarca",
    "Formosa", "Comodoro Rivadavia", "Trelew", "Santa Rosa",
]
# Tier C sweeps only the top metros — long-tail provinces are all local retail.
CITIES_C = CITIES[:22]

JUNK = re.compile(
    r"(amazon\.|google\.|facebook|instagram|linkedin|twitter|youtube|tiktok|"
    r"whatsapp|yelp\.|mercadolibre|mercadolibre\.com|tiendanube\.com$|"
    r"shopify\.com$|wixsite|wordpress\.com|blogspot|squarespace|"
    r"godaddysites|business\.site|sites\.google|linktr\.ee|"
    r"gob\.ar$|gov\.ar$|edu\.ar$|"
    r"computrabajo|indeed|zonajobs|bumeran|"
    r"paginasamarillas|guiaempresas|cylex|opendi|infoisinfo)", re.I)

RE_A = re.compile(r"amazon|\bfba\b", re.I)
RE_B = re.compile(
    r"(agenc|market|ecommerce|e-commerce|comercio electr|digital|"
    r"publicidad|performance|consultor|shop|tienda ?nube|marketplace|"
    r"seo|ads|media)", re.I)

_lock = threading.Lock()


def env():
    d = {}
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def auth_header(e):
    tok = base64.b64encode(
        f"{e['DATAFORSEO_LOGIN']}:{e['DATAFORSEO_PASSWORD']}".encode()).decode()
    return "Basic " + tok


def post(endpoint, payload, hdr):
    req = urllib.request.Request(
        API + endpoint, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": hdr, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def balance(hdr):
    req = urllib.request.Request(API + "/appendix/user_data",
                                 headers={"Authorization": hdr})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["tasks"][0]["result"][0]["money"]["balance"]


def build_searches():
    out, seen = [], set()
    plan = ([(c, q, "A") for c in CITIES for q in QUERIES_A]
            + [(c, q, "B") for c in CITIES for q in QUERIES_B]
            + [(c, q, "C") for c in CITIES_C for q in QUERIES_C])
    for city, q, tier in plan:
        key = f"{tier}|{city}|{q}"
        if key in seen:
            continue
        seen.add(key)
        out.append({"key": key, "keyword": f"{q} {city}", "city": city,
                    "query_tier": tier})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--retry-empty", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    searches = build_searches()
    print(f"plan: {len(searches)} searches x {DEPTH} places, "
          f"est ${len(searches)*COST_PER_SEARCH:.2f}")
    if args.dry_run:
        return

    e = env()
    hdr = auth_header(e)
    store = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    if args.retry_empty:
        for k in [k for k, v in store.items() if not v.get("records")]:
            del store[k]
    todo = [s for s in searches if s["key"] not in store]
    if args.limit:
        todo = todo[: args.limit]

    bal = balance(hdr)
    need = len(todo) * COST_PER_SEARCH
    print(f"{len(store)} cached, {len(todo)} to fetch | "
          f"balance ${bal:.2f}, need ~${need:.2f}")
    if need > bal:
        sys.exit(f"insufficient balance: need ${need:.2f}, have ${bal:.2f}")

    done, spent = [0], [0.0]

    def run(s):
        try:
            resp = post("/serp/google/maps/live/advanced", [{
                "keyword": s["keyword"], "location_name": "Argentina",
                "language_code": "es", "depth": DEPTH}], hdr)
            task = (resp.get("tasks") or [{}])[0]
            res = (task.get("result") or [{}])[0] if task.get("result") else {}
            items = res.get("items") or []
            recs = [{"title": it.get("title"),
                     "website": it.get("url") or (
                         f"https://{it['domain']}" if it.get("domain") else ""),
                     "category": it.get("category")}
                    for it in items if it.get("title")]
            cost = resp.get("cost") or 0.0
        except Exception as ex:
            recs, cost = [], 0.0
            print(f"  FAIL [{s['keyword'][:40]}]: {str(ex)[:60]}")
        with _lock:
            store[s["key"]] = {"city": s["city"],
                               "query_tier": s["query_tier"], "records": recs}
            spent[0] += cost
            done[0] += 1
            if done[0] % 50 == 0:
                PROGRESS.write_text(json.dumps(store, ensure_ascii=False))
                places = sum(len(v["records"]) for v in store.values())
                print(f"  {done[0]}/{len(todo)} | {places} places | "
                      f"spent ${spent[0]:.2f}")

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(run, todo))
    PROGRESS.write_text(json.dumps(store, ensure_ascii=False))

    by_dom = {}
    for v in store.values():
        for r in v["records"]:
            m = re.match(r"https?://([^/\s]+)", r.get("website") or "")
            if not m:
                continue
            d = m.group(1).lower().split(":")[0]
            d = d[4:] if d.startswith("www.") else d
            if not d or "." not in d or JUNK.search(d):
                continue
            blob = f"{r.get('title') or ''} {r.get('category') or ''} {d}"
            tier = "A" if RE_A.search(blob) else (
                "B" if (v["query_tier"] == "B" or RE_B.search(blob)) else "C")
            prev = by_dom.get(d)
            # a domain seen in several searches keeps its strongest tier
            if prev and prev["tier"] <= tier:
                continue
            by_dom[d] = {"domain": d, "company": r.get("title") or d,
                         "tier": tier, "city": v["city"],
                         "category": r.get("category") or "",
                         "source": "google_maps_dfs"}
    with OUT.open("w", encoding="utf-8") as f:
        for r in by_dom.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    places = sum(len(v["records"]) for v in store.values())
    tiers = {t: sum(1 for r in by_dom.values() if r["tier"] == t)
             for t in "ABC"}
    print(f"\n{places} places -> {len(by_dom)} unique domains {tiers} -> {OUT}")
    print(f"run cost ${spent[0]:.2f}")


if __name__ == "__main__":
    main()
