# Amazon México sellers — direct outreach

Direct-to-seller cold outreach: Mexican sellers on **amazon.com.mx**, offering the
daniks.ai product (Amazon Ads autopilot — free 2-week A/B trial, from $49/mo).
Not the white-label/agency motion — this is the end-user seller offer.

## Assets

- `sequence-sellers-mx.md` — es-MX, 4 steps + reply handler + 2 A/B variants on step 1.
- `data/instantly_MX_SELLERS.csv` — validated, Instantly-ready leads (see status).
- `data/mx_sellers_raw.jsonl` — all confirmed MX-based sellers (business name +
  full address), the reusable asset even where no email was found.
- `data/mx_domains.jsonl` / `.txt` — discovered seller domains.
- `domain_discovery.py`, `build_mx_csv.py` — the enrichment + strict CSV builder.

## How leads are collected (free, no paid tools)

1. **Scrape amazon.com.mx in the in-app Browser pane** (real Chrome fingerprint —
   plain curl gets 503/captcha). A single foreground tab runs one JS loop that:
   - self-feeds ASINs by crawling `/gp/bestsellers/*` category pages,
   - fetches `/dp/<ASIN>`, extracts the seller via `id=sellerProfileTriggerId`,
   - fetches `/sp?seller=<ID>` **with an `Accept: text/html` header** (without it
     the endpoint returns a 152-byte JSON stub), parses «Nombre comercial» +
     «Dirección»; keeps sellers whose address country == `MX`.
   - Two tabs do NOT help: Chrome throttles background-tab timers to ~1/min, so
     only the single foreground tab runs at speed.
2. **Domain discovery** (`domain_discovery.py`): brand/legal-name → domain via
   guess (`.mx/.com.mx/.com`) + DuckDuckGo HTML search.
3. **Email harvest** (`../scripts/2b_email_harvest.py`) on discovered domains.
4. **Strict validation** (`build_mx_csv.py`): keeps an email only if the site
   corroborates the seller (email domain == seller domain, brand token overlaps,
   no placeholder/tracking junk). Protects the shared senders' reputation — no
   blind name-guess sends. Dedupes vs every existing Instantly master.

Yield (measured): ~30% of sellers seen are MX-based; ~34% of MX sellers convert to
one clean corroborated email. So ≈1 usable email per ~10 product pages scraped.

## Hard limit hit 2026-08-10

Amazon **rate-limited the residential IP** after sustained scraping (503/captcha on
every request). Collected 59 MX sellers → 19 validated emails before the wall.
Reaching 1000 verified emails needs either (a) the scrape spread over many
days/sessions with long cool-downs, (b) rotating IPs, or (c) a paid Amazon-seller
database. The pipeline is fully reusable — re-run the browser loop after cool-down,
append to `mx_sellers_raw.jsonl`, re-run `domain_discovery.py` → `2b_email_harvest.py`
→ `build_mx_csv.py`.
