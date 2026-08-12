#!/usr/bin/env python3
"""
India Amazon-seller lead build, stage 1: domain discovery via DataForSEO SERP.

Amazon.in seller profile pages publish a business name and address but never an
email, so the marketplace itself is a dead end for outreach (see the MX/UK
pipelines). The sellers' own brand sites do publish emails, so the job is to
find Indian brand/manufacturer sites that also sell on Amazon and then harvest
them (stage 2).

Query grid = product categories x intent templates + city/state templates. Every
template is written so the ranking pages are *sellers*, not marketplaces.

Output:   outreach/in-sellers/data/in_serp_domains.jsonl  {domain, title, query}
Progress: outreach/in-sellers/data/_in_serp_progress.json  (resumable, per query)

Usage:
    python3 outreach/in-sellers/in1_serp.py --dry-run
    python3 outreach/in-sellers/in1_serp.py --limit 20        # smoke test
    python3 outreach/in-sellers/in1_serp.py --max-cost 12
"""
import argparse
import concurrent.futures as cf
import importlib
import json
import re
import sys
import threading
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
dfs = importlib.import_module("prep7_dfs_maps")   # auth_header/post/balance/env

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = DATA / "in_serp_domains.jsonl"
PROGRESS = DATA / "_in_serp_progress.json"
DEPTH = 100

_lock = threading.Lock()

# ---------------------------------------------------------------- query grid
CATEGORIES = [
    # home & kitchen
    "kitchenware", "stainless steel utensils", "pressure cooker", "cookware",
    "non stick pan", "water bottle", "tiffin box", "casserole", "dinner set",
    "storage container", "home decor", "wall art", "photo frame", "candles",
    "agarbatti incense", "bedsheet", "curtains", "cushion cover", "doormat",
    "carpet rug", "mattress", "pillow", "blanket", "towel", "furniture",
    "wooden furniture", "office chair", "shoe rack", "laundry basket",
    "cleaning supplies", "mop", "dustbin", "kitchen organizer",
    # food
    "spices masala", "tea", "green tea", "coffee beans", "organic food",
    "dry fruits", "nuts", "honey", "ghee", "cold pressed oil", "pickle",
    "millets", "protein bar", "snacks namkeen", "chocolate", "jaggery",
    "flour atta", "instant mix", "papad", "sauces and dips",
    # beauty & wellness
    "ayurvedic products", "skincare", "face wash", "sunscreen", "hair oil",
    "shampoo", "beard oil", "essential oil", "soap handmade", "perfume",
    "cosmetics", "lipstick", "nail polish", "makeup brush", "hair care",
    "health supplements", "protein powder", "multivitamin", "ayurvedic medicine",
    "sanitary pads", "baby care products", "diapers", "baby food",
    # apparel & accessories
    "kurta", "saree", "ethnic wear", "tshirt brand", "shirts", "jeans",
    "activewear", "innerwear", "socks", "footwear", "sandals", "sports shoes",
    "handbag", "backpack", "wallet", "leather goods", "belt", "jewellery",
    "artificial jewellery", "silver jewellery", "watches", "sunglasses",
    "scarf stole", "kids clothing", "school bag",
    # electronics & accessories
    "mobile accessories", "phone case", "screen guard", "power bank",
    "earphones", "bluetooth speaker", "smartwatch", "laptop accessories",
    "keyboard mouse", "usb cable", "charger", "led bulb", "led lights",
    "extension board", "inverter battery", "cctv camera", "smart home device",
    "computer peripherals", "gaming accessories", "car accessories",
    "car care products", "bike accessories", "helmet",
    # hobby, sports, kids
    "toys", "educational toys", "soft toys", "board games", "puzzle",
    "stationery", "notebook", "art supplies", "craft supplies", "musical instrument",
    "guitar", "yoga mat", "fitness equipment", "dumbbells", "cricket equipment",
    "badminton racket", "football", "camping gear", "fishing gear",
    "pet supplies", "dog food", "aquarium", "gardening tools", "seeds plants",
    "planters", "bird feeder",
    # industrial / B2B-ish consumer
    "hardware tools", "power tools", "hand tools", "safety equipment",
    "industrial supplies", "packaging material", "adhesive tape",
    "electrical fittings", "plumbing fittings", "paint", "hardware fittings",
    "measuring instrument", "lab equipment", "medical devices",
    "surgical instruments", "hospital supplies", "office supplies",
    "printing supplies", "ink cartridge",
    # crafts / regional
    "handicrafts", "brass items", "wooden handicraft", "marble handicraft",
    "terracotta pottery", "ceramic tableware", "handloom", "khadi products",
    "jute bags", "leather bags", "block print", "bamboo products",
    "coir products", "puja items", "religious idols", "gift items",
    "return gifts", "corporate gifts", "wedding gifts",
]

TEMPLATES = [
    '{c} brand india "buy on amazon"',
    '{c} india "available on amazon"',
    'buy {c} online india "amazon.in"',
    '{c} manufacturer india amazon seller',
    'indian {c} brand shop online amazon',
]

CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Ahmedabad", "Chennai",
    "Kolkata", "Surat", "Pune", "Jaipur", "Lucknow", "Kanpur", "Nagpur",
    "Indore", "Thane", "Bhopal", "Visakhapatnam", "Patna", "Vadodara",
    "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad", "Meerut",
    "Rajkot", "Varanasi", "Srinagar", "Aurangabad", "Amritsar", "Noida",
    "Gurgaon", "Coimbatore", "Kochi", "Chandigarh", "Guwahati", "Jodhpur",
    "Madurai", "Raipur", "Ranchi", "Tiruppur", "Moradabad", "Jalandhar",
    "Panipat", "Bhiwandi", "Sivakasi", "Firozabad", "Aligarh", "Karur",
    "Erode",
]

CITY_TEMPLATES = [
    'amazon seller {city} india contact',
    'ecommerce brand {city} "sell on amazon"',
    '{city} manufacturer "amazon.in" online store',
]


def build_queries():
    qs = []
    for c in CATEGORIES:
        for t in TEMPLATES:
            qs.append(t.format(c=c))
    for city in CITIES:
        for t in CITY_TEMPLATES:
            qs.append(t.format(city=city))
    seen, out = set(), []
    for q in qs:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


# ------------------------------------------------------------------ filtering
# marketplaces, media, gov/edu, SaaS and other non-seller hosts
BLOCK = re.compile(
    r"(^|\.)(amazon\.|amzn\.|flipkart|myntra|ajio|meesho|snapdeal|shopclues|"
    r"paytmmall|tatacliq|jiomart|bigbasket|nykaa|firstcry|pepperfry|urbanladder|"
    r"limeroad|craftsvilla|indiamart|tradeindia|exportersindia|justdial|sulekha|"
    r"quikr|olx\.|udaan\.|moglix|industrybuying|alibaba|aliexpress|made-in-china|"
    r"ebay\.|etsy\.|walmart|shopify\.com|wix|squarespace|blogspot|wordpress\.com|"
    r"medium\.com|linktr\.ee|google\.|youtube|facebook|instagram|linkedin|twitter|"
    r"pinterest|reddit|quora|wikipedia|scribd|slideshare|issuu|tripadvisor|"
    r"zomato|swiggy|practo|naukri|shiksha|collegedunia|byjus|unacademy|coursera|"
    r"timesofindia|economictimes|hindustantimes|ndtv|business-standard|livemint|"
    r"thehindu|indianexpress|moneycontrol|zeebiz|financialexpress|news18|"
    r"businessinsider|forbes|entrepreneur|inc42|yourstory|techcrunch|"
    r"tofler|zaubacorp|indiafilings|cleartax|vakilsearch|lawrato|"
    r"glassdoor|indeed|ambitionbox|apollo\.io|crunchbase|owler|zoominfo|"
    r"archive\.org|github|stackoverflow|apple\.com|microsoft|adobe)"
    r"|\.gov(\.in)?$|\.nic\.in$|\.ac\.in$|\.edu(\.in)?$|\.mil$",
    re.I)


def host_of(url):
    try:
        h = urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""
    h = h[4:] if h.startswith("www.") else h
    return h if "." in h else ""


def parse_items(items):
    out = []
    for it in items or []:
        if it.get("type") != "organic":
            continue
        h = host_of(it.get("url") or "")
        if not h or BLOCK.search(h):
            continue
        out.append((h, (it.get("title") or "").strip()[:120]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--max-cost", type=float, default=14.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    queries = build_queries()
    store = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    todo = [q for q in queries if q not in store]
    if args.limit:
        todo = todo[: args.limit]
    print(f"grid: {len(queries)} queries ({len(store)} cached) -> "
          f"{len(todo)} to run, depth {DEPTH}")
    if args.dry_run:
        for q in queries[:10]:
            print("  ", q)
        return

    hdr = dfs.auth_header(dfs.env())
    bal = dfs.balance(hdr)
    budget = min(args.max_cost, bal - 1.0)
    print(f"balance ${bal:.2f} | budget for this stage ${budget:.2f}")

    done, spent, stop = [0], [0.0], threading.Event()

    def run(kw):
        if stop.is_set():
            return
        try:
            resp = dfs.post("/serp/google/organic/live/regular", [{
                "keyword": kw, "location_name": "India", "language_code": "en",
                "depth": DEPTH}], hdr)
            task = (resp.get("tasks") or [{}])[0]
            res = (task.get("result") or [{}])[0] if task.get("result") else {}
            hits = parse_items(res.get("items"))
            cost = resp.get("cost") or 0.0
        except Exception as ex:
            print(f"  FAIL [{kw[:45]}]: {str(ex)[:60]}")
            return
        with _lock:
            store[kw] = hits
            spent[0] += cost
            done[0] += 1
            if spent[0] >= budget:
                stop.set()
            if done[0] % 50 == 0 or stop.is_set():
                PROGRESS.write_text(json.dumps(store))
                uniq = {h for v in store.values() for h, _ in v}
                print(f"  {done[0]}/{len(todo)} | {len(uniq)} domains | "
                      f"${spent[0]:.3f}")

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(run, todo))
    PROGRESS.write_text(json.dumps(store))

    seen = {}
    for kw, hits in store.items():
        for h, title in hits:
            if h not in seen:
                seen[h] = {"domain": h, "title": title, "query": kw}
    with OUT.open("w", encoding="utf-8") as f:
        for r in seen.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n{len(seen)} unique domains -> {OUT} | spent ${spent[0]:.2f}")


if __name__ == "__main__":
    main()
