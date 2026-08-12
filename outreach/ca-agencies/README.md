# Canada agency outreach — [CA] Daniks.AI White Label

Instantly campaign **`[CA] Daniks.AI White Label — PPC Agencies`**
(`f0eb6ed7-3cd9-4465-9fe3-c9ec5fc456ca`), Active since 2026-08-10. Cloned from
the live [US] campaign, so it inherits the 5-step EN white-label sequence
(A/B on step 1, pauses 3/4/5/4), the ET business-hours schedule and the six
`daniel@` / `eric@` sending mailboxes.

## Round 1 — Amazon-specific agencies (2026-08-10)

Target: Canadian **Amazon** PPC / marketplace agencies only.

| Source | Firms |
|---|---|
| Clutch `ca/agencies/ppc` Amazon-advertising category (4 pages) | 71 |
| Sortlist / DesignRush / GoodFirms / Semrush partner listings | 39 |
| City + listicle web search (15 cities) | 31 |
| Quebec FR agencies (`agence amazon`, `publicité Amazon`) | 17 |

118 unique firms → 78 domains not already in layers 1-3 → harvested with
`2b_email_harvest.py`, then a research agent chased 15 form-only sites (12 hit).
Merged with the 108 CA addresses that were sitting in the layer-1..3 masters
(previously mis-segmented as `EN-US`).

Import dialog said 153 contacts; **114 actually landed** — Instantly's
workspace-wide dedup silently dropped the rest. Nine CA leads that were queued
in [US] were moved over first (Move → Move to campaign, Copy off).

## Round 2 — broadened ICP (2026-08-10)

The pure-Amazon niche in Canada is exhausted at ~118 firms, so round 2 targets
**all Canadian digital / PPC / ecommerce agencies** — the white-label offer fits
any shop running paid media for ecommerce clients.

| Source | Firms |
|---|---|
| Clutch PPC + digital-marketing + ecommerce, Canada (all pages) | 221 |
| DesignRush + Sortlist PPC/digital/ecommerce Canada | 189 |
| City listicles, 20+ cities incl. Atlantic + Prairies | 129 |
| Shopify / DTC / retail-media ecommerce agencies | 85 |

499 unique firms → **416 new domains** → `2b_email_harvest.py` (255 hits) then
`2c_deep_harvest.py` on the remainder → **267 leads imported**.

Excluded as non-Canadian or duplicate orgs: directiveconsulting.com,
insidea.com, wiserbrand.com, whitespark.ca, tech2globe.ca (same org as
tech2globe.com, already contacted).

## Round 3-5 — Quebec, partner directories, Shopify/ecommerce (2026-08-10)

| Wave | Firms | New domains | Leads |
|---|---|---|---|
| Quebec / francophone directories + listicles | 134 | 110 | 79 imported |
| Digital Agency Network (8 Canadian city pages) + retail/DTC | 172 | 170 | 118 **queued** |
| Google Partners Canada + Shopify/Klaviyo partners | 350+ | 273 | 187 **queued** |

Big creative/brand shops were dropped from the Quebec and retail waves — Sid Lee,
LG2, Cossette, DDB, Publicis, Tank Worldwide, Zulu Alpha Kilo and similar run
brand campaigns, not ecommerce paid media, so the white-label offer misfits.

## BLOCKED: workspace contact quota is full

The Instantly plan (Hyper Growth, $97/mo) caps **uploaded contacts at 25,000** and
the workspace sits at **24,969** — 31 slots left, against 305 leads ready to go.
The import dialog replaces its button with "Upgrade plan" once the list exceeds
the remaining quota, so the last two waves could not be loaded.

Ready-to-paste file: `outreach/data/instantly_CA_QUEUED_bulk.txt` (305 lines,
already deduped against everything imported so far). Paste it into
Add Leads → Emails Manually once quota exists.

Three ways to free room, all needing a decision from the account owner:

1. **Buy a contact add-on** on the current plan (cheapest if only ~1k more slots
   are needed).
2. **Upgrade to Light Speed** ($358/mo) — 100,000 contacts, only worth it if
   several verticals keep scaling.
3. **Delete leads from finished campaigns** — the completed [DE] (21,706 sent)
   and [ES] (6,599 sent) Amazon-seller campaigns hold most of the 25,000. This
   frees space at no cost but discards their lead history, and those numbers
   feed other verticals' reporting, so it should not be done casually.

## Cleaning rules (apply before every import)

The harvesters produce three recurring defects — the build step filters them:

- `%20`-prefixed addresses (URL-encoded space picked out of `href`s).
- Wrong-department mailboxes: `careers@`, `jobs@`, `hr@`, `press@`, `billing@`,
  `data@`, `proposals@`, `techsupport@`.
- Fake first names generated from greeting locals — `Bonjour`, `Letschat`,
  `Sayhi`, `Spicy`, `Grow`, `Join`, `Maven`, `Contactus`, `Clientcare`,
  `Imagine`, `Engage`, `Mailbox`, `Vancouver`. These must fall back to `there`
  so the copy reads "Hi there," rather than "Hi Spicy,".

Two addresses max per domain, on-domain only, ranked personal-name first.

## Files (git-ignored — PII)

```
outreach/data/ca_research_{clutch,directories,google,quebec}.json   round 1 raw
outreach/data/ca_new_agencies.json  ca_new_domains.txt              round 1 new
outreach/data/instantly_CA_master.csv  instantly_CA_bulk.txt        round 1 import
outreach/data/ca_r2_{clutch,directories,listicles,ecom}.json        round 2 raw
outreach/data/ca_r2_agencies.json  ca_r2_domains.txt                round 2 new
outreach/data/instantly_CA_r{2..5}_master.csv + _bulk.txt          rounds 2-5
outreach/data/instantly_CA_QUEUED_bulk.txt                          305 leads awaiting quota
outreach/data/ca_all_domains.txt                                    dedup key for round 3
```

## Notes

- Lead verification is skipped (0 Instantly credits), so generic inboxes carry
  the usual 5-15% bounce risk.
- Bulk-insert-manually is the only import path that works from an automated
  browser session; the CSV uploader commits the first few rows then hangs.
- The campaign's lead counter is cached — verify an import by searching for
  specific addresses, not by reading the number.
