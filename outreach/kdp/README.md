# KDP outreach — lead collection

## Round 7 (2026-08-11) — GERMANY / DACH, three new campaigns LAUNCHED

First non-English KDP round. Six research agents swept the German-language book
market (Amazon-Ads/Buchmarketing agencies, Selfpublishing-Dienstleister, KDP
coaches & influencers, indie Verlage, low-content/planner brands + ghostwriting,
book PR/promo & eBook-deal newsletters) → 113 orgs → 109 domains after
suppression → `harvest_deep.py` → **84 clean leads after QA**, all imported and
**launched (Active) 2026-08-11**.

Split by which offer actually fits (same three-way logic as r4):

| Bucket | Leads | Campaign | Letter |
|---|---|---|---|
| Client-managing services (Amazon-Ads agencies, Selfpublishing-Dienstleister, ghostwriting) | 39 | «Daniks.AI KDP — Buchmarketing Services & Agenturen (DE)» `0e274b9e-f0ac-4368-8846-57d391ed4aaf` | white-label $999 |
| Own-catalog publishers (genre presses, Kinderbuch, planner/Rätsel brands) | 21 | «Daniks.AI KDP — Indie Verlage Direct (DE)» `22a8ff19-8d21-41e3-803a-476f41edc8ea` | direct: 2-week A/B, from $49 |
| Partners (KDP coaches/podcasters, promo services, eBook-deal newsletters) | 24 | «Daniks.AI Partnerprogramm — KDP Coaches & Buch-Promo (DE)» `306ed5e9-ba78-42a9-878f-62e285644100` | 25% lifetime |

Sequences are written in German (Sie-form), not literally translated:
`sequence-kdp-services-de.md`, `sequence-kdp-publishers-direct-de.md`,
`sequence-kdp-partners-de.md`. Same cadence as EN (services/publishers 5 steps
3/4/5/4, partners 4 steps 3/4/5), A/B in step 1, zero links in cold mails,
stop-on-reply, tracking off, 30/day, 8 senders daniel@+eric@ (services,
publishers) / 4 senders nick@ (partners).

**Schedule gotcha:** Mon–Fri 09:00–18:00 **`Arctic/Longyearbyen`** — that is
Instantly's identifier for Central European time. `Europe/Berlin` is rejected
with `400 timezone must be equal to one of the allowed values`. The pre-existing
DE campaigns use the same value.

Build pipeline (`build_kdp_de_csv.py` imports `build_kdp_csv.py` for suppression):

```
agents → data/de/raw_{agencies,services,lowcontent_ghost,publishers,promo,influencers}.jsonl
python3 outreach/kdp/build_kdp_de_csv.py --stage domains   # → data/de/kdp_de_domains.txt (109)
python3 outreach/kdp/harvest_deep.py --domains-file outreach/kdp/data/de/kdp_de_domains.txt
python3 outreach/kdp/build_kdp_de_csv.py --stage csv       # → three data/de/instantly_import_*.csv
```

