# Outreach lead pipeline — Daniks.AI White-Label (Amazon PPC agencies)

> **AU vertical** (2026-08-10): dedicated Australia cut for the `[AU]` campaign
> clone (id `83755a44-…`, Sydney TZ). `scripts/au1_build_csv.py` merges the
> AU rows from layers 1-3 masters with fresh web-research domains
> (`data/au_agencies.jsonl`, harvested via `2b_email_harvest.py`) →
> `data/instantly_AU.csv` (176 contacts / 103 domains). Import manually.

> **UK vertical** (2026-08-11): dedicated Great Britain cut for the `[UK]`
> campaign clone (id `a127207a-…`, TZ `Europe/Isle_of_Man` — `Europe/London` is
> rejected by Instantly's timezone enum). `scripts/uk1_build_csv.py` merges the
> GB rows of `data/instantly_all_master.csv` with fresh web-research domains
> (`data/uk_agencies.jsonl`) and the deep-harvest crack of GB domains that had
> no email at master-build time (`data/uk_domains_noemail.txt` → `2c_deep_harvest.py`)
> → `data/instantly_UK.csv` (228 contacts / 190 domains). Unlike the AU builder
> this one also drops addresses that FAILED the July verification run (109 of
> them), comparing `emails_to_verify.csv` against `verified/verified_*.csv`.
> 214 leads live in the campaign; 14 were skipped as already-contacted in `[US]`.

> **Prep-center vertical** (2026-08-10): separate segment targeting FBA prep
> centers / 3PLs with the 25%-lifetime affiliate offer. Scripts
> `prep1_directories.py` (free directory scrape: selleressentials + hopstack +
> rocketsource) → `2b_email_harvest.py --domains-file data/prep_domains.txt` →
> `prep2_build_instantly_csv.py` (dedupes vs agency masters). Output:
> `data/instantly_segments_prep/instantly_PREP-{US,INTL,CN}.csv`.
> Sequence draft: `sequences/prep-centers-en.md`. PREP-CN pairs with the
> WeChat/China motion — don't import into the EN campaign blindly.
>
> **Round 2** (2026-08-11, +94 leads → 264 in campaign `61e094c8-…`):
> `prep1_directories.py` → `prep3_ddg_serp.py` / `prep3b_bing_serp.py`
> (free SERP sweeps; both get rate-limited fast) → `prep4_normalize_r2.py`
> (merges ShipHype + RocketSource + fbaprepfinder + prepmarketplace +
> sermondo + SERP, dedupes vs round 1) → `2b_email_harvest.py` →
> `2c_deep_harvest.py` on the no-email remainder → `prep5_build_r2_csv.py`.
> ShipHype (403) and RocketSource (429) block urllib — those two lists were
> pulled through the Claude-in-Chrome browser and saved as
> `data/prep_r2_shiphype_domains.txt` / `prep_r2_rocketsource.txt`.
> `prep6_gmaps.py` (Apify Maps sweep) is written but refuses to run: the
> Apify cycle is spent ($0.08 of $5 left), DataForSEO is at −$0.03.
>
> **Niche ceiling:** 526 unique prep domains found, only 244 publish an
> email. The worldwide FBA-prep niche is ~600-900 companies with websites,
> so volume targets in the thousands need either an adjacent segment
> (general 3PL / e-commerce fulfillment, not Amazon-specific) or a funded
> Maps/SERP API.

> **CPA / e-commerce accountant vertical** (2026-08-10): same 25%-lifetime
> affiliate offer to accounting firms specializing in Amazon/e-commerce books
> (trusted advisors; clients complain to them about ad spend). Scripts
> `cpa1_directories.py` (free scrape: A2X ecommerce-accountant directory +
> Link My Books experts; 107 firms US/GB/AU-heavy) →
> `2b_email_harvest.py --domains-file data/cpa_domains.txt` →
> `cpa2_build_instantly_csv.py` (caps 3 emails/firm, dedupes vs agency+prep
> masters). Output: `data/instantly_segments_cpa/instantly_CPA-{US,GB,INTL}.csv`
> (69 rows / 54 firms). Sequence draft: `sequences/accountants-en.md`.
> Niche is finite — this can share a campaign with prep centers (different
> Step-1 copy per segment) to save mailbox capacity.

> **Aggregator / brand-holdco ABM** (2026-08-10): NOT an Instantly motion —
> ~50-100 named accounts, personal 1:1 emails (Agency plan / volume pricing
> pitch). See `outreach/aggregators/`.

Collects and enriches Amazon-PPC-agency contacts to feed the Instantly cold
campaign «Daniks.AI White Label — PPC Agencies». Numbers game: the niche is
finite (~10-20k agencies worldwide), so we go for full coverage of the niche +
several personas per agency + 5 touches, not "hundreds of thousands of random
addresses."

## Layers (lead sources)

| Layer | Source | Tool | Status |
|-------|--------|------|--------|
| 1 | Amazon Ads Partner Directory (~3,615 verified partners) | Apify `lexis-solutions/amazon-ads-partner-directory-scraper` | **done** (3,507 domains, 2,799 contacts) |
| 2 | Google Maps, ~65 cities × localized queries (127 searches) | DataForSEO `serp/google/maps` via `5b_gmaps_dataforseo.py` (Apify `5_gmaps_scrape.py` kept as fallback) | **done** (1,739 places → 627 new agencies → 559 contacts, cost $0.24) |
| 3 | Google SERP agency domains × languages × geo | DataForSEO `serp/google/organic` via `7b_serp_dataforseo.py` (Apify `7_serp_scrape.py` kept as fallback) | **done** (2,141 organic → 290 new agencies → 252 contacts, cost $0.38) |
| 4 | Directories (Clutch, DesignRush, Sortlist, G2, SPN) | mixed | later |

## Enrichment pipeline (shared)

```
raw actor output
  → 1_normalize_layer1.py     dedupe by domain (+ suppress already-contacted) → agencies.jsonl + domains.txt
  → 2_contact_scrape.py       Apify contact-info-scraper → emails + socials
  → 4_apollo_enrich.py        (optional) Apollo org-enrich → phone/LinkedIn/size  [FREE plan = firmographics only]
  → 3_build_instantly_csv.py  merge → dedupe emails → per-segment Instantly CSVs
```

## Budget reality (Apify Starter, BRONZE tier)

- Plan: $29/mo included, **hard overage stop at $50/cycle**.
- Contact scraper ≈ $0.002/page (~$0.008/site). Directory scrape ≈ $0.005/partner.
- **One cycle fits Layer 1 end-to-end** (~$18 scrape + ~$25 contacts ≈ $43).
  Layers 2-3 go to the next cycle (or raise the cap). This matches the
  "send slowly" posture — 6-8 warmed mailboxes can't burn a bigger list fast.

## Apollo caveat

Connected account is **free plan**. Only `/organizations/enrich` works (company
firmographics). People/email endpoints need a paid plan (API_INACCESSIBLE on
free). So Apollo here = company context, not decision-maker emails. Emails come
from the Apify contact scraper. Upgrading Apollo (~$49-99/mo) is a separate
user decision that would unlock named founder/CEO verified emails.

## Data files (data/, git-ignored)

- `layer1_amazon_partners_raw.json` — raw actor dump
- `layer1_agencies.jsonl` / `layer1_domains.txt` — normalized
- `layer1_contacts_raw.json` — contact-scraper output
- `apollo_orgs.json` — firmographic cache
- `instantly_layer1_master.csv` + `instantly_segments/*.csv` — import-ready
- `layer2_gmaps_raw/gmaps_<lang>.json` — raw Google-Maps batches (layer 2)
- `layer2_agencies.jsonl` / `layer2_domains.txt` — layer 2 normalized (deduped vs layer 1)
- `instantly_layer2_master.csv` + `instantly_segments_layer2/*.csv` — layer 2 import-ready
- `layer3_serp_raw/serp_<country>_<lang>.json` — raw Google-SERP batches (layer 3)
- `layer3_agencies.jsonl` / `layer3_domains.txt` — layer 3 normalized (deduped vs layers 1-2)
- `instantly_layer3_master.csv` + `instantly_segments_layer3/*.csv` — layer 3 import-ready
- `suppress_domains.txt` — domains already in a live campaign (never re-mail)

## Run order

```bash
python3 outreach/scripts/1_normalize_layer1.py outreach/data/layer1_amazon_partners_raw.json
python3 outreach/scripts/2_contact_scrape.py           # watch Apify credit
python3 outreach/scripts/4_apollo_enrich.py --limit 500 # optional, free
python3 outreach/scripts/3_build_instantly_csv.py
```

## Layer 2 run order (Google Maps) — DONE via DataForSEO

Apify was capped ($29 hard limit hit), so Layer 2 ran through **DataForSEO's
Google-Maps SERP** instead (`5b_gmaps_dataforseo.py`) at ~$0.002/search — the
whole layer cost **$0.24** vs the $10-25 Apify estimate, and DataForSEO was
already funded. City is put in the keyword, country as `location_name`, so no
per-city location-DB mapping is needed. Note: the live/advanced endpoint only
reliably runs ~1 task per POST, so the scraper sends one keyword per request and
`--retry-empty` re-fetches any that came back throttled/empty.

```bash
python3 outreach/scripts/5b_gmaps_dataforseo.py --dry-run   # plan + cost, $0
python3 outreach/scripts/5b_gmaps_dataforseo.py             # 127 searches, ~$0.25
python3 outreach/scripts/5b_gmaps_dataforseo.py --retry-empty  # redo throttled/empty ones
python3 outreach/scripts/6_normalize_layer2.py             # dedupe vs layer 1 + suppress
python3 outreach/scripts/2b_email_harvest.py --domains-file outreach/data/layer2_domains.txt  # $0
python3 outreach/scripts/3_build_instantly_csv.py --layer 2
# → instantly_layer2_master.csv + instantly_segments_layer2/*.csv (emails deduped vs layer 1)
```

Fallback (Apify actor, if DataForSEO balance runs out): raise **Max monthly
usage** in Apify Console → Billing → Limits, then run `5_gmaps_scrape.py`
(same `6→2b→3` steps after). `_gmaps_progress.json` caches finished batches.

## Layer 3 run order (Google SERP) — DONE via DataForSEO

Same DataForSEO pivot as layer 2: Apify was capped, so the widest layer ran
through **DataForSEO's organic SERP** (`7b_serp_dataforseo.py`) at ~$0.0035/query
— whole layer cost **$0.38**. Localized "amazon ppc agency" query sets across 22
countries (country = `location_name`, language = `language_code`). Same
live/advanced gotcha (one task per POST + `--retry-empty`). The normalizer drops
the directories / listicles / SaaS tools that clog these SERPs and dedupes
against layers 1-2. SERP skews to long-tail non-English shops the directory and
Maps missed (JP/ES/IT/AT/BR heavy).

```bash
python3 outreach/scripts/7b_serp_dataforseo.py --dry-run   # plan + cost, $0
python3 outreach/scripts/7b_serp_dataforseo.py             # 115 queries, ~$0.40
python3 outreach/scripts/7b_serp_dataforseo.py --retry-empty  # redo throttled/empty ones
python3 outreach/scripts/8_normalize_layer3.py            # dedupe vs layers 1-2 + suppress
python3 outreach/scripts/2b_email_harvest.py --domains-file outreach/data/layer3_domains.txt  # $0
python3 outreach/scripts/3_build_instantly_csv.py --layer 3
# → instantly_layer3_master.csv + instantly_segments_layer3/*.csv (emails deduped vs layers 1-2)
```

Fallback (Apify actor): raise **Max monthly usage** in Apify Console → Billing →
Limits, then run `7_serp_scrape.py` (same `8→2b→3` steps after).
`_serp_progress.json` caches finished country batches.
