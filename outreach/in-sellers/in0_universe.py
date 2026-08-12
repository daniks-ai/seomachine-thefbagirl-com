#!/usr/bin/env python3
"""
India Amazon-seller lead build, stage 0: the domain universe.

Source is the Chrome UX Report top-1M origins *for India*
(github.com/zakird/crux-top-lists, data/country/in/<YYYYMM>.csv.gz) — a free,
traffic-ranked list of the sites Indians actually load. DataForSEO SERP would be
the alternative but the shared balance is empty, and this list is both larger
and unbiased by query wording.

Two tiers are written, both in traffic-rank order:
  in_universe.txt      every *.in host (the dense Indian tier)
  in_universe_com.txt  .com/.shop/.store/.online/.co/.site hosts — mixed
                       Indian/global, only worth crawling as a second wave
                       (the crawler's India signal sorts them out)

Institutional, media, marketplace and platform hosts are dropped here so the
crawler never spends a request on them.

Usage:
    python3 outreach/in-sellers/in0_universe.py
"""
import csv
import gzip
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SRC = DATA / "crux_in.csv.gz"
OUT_IN = DATA / "in_universe.txt"
OUT_COM = DATA / "in_universe_com.txt"

SECOND_TIER_TLD = (".com", ".shop", ".store", ".online", ".co", ".site",
                   ".net", ".biz", ".company", ".world", ".life", ".club")

INSTITUTIONAL = re.compile(
    r"\.(gov|nic|ac|edu|res|mil)\.in$|\.(gov|edu|mil)$|"
    r"(^|\.)(gov|police|court|university|college|school|hospital)\.", re.I)

BLOCK = re.compile(
    r"(^|\.)(amazon\.|amzn\.|flipkart|myntra|ajio|meesho|snapdeal|shopclues|"
    r"paytm|tatacliq|jiomart|bigbasket|blinkit|zepto|dunzo|nykaa|firstcry|"
    r"pepperfry|urbanladder|limeroad|craftsvilla|indiamart|tradeindia|"
    r"exportersindia|justdial|sulekha|quikr|olx|udaan|moglix|industrybuying|"
    r"alibaba|aliexpress|shein|temu|ebay|etsy|walmart|myshopify|shopify|"
    r"wix|squarespace|weebly|blogspot|wordpress|tumblr|medium|linktr|"
    r"google|gstatic|youtube|facebook|fbcdn|instagram|linkedin|twitter|"
    r"whatsapp|telegram|pinterest|reddit|quora|wikipedia|wikimedia|"
    r"cloudflare|akamai|fastly|jsdelivr|cdn|doubleclick|adservice|"
    r"scribd|slideshare|issuu|tripadvisor|makemytrip|goibibo|irctc|"
    r"zomato|swiggy|practo|naukri|shine\.com|monster|shiksha|collegedunia|"
    r"byjus|unacademy|vedantu|toppr|coursera|udemy|khanacademy|"
    r"timesofindia|indiatimes|economictimes|hindustantimes|ndtv|aajtak|"
    r"business-standard|livemint|thehindu|indianexpress|moneycontrol|"
    r"zeenews|zeebiz|financialexpress|news18|abplive|jagran|bhaskar|"
    r"amarujala|republicworld|firstpost|scroll\.in|thewire|theprint|"
    r"inc42|yourstory|techcrunch|gadgets360|91mobiles|smartprix|"
    r"cricbuzz|espncricinfo|hotstar|jiocinema|sonyliv|zee5|netflix|"
    r"pornhub|xvideos|xnxx|xhamster|bet365|dream11|rummy|casino|"
    r"tofler|zaubacorp|indiafilings|cleartax|vakilsearch|taxguru|"
    r"glassdoor|indeed|ambitionbox|foundit|apna\.co|"
    r"hdfc|icici|axisbank|sbi\.|kotak|paypal|razorpay|payu|billdesk|"
    r"github|stackoverflow|apple\.|microsoft|adobe|oracle|salesforce|"
    r"archive\.org|w3\.org|mozilla|whatsapp)", re.I)


def main():
    tier1, tier2 = [], []
    seen = set()
    with gzip.open(SRC, "rt") as f:
        r = csv.reader(f)
        next(r)
        for origin, _rank in r:
            h = origin.split("//")[-1].lower().strip("/")
            if not h or "." not in h or h in seen:
                continue
            seen.add(h)
            if h.startswith("www."):
                h = h[4:]
            if INSTITUTIONAL.search(h) or BLOCK.search(h):
                continue
            # skip deep subdomains of one host (blog.x.in, m.x.in ...) — the
            # apex is already in the list or will be reached by the crawler
            if h.count(".") > 2 and not h.endswith(".co.in"):
                continue
            if h.endswith(".in"):
                tier1.append(h)
            elif h.endswith(SECOND_TIER_TLD):
                tier2.append(h)
    OUT_IN.write_text("\n".join(dict.fromkeys(tier1)) + "\n")
    OUT_COM.write_text("\n".join(dict.fromkeys(tier2)) + "\n")
    print(f"tier1 (.in): {len(set(tier1))} -> {OUT_IN}")
    print(f"tier2 (.com etc): {len(set(tier2))} -> {OUT_COM}")


if __name__ == "__main__":
    main()