QA dropped or fixed before import: `hellogeroz@gmail.com` (autoren-partner.de,
off-domain gmail), `info@flyeralarm-trading.com` (Cupcakes & Kisses — their
printer, not the brand), `produktsicherheit@droemer-knaur.de` (Groh — parent
group's product-safety inbox), `max@mustermann.de` placeholder, a ROT13
address at lowcontentkurs.de, and the concatenation artifact
`19-519info@singliesel.dewww.singliesel.de` → `info@singliesel.de`. Coaches who
also sell services (Gaiswinkler, Nomad, Autorenkompass, Schlienz) were routed to
the partner letter rather than white-label.

Workspace dedup caught one silent overlap at import: `kontakt@carow-verlag.de`
already sits in «Amazon Sellers [DE Companies]», so 84 of 85 leads went in.
Suppressed as already contacted: sinaveria.de, selfpublisherbibel.de,
nomad-publishing.de, nice-publishing.de.

**Open:** 19 DACH domains yielded no email (`data/de/no_email_de.txt`). They were
harvested with `harvest_deep.py` before r6's `harvest_crawl.py` existed — that
crawler is the better tool and should be re-run over them before anyone resorts
to contact forms.

---

## Round 6 (2026-08-10) — full site crawl

`harvest_deep.py` still guessed URLs, so it missed addresses published on
non-standard pages (Celebrate Lit's was on `/19-2/`, a services page).
`harvest_crawl.py` instead enumerates the site's own internal links, scores them
(contact > about > team > submissions > services > faq > press), reads the best
14 pages, and additionally parses **JSON-LD / schema.org** and inline JSON
(`__NEXT_DATA__`, `__NUXT__`, Wix warmup) where many sites keep the address.

Run over 195 never-contacted, reachable domains: **113 yielded an email.**

Split of that yield:
* **75 are `.de` / `.at`** — they belong to the pre-existing **German (DACH) KDP
  round**, not to the English campaigns. Left alone.
* **26 English** → **12 after QA** → imported: 5 services, 4 partners, 3 publishers.
* 72 English domains still have no address at all.

QA again removed the usual third-party noise (lit agencies, web designers,
`john@doe.com`, `info@simprosys.com`) — the same 14-address blocklist as r5.
Two useful recoveries: Ghostwriters Avenue and The Writing Room, whose contact
forms could not be submitted (phone-gated / lazy reCAPTCHA), turned out to
publish `sales@` and `info@` addresses deeper in the site.

> ⚠️ **Note for whoever owns the German round:** `harvest_deep.py` and
> `classify_forms.py` already existed in this folder from that earlier session
> and were **overwritten** by this session's versions. The data they had
> produced (`data/kdp_contacts_deep.json`, 270 domains incl. the German ones)
> is intact and `build_kdp_de_csv.py` still reads it fine — only the two script
> sources were replaced.

---

## Round 5 (2026-08-10) — deep re-harvest of the domains v1 missed

The shallow `harvest_kdp.py` only fetched the homepage + 2 link-matched pages
and could not read Cloudflare-obfuscated addresses, so **161 of the 297 r4
domains yielded no email**. `harvest_deep.py` re-ran them with:
Cloudflare `data-cfemail` decoding, `[at]`/`[dot]` de-obfuscation, direct probes
of 18 common contact paths, a wider link-hint regex, 6 pages/domain, and a
`hasForm` flag for routing the leftovers.

Result: **58 domains yielded an email → 43 clean leads after QA**, imported
2026-08-10 into the matching campaign by the same three-way split:

| Bucket | Leads | Campaign |
|---|---|---|
| Client-managing services | 20 | services `58f661bd…` |
| Adjacent partners | 15 | partners `3a49143f…` |
| Own-catalog publishers | 8 | Indie Publishers Direct `9c35c610…` |

QA dropped 15 third-party/junk addresses the scraper picked up off client and
credit links (lit agencies, web designers, PR reps, `john@doe.com`) and decoded
a second ROT13-obfuscated address (Fisher King → `submissions@`).

**Still unreachable by email: 118 orgs** — see `data/no_email_remaining.txt`
(58 have a contact form, 21 have a LinkedIn page, 24 sites are dead/unreachable).
These need manual form/LinkedIn follow-up; not yet actioned.

---

## Round 4 (2026-08-10) — big sweep, THREE-WAY split by offer fit

137 leads imported 2026-08-10 after splitting by which letter actually fits
(9 research agents, 297 new domains harvested, 456-domain suppression):

| Bucket | Leads | Campaign | Letter |
|---|---|---|---|
| Client-managing services (ads agencies, ghostwriting, VA/PA agencies, intl assisted/hybrid publishers) | 67 | services `58f661bd…` (Active) | white-label $999 |
| Adjacent partners (book/author coaches, blog-tour + promo services, review services, cover/format/audio/website/translation studios) | 39 | influencers `3a49143f…` (Active) | 25% lifetime partner |
| Influencers (long-tail KDP educators/podcasters) | 8 | influencers `3a49143f…` (Active) | 25% lifetime partner |
| **Own-catalog publishers** (digital-first genre presses, nonfiction/children's indies, planner/coloring/workbook brands) | 23 | **NEW** «Daniks.AI KDP — Indie Publishers Direct (EN)» `9c35c610-01fb-4109-965e-1702490e8fbc` | direct offer: A/B trial 2 wks, $49/$129, target ACoS |

New campaign built 2026-08-10: 5 steps (A/B in step 1), pauses 3/4/5/4, ET
Mon-Fri 9-18, 8 senders (daniel@+eric@ × 4 daniks domains), stop-on-reply,
open tracking off, 30/day. Sequence source: `sequence-kdp-publishers-direct-en.md`.
**LAUNCHED (Active) 2026-08-10** on the user's explicit go-ahead. Pre-launch
reload check caught one silent loss: the step-4→5 delay had reverted to 1 day
(the inline triple-click edit hadn't stuck) — fixed to 4 and re-saved. All six
email bodies, senders and schedule verified present after reload.

Messaging: KDP case ACoS 46%→21% + sales x2 (canonical facts 2026-08).
Quality pass dropped 14 junk/third-party emails (ROT13-obfuscated Post Hill
fixed to contact@; lit-agency/webmaster/publicist addresses dropped) and 2
hidden same-org dups (Blue Balloon=Ballast, Author Assistants Academy=NFAA).
~22 influencers/orgs without harvestable emails stay in `round4_raw/`.

---

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
