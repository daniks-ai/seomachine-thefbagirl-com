# Amazon UK sellers — direct outreach

Direct-to-seller cold outreach: GB-based sellers on **amazon.co.uk**, offering the
daniks.ai product (Amazon Ads autopilot — free 2-week A/B trial, from $49/mo).
Not the white-label/agency motion — this is the end-user seller offer.
UK clone of the `outreach/mx-sellers/` pipeline (see its README for full history).

## Assets

- `sequence-sellers-uk.md` — en-GB, 5 steps + reply handler + 2 A/B variants on step 1.
- `data/instantly_UK_SELLERS.csv` — validated, Instantly-ready leads.
- `data/uk_sellers_raw.jsonl` — all confirmed GB-based sellers (business name +
  full address), the reusable asset even where no email was found.
- `uk_domains.jsonl` / `.txt` — discovered seller domains.
- `domain_discovery.py`, `build_uk_csv.py` — enrichment + strict CSV builder.
- `browser_worker.js` — bounded scrape burst for the in-app Browser pane.
- `daily_collect.py` — orchestrates drain → domains → email harvest → CSV.

## How leads are collected (free, no paid tools)

1. **Scrape amazon.co.uk in the in-app Browser pane** (real Chrome fingerprint —
   plain curl gets 503/captcha). A single foreground tab runs one JS loop that:
   - self-feeds ASINs by crawling `/gp/bestsellers/*` category pages,
   - fetches `/dp/<ASIN>`, extracts the seller via `id=sellerProfileTriggerId`,
   - fetches `/sp?seller=<ID>` **with an `Accept: text/html` header** (without it
     the endpoint returns a tiny JSON stub), parses «Business Name» +
     «Business Address»; keeps sellers whose last address line == `GB`.
2. **Domain discovery** (`domain_discovery.py`): brand/legal-name → domain via
   guess (`.co.uk/.uk/.com`) + DuckDuckGo HTML search.
3. **Email harvest** (`../scripts/2b_email_harvest.py`) on discovered domains.
4. **Strict validation** (`build_uk_csv.py`): keeps an email only if the site
   corroborates the seller (email domain == seller domain, brand token overlaps,
   no placeholder/tracking junk). Dedupes vs every existing Instantly master.

## Ops notes

- Same IP-throttle limits as MX: bounded bursts only (worker stops at 40 new GB
  sellers / 4 captchas / 25 min). Amazon re-throttles the residential IP on
  sustained scraping; keep the pacing and stop conditions.
- GB yield on amazon.co.uk bestsellers is much higher than MX yield was on
  amazon.com.mx (many domestic sellers vs CN-dominated MX marketplace).
