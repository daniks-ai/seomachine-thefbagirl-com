#!/usr/bin/env python3
"""
KDP authors round (US/UK/AU/CA) — domain discovery via DataForSEO organic SERP.

The KDP *services* niche (agencies, book-marketing shops, indie presses) was
mined dry over rounds 1-7 (~380 EN leads). The only pool big enough to yield
thousands of leads is the self-published authors themselves — they are the ones
running (or failing to run) Amazon Ads on their own books, i.e. the direct
$49/$129 offer, not the white-label one.

Almost every working indie author has a small WordPress/Squarespace site with a
Books / About / Contact page. This pass finds those sites by searching the
footprints they share, per genre and per country.

Output:  data/serp_domains.jsonl   {domain, country, query, rank}
Cache:   data/_serp_progress.json  (resumable; re-runs cost nothing)

Usage:
    python3 outreach/kdp-authors/serp_discovery.py --dry-run
    python3 outreach/kdp-authors/serp_discovery.py --limit 20
    python3 outreach/kdp-authors/serp_discovery.py --workers 12
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
maps = importlib.import_module("prep7_dfs_maps")

DATA = Path(__file__).resolve().parent / "data"
OUT = DATA / "serp_domains.jsonl"
PROGRESS = DATA / "_serp_progress.json"

COST_PER_QUERY = 0.0035
DEPTH = 100

_lock = threading.Lock()

GEOS = [
    ("United States", "US"),
    ("United Kingdom", "GB"),
    ("Australia", "AU"),
    ("Canada", "CA"),
]

# Fiction genres where indie/KDP publishing dominates.
GENRES = [
    "romance", "contemporary romance", "dark romance", "paranormal romance",
    "romantasy", "thriller", "psychological thriller", "crime fiction",
    "cozy mystery", "mystery", "fantasy", "urban fantasy", "epic fantasy",
    "science fiction", "space opera", "military science fiction", "litrpg",
    "horror", "historical fiction", "western", "young adult fantasy",
    "paranormal", "post-apocalyptic", "sweet romance", "romantic suspense",
    "christian fiction", "clean romance", "detective fiction",
]

# Non-fiction / low-content verticals — usually a brand, not a novelist.
NICHES = [
    "cookbook author", "memoir author", "self-help author",
    "children's book author", "picture book author", "middle grade author",
    "business book author", "personal finance author", "fitness book author",
    "travel guide author", "coloring book creator", "puzzle book publisher",
    "activity book publisher", "planner brand", "journal brand",
    "workbook publisher", "devotional author", "poetry author",
]

# Footprints that show up on an author's own site, not on a retailer page.
GENRE_TEMPLATES = [
    '"{g} author" "contact me" books',
    '"{g} author" official website newsletter "my books"',
    'indie "{g} author" website "media kit"',
    'self-published "{g} author" website contact email',
    '"{g} author" "signed paperbacks" OR "signed copies" contact',
]
NICHE_TEMPLATES = [
    '"{g}" self-published website "contact"',
    '"{g}" indie "available on amazon" website contact email',
]
GENERIC = [
    '"indie author" "press kit" contact email',
    '"self-published author" website "contact me" amazon',
    '"author website" "buy on amazon" "email me"',
    '"my novels" author website contact email',
    '"my books" author "kindle unlimited" website contact',
    '"KDP author" website "contact"',
    '"author of" "available on amazon" "for media inquiries"',
    '"indie author" newsletter "free book" website contact',
    '"self publishing" author blog "my books" contact email',
    '"amazon bestselling author" website "contact"',
    '"author" "rights and permissions" self-published contact',
    '"book series" author official site "contact" -publisher',
]


# --- wave 2 --------------------------------------------------------------
# Wave 1 (genre x footprint) returned ~4.7k domains. Wave 2 widens along three
# axes that surface *different* authors rather than re-ranking the same ones:
# tropes/series language, the author's commercial pages, and the non-fiction
# and low-content brands that never call themselves "authors".
TROPES = [
    "enemies to lovers", "second chance romance", "small town romance",
    "reverse harem", "why choose romance", "mafia romance", "hockey romance",
    "grumpy sunshine", "fated mates", "shifter romance", "vampire romance",
    "dragon rider fantasy", "cultivation progression fantasy", "cozy fantasy",
    "amateur sleuth", "psychological suspense", "domestic thriller",
    "military thriller", "spy thriller", "time travel romance",
    "regency romance", "viking romance", "steamy romance", "clean sweet romance",
]
TROPE_TEMPLATES = [
    '"{g}" author website "contact"',
    '"{g}" indie author "newsletter" "my books"',
]
COMMERCIAL_TEMPLATES = [
    '"{g} author" "book a signing" OR "events" contact email',
    '"{g} author" "arc team" OR "street team" sign up contact',
    '"{g} author" "bulk orders" OR "wholesale" signed books contact',
    '"{g} author" "rights" OR "foreign rights" enquiries website',
]
LOWCONTENT = [
    "coloring book publisher", "activity book brand", "sudoku book publisher",
    "crossword book publisher", "word search book publisher",
    "kids workbook brand", "notebook brand amazon", "guided journal brand",
    "recipe journal brand", "prayer journal brand", "budget planner brand",
    "teacher workbook publisher", "handwriting workbook publisher",
    "logbook publisher", "sketchbook brand", "large print puzzle books",
    "toddler activity book brand", "kdp low content publisher",
]
LOWCONTENT_TEMPLATES = [
    '"{g}" "amazon" website "contact us" -jobs',
    '"{g}" self-published "wholesale" OR "bulk" contact email',
]
GENERIC2 = [
    '"author" "my amazon author page" website contact',
    '"author" "books2read" OR "universal book link" contact email',
    '"indie author" "advertising" "amazon ads" blog contact',
    '"self-published" author "my launch" "amazon ranking" website',
    '"author" website "for review copies" contact email',
    '"author" "school visits" books website contact',
    '"author" "speaking" "my books" contact email website',
    '"our books" "independent publisher" contact submissions amazon',
    '"micro press" OR "small press" indie books contact amazon',
    '"author services" "amazon ads" book marketing contact',
    '"book coach" author website contact email',
    '"launch team" author "kindle" website contact',
]


def build_queries2():
    out = []
    for loc, cc in GEOS:
        for g in TROPES:
            for t in TROPE_TEMPLATES:
                out.append((t.format(g=g), loc, cc))
        for g in GENRES[:14]:
            for t in COMMERCIAL_TEMPLATES:
                out.append((t.format(g=g), loc, cc))
        for g in LOWCONTENT:
            for t in LOWCONTENT_TEMPLATES:
                out.append((t.format(g=g), loc, cc))
        for q in GENERIC2:
            out.append((q, loc, cc))
    return out


# --- wave 3: hubs ---------------------------------------------------------
# Instead of one author per result, these queries find pages that *list* authors
# — interviews, multi-author box sets, blog tours, anthologies, review blogs,
# newsletter swaps. The crawler harvests their outbound links, so one hub can be
# worth dozens of author domains at zero SERP cost.
HUB_TEMPLATES = [
    '"{g}" "author interview" "her website" OR "his website"',
    '"{g}" multi-author box set "featuring" authors',
    '"{g}" anthology "contributing authors" indie',
    '"{g}" book blog tour "hosted by" authors sign up',
    '"{g}" "author spotlight" indie blog',
    '"{g}" "new releases" indie authors roundup blog',
]
HUB_GENERIC = [
    '"indie author" blogroll "author friends" links',
    '"authors i recommend" indie website links',
    '"newsletter swap" authors sign up list',
    '"author takeover" facebook group authors list website',
    '"book bloggers" list "author websites"',
    '"cover reveal" indie author blog "about the author" website',
    '"meet the authors" indie anthology charity',
    '"writing group" members published authors websites',
    '"self published authors" directory list website',
    '"local authors" bookstore list website',
]


def build_queries3():
    out = []
    for loc, cc in GEOS:
        for g in GENRES[:18]:
            for t in HUB_TEMPLATES:
                out.append((t.format(g=g), loc, cc))
        for q in HUB_GENERIC:
            out.append((q, loc, cc))
    return out


def build_queries():
    out = []
    for loc, cc in GEOS:
        for g in GENRES:
            for t in GENRE_TEMPLATES:
                out.append((t.format(g=g), loc, cc))
        for g in NICHES:
            for t in NICHE_TEMPLATES:
                out.append((t.format(g=g), loc, cc))
        for q in GENERIC:
            out.append((q, loc, cc))
    return out


# Retailers, aggregators, socials, trad publishers, media — never a lead.
PLATFORM = re.compile(
    r"(^|\.)("
    r"amazon|amzn|goodreads|bookbub|kobo|barnesandnoble|bn|audible|apple|itunes|"
    r"smashwords|draft2digital|books2read|ingramspark|lulu|blurb|bookbaby|"
    r"waterstones|booktopia|whsmith|foyles|indigo|chapters|thriftbooks|abebooks|"
    r"alibris|betterworldbooks|bookdepository|wordery|blackwells|hive|"
    r"facebook|instagram|twitter|x|threads|tiktok|youtube|pinterest|linkedin|"
    r"reddit|tumblr|medium|substack|patreon|kickstarter|indiegogo|discord|"
    r"wikipedia|wikimedia|fandom|quora|yelp|tripadvisor|glassdoor|indeed|"
    r"wordpress|blogspot|blogger|wix|weebly|squarespace|godaddy|shopify|etsy|"
    r"ebay|walmart|target|costco|google|bing|yahoo|msn|duckduckgo|"
    r"penguinrandomhouse|penguin|randomhouse|harpercollins|simonandschuster|"
    r"hachette|hachettebookgroup|macmillan|scholastic|bloomsbury|faber|"
    r"quarto|wiley|pearson|springer|elsevier|oup|cambridge|"
    r"publishersweekly|kirkusreviews|booklistonline|libraryjournal|"
    r"nytimes|guardian|telegraph|bbc|cnn|forbes|entrepreneur|inc|businessinsider|"
    r"huffpost|buzzfeed|vulture|theverge|wired|writersdigest|janefriedman|"
    r"reedsy|scribophile|wattpad|inkitt|royalroad|archiveofourown|fanfiction|"
    r"librarything|storygraph|bookshop|bookriot|epicreads|netgalley|"
    r"gov|nih|nasa|ac|edu"
    r")\.",
    re.I,
)
BAD_TLD = re.compile(r"\.(gov|edu|mil|gov\.uk|ac\.uk|edu\.au|gov\.au)$", re.I)


def keep(host):
    if not host or "." not in host:
        return False
    if BAD_TLD.search(host) or PLATFORM.search("." + host):
        return False
    if maps.JUNK.search(host):
        return False
    # long subdomain chains are almost always platforms / CDNs
    if host.count(".") > 3:
        return False
    return True


def parse(items):
    out = []
    for it in items or []:
        if it.get("type") != "organic":
            continue
        url = it.get("url") or ""
        try:
            host = urllib.parse.urlparse(url).netloc.lower()
        except Exception:
            continue
        host = host[4:] if host.startswith("www.") else host
        if keep(host):
            out.append((host, it.get("rank_absolute") or 0))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--set", default="1", choices=["1", "2", "3", "all"])
    args = ap.parse_args()

    queries = {"1": build_queries, "2": build_queries2, "3": build_queries3,
               "all": lambda: build_queries() + build_queries2() + build_queries3()
               }[args.set]()
    print(f"plan: {len(queries)} queries x top-{DEPTH} "
          f"= est ${len(queries) * COST_PER_QUERY:.2f}")
    if args.dry_run:
        for q in queries[:8]:
            print("  ", q)
        return

    hdr = maps.auth_header(maps.env())
    store = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    todo = [q for q in queries if f"{q[2]}|{q[0]}" not in store]
    if args.limit:
        todo = todo[: args.limit]

    bal = maps.balance(hdr)
    need = len(todo) * COST_PER_QUERY
    print(f"{len(store)} cached, {len(todo)} to fetch | balance ${bal:.2f}, "
          f"need ~${need:.2f}")
    if need > bal:
        sys.exit("insufficient balance")

    done, spent = [0], [0.0]

    def run(item):
        kw, loc, cc = item
        try:
            resp = maps.post("/serp/google/organic/live/advanced", [{
                "keyword": kw, "location_name": loc, "language_code": "en",
                "depth": DEPTH}], hdr)
            task = (resp.get("tasks") or [{}])[0]
            res = (task.get("result") or [{}])[0] if task.get("result") else {}
            hits = parse(res.get("items"))
            cost = resp.get("cost") or 0.0
        except Exception as ex:
            hits, cost = [], 0.0
            print(f"  FAIL [{kw[:40]}]: {str(ex)[:60]}")
        with _lock:
            store[f"{cc}|{kw}"] = {"country": cc, "hits": hits}
            spent[0] += cost
            done[0] += 1
            if done[0] % 25 == 0:
                PROGRESS.write_text(json.dumps(store))
                uniq = {h[0] for v in store.values() for h in v["hits"]}
                print(f"  {done[0]}/{len(todo)} | {len(uniq)} unique domains | "
                      f"${spent[0]:.2f}", flush=True)

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(run, todo))
    PROGRESS.write_text(json.dumps(store))

    seen = {}
    for key, v in store.items():
        q = key.split("|", 1)[1]
        for host, rank in v["hits"]:
            rec = seen.setdefault(host, {"domain": host, "countries": [],
                                         "queries": 0, "best_rank": 999})
            if v["country"] not in rec["countries"]:
                rec["countries"].append(v["country"])
            rec["queries"] += 1
            rec["best_rank"] = min(rec["best_rank"], rank or 999)
            rec.setdefault("sample_query", q)
    with OUT.open("w", encoding="utf-8") as f:
        for r in seen.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n{len(seen)} unique domains -> {OUT} | cost ${spent[0]:.2f}")


if __name__ == "__main__":
    main()
