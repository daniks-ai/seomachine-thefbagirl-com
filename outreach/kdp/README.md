# KDP outreach — lead collection

## Round 3 (2026-08-03) — IMPORTED into the existing Active campaigns 2026-08-03

Third wave, deduped against rounds 1-2 (`data/sent/*.csv` now holds all six
import CSVs) + all prior Daniks campaigns. Messaging context: KDP PPC autopilot
now has multiple success cases (low ACOS, significant sales lift).

| Segment | File | Leads |
|---|---|---|
| `kdp_ads_agency` (11) + `book_marketing` (32) + `publishing_services` (18) | `data/instantly_import_kdp_services_r3.csv` | 61 |
| `kdp_influencer` | `data/instantly_import_kdp_influencers_r3.csv` | 7 |

Round-3 coverage: genre-specific PR boutiques (romance/romantasy, children's,
Christian/faith-based, sci-fi/fantasy), UK literary PR (Midas, FMcM, Riot),
audiobook production/marketing (ACX), NZ/IE self-publishing services, ebook
promo newsletters (Book Cave, Booksends, ManyBooks, BookGorilla), next-tier
KDP influencers (low-content/puzzle-book creators, BookTok educators).
Geo: 32 US, 16 UK, 6 AU, 5 CA, 3 NZ, 1 IE.

Suppression caught cross-campaign dups (sellermetrics.app — agency campaign,
broadsidepr.com — Kimberly Burns r1). Manually dropped: placeholder emails
(ReadersMagnet `example@gmail.com`, YourChicGeek `j.doe@inbox.com`), off-domain
web-agency credit (Self-Publishing NZ), `hr@midaspr.co.uk` → `info@`.
Influencers researched but without harvestable email (Ivy Hang, BookBird/Yves
Lummer, Ben McQueeney, Shelby Leigh, Paul Teague, Sandra Nomoto, Daniel
Tortora, Rebecca Holman, Lainey Cameron, Tommy Swindali, Kim George, Lois
Hoffman) stay in `data/round3_raw/raw_influencers.jsonl` for contact-form/
LinkedIn follow-up. Verification skipped again (0 credits).

---

## Round 2 (2026-07-23) — IMPORTED into the existing Active campaigns 2026-07-23

Second wave, deduped against round 1 + all prior Daniks campaigns (suppression
now also reads `data/sent/*.csv` + `data/round1_domains.txt`):

| Segment | File | Leads |
|---|---|---|
| `kdp_ads_agency` (13) + `book_marketing` (37) + `publishing_services` (25) | `data/instantly_import_kdp_services_r2.csv` | 75 |
| `kdp_influencer` | `data/instantly_import_kdp_influencers_r2.csv` | 9 |

Round-2 coverage: deeper book-PR/publicity boutiques (incl. genre-specific),
hybrid publishers & assisted self-publishing (US/UK/CA/AU/NZ/IN/ZA/IE),
directory sweep (ALLi/Reedsy/Jane Friedman lists), next-tier KDP influencers.
Geo: 47 US, 12 UK, 7 AU, 4 CA, rest other EN markets.

Excluded as round-1 same-org duplicates: BooksGoSocial (=bgsauthors), Self-
Publishing School (=selfpublishing.com), Meryl Moss Media (=BookTrib), Bryan
Cohen (=Best Page Forward), Penny Sansevieri (=amarketingexpert), Ocean Reeve
(oceanreeve.com=oceanreevepublishing.com). Placeholder/off-domain emails
blacklisted in `build_kdp_csv.py` (`example@mail.com`, `you@company.com`, …).

Influencers without a public email (Ben Chinnock, Rags To Niches, Publish with
Ashley, Heart Breathings, M.K. Williams, Bethany Atazadeh, Author Revolution,
Russell Nohelty, Six Figure Author Experiment, Amy Harrop, Author Level Up,
Nick Stephenson, Romney Nelson, Derek Murphy, Karla Marie, Jane Friedman,
Nonfiction Authors Assoc, My Freedom Empire) stay in `raw_influencers.jsonl`
for contact-form/LinkedIn follow-up.

Round-1 files: import CSVs archived in `data/sent/`, raw JSONL in
`data/round1_raw/`, domain list in `data/round1_domains.txt`.

---

## Round 1 (2026-07-15) — imported, campaigns Active

Cold-outreach leads for the new daniks.ai KDP offering (Amazon Ads for books).
Collected via WebSearch fan-out (DataForSEO balance was negative, so no SERP
layer) + the zero-cost email harvester.

## Segments

| Segment | File | Leads | Who |
|---|---|---|---|
| `kdp_ads_agency` + `book_marketing` | `data/instantly_import_kdp_services.csv` | 79 | Agencies/services managing Amazon Ads or marketing for KDP authors & publishers — direct/white-label customers |
| `kdp_influencer` | `data/instantly_import_kdp_influencers.csv` | 14 | KDP YouTubers/course creators/podcasters — affiliate-partner angle (25% lifetime, as in FBA campaigns) |

Both CSVs are deduped against every prior Daniks campaign list
(`outreach/data/instantly_layer*_master.csv` + all `influencers-*` CSVs) — zero
overlap found (different niche).

## Pipeline

```
agents (WebSearch) → data/raw_{agencies,bookmarketing,influencers}.jsonl
python3 outreach/kdp/build_kdp_csv.py --stage domains   # → data/kdp_domains.txt (162 domains)
python3 outreach/kdp/harvest_kdp.py --workers 24        # $0, stdlib scraper → kdp_contacts_raw.json
python3 outreach/kdp/build_kdp_csv.py --stage csv       # → the two import CSVs
```

Harvest yield: 162 domains → 90 with ≥1 published email → 79 usable service
leads after junk filtering (sentry/wixpress, hex locals, `%20`-prefixes,
entity-truncated `nfo@` → `info@`).

## Notes / caveats

- Emails are scraped from public contact pages, mostly `info@`/`hello@` style —
  run them through Instantly's built-in verification on import before sending.
- Influencers without a published email (17 of 31 researched, incl. Dave
  Chesson/Kindlepreneur, Janet Margot, Ryan Hogue, David Gaughran, Nicholas
  Erik) are kept in `data/raw_influencers.jsonl` — reachable via site contact
  forms / LinkedIn, manual follow-up.
- Publishing.com (Mikkelsen twins) had an FTC settlement (Apr 2026, $1.5M,
  deceptive earnings claims) — consider excluding from partner outreach.
- Dropped as leads: BookBub, Reedsy (platforms), AuthorHouse (Author Solutions
  vanity brand).
- Sequences written 2026-07-15: `sequence-kdp-services-en.md` (5 steps, A/B,
  3/4/5/4-day pauses) and `sequence-kdp-partners-en.md` (4 steps, A/B, 3/4/5).
- Both Instantly campaigns BUILT and fully configured, **paused — launch is a
  manual user action**:
  - Services: campaign `58f661bd-2cdd-43ce-ba8c-cd908e0dea9c` (79 leads,
    8 senders daniel@/eric@ across 4 daniks domains, ET Mon-Fri 9-18, 30/day).
  - Influencers: campaign `3a49143f-900a-4ba7-8157-309960455ef4` (14 leads,
    4 senders nick@, same schedule, 30/day).
- Lead verification was skipped at import (0 Instantly credits; $9/mo upsell
  declined) — buy credits and re-verify, or accept some bounces.
- Reply handlers in the sequence files are for manual sends from Unibox.
