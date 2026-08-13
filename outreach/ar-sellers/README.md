# Argentina — outreach vertical

Argentine lead build for daniks.ai, split into two segments with two different
offers, in **es-AR (voseo)**.

## Read this first: Argentina has no Amazon marketplace

There is no `amazon.com.ar`. Amazon does not operate a marketplace in Argentina.
That single fact shapes everything here:

* **The MX/UK playbook does not port.** `mx-sellers/` and `uk-sellers/` work by
  crawling the local marketplace and keeping sellers whose seller-profile address
  country matches. With no local marketplace there is nothing to crawl, and
  filtering `amazon.com` for AR-based sellers is a needle-in-haystack scrape of a
  US-sized catalogue.
* **An Argentine "Amazon seller" is an exporter.** They sell on `amazon.com`, in
  USD, to US customers. All copy is written from that angle — exporting, dollars,
  the US market — never "tu tienda de Amazon Argentina".
* **The Amazon-native population in Argentina is genuinely small.** The Google
  Maps sweep across 52 cities × 4 Amazon-explicit queries returned **9** business
  domains that mention Amazon at all. That is the real size of the niche, not a
  collection failure. Volume therefore comes from the adjacent, verifiable
  population: Argentine e-commerce/performance agencies and online brands.

Anyone asked to "get more Argentine Amazon sellers" should read the paragraph
above before spending money on it.

## Segments

| Segment | Who | Offer | Sequence |
|---|---|---|---|
| `AR-AGENCIES` | agencies, consultancies, marketplace/performance shops | partner **25% lifetime** (USD), Agency Plan US$999/mo flat from step 3 | `sequence-agencias-ar.md` |
| `AR-SELLERS` | brands, manufacturers, importers, exporters, online retailers | product: free 2-week A/B trial, from US$49/mo | `sequence-sellers-ar.md` |

The agency sequence leads with the affiliate, not the white-label, on purpose:
most Argentine agencies live on Mercado Libre and local clients, so US$999/mo for
an Amazon roster asks the majority for something they cannot use. The 25%
recurring commission asks them for nothing but an introduction — **and it pays in
dollars**, which in Argentina is an argument by itself.

## Pipeline

```bash
python3 outreach/ar-sellers/ar1_dfs_maps.py --dry-run   # plan + cost
python3 outreach/ar-sellers/ar1_dfs_maps.py             # Maps, 756 searches
python3 outreach/ar-sellers/ar2_dfs_serp.py             # organic SERP, 50 queries
python3 outreach/ar-sellers/ar7_cace.py                 # CACE chamber directory (free)
python3 outreach/ar-sellers/ar3_normalize.py            # merge + tier + suppress
python3 outreach/ar-sellers/ar_harvest.py               # 2b then 2c, private cache
python3 outreach/ar-sellers/ar4_geo_check.py            # prove each domain is Argentine
python3 outreach/ar-sellers/ar5_build_csv.py            # -> instantly_AR_*.csv
python3 outreach/ar-sellers/ar6_build_sequences.py      # md -> Instantly sequences JSON
```

### Layer notes

* **`ar1_dfs_maps.py`** — 52 cities × 18 queries, DataForSEO Maps, ~$0.002/search
  (measured $1.30 for the full sweep). Tier A/B/C is assigned from the place
  title + category, strongest tier wins across searches.
* **`ar2_dfs_serp.py`** — 50 organic queries, depth 100, ~$0.53. This is where the
  Amazon-explicit long tail lives, because Argentine Amazon operators are
  remote-first and have no map pin.
* **`ar7_cace.py`** — the Cámara Argentina de Comercio Electrónico member
  directory (~2,400 members), free. The site is Shopify, so members come from
  `/collections/socios/products.json`; each member's own site is an outbound link
  on its product page. **Shopify 429s hard** — the first run silently capped at
  261 of 2,393 resolved. Workers are 5 with exponential backoff and a resume
  cache (`_cace_sites.json`); if a run ends far short of the member count, it was
  throttled, so just run it again.
* **`ar4_geo_check.py`** — required, not optional. A SERP run pinned to Argentina
  still returns Spanish and Mexican sites at the top of every "vender en amazon"
  query, because that SERP is dominated by Spain. `.ar` TLDs auto-pass; everything
  else is scored on +54 numbers, CUIT/AFIP, provinces and ARS, minus Spain/Mexico
  markers (+34, +52, NIF/RFC, euros). ~68% of the merged set passes.
* **`ar_harvest.py`** — wrapper around the shared `2b`/`2c` harvesters that keeps
  the cache in `ar-sellers/data/`. The shared scripts rewrite the *whole*
  `outreach/data/_harvest_progress.json`; other verticals harvest in this repo at
  the same time and a full-store rewrite from here would drop their rows.
* **`ar5_build_csv.py`** — the defensive layer. Geo gate, role/junk gate,
  first-name whitelist (a cold email opening "Hola Msanchez" is worse than "Hola
  equipo"), off-domain gate, 2 addresses per domain, and an off-niche gate:
  "agencia" in Spanish also means estate agent, travel agent and insurance
  broker, and the Maps sweep drags all three in.

### Cross-round dedupe

`ar5_build_csv.py` dedupes against every `instantly_*.csv` in `outreach/data/`
plus `data/ar_imported_emails.txt`. **That last file is the record of what was
actually pushed into Instantly** — append to it after every import, and never
dedupe against this vertical's own output CSVs (the builder is re-run while the
harvest is still filling, so that would empty it).

## Result (2026-08-12)

| | domains | emails | Instantly campaign |
|---|---|---|---|
| `AR-AGENCIES` | 1,511 | **1,722** | `[AR] Daniks.AI Partners — Agencias & Consultoras (es-AR)` `eb3aa7b1-1fce-4915-9b6e-970fb0307dcd` — **Active**, 1,717 leads |
| `AR-SELLERS` | 999 | **1,177** | `[AR] Daniks.AI — Amazon Sellers (es-AR)` `b667e46e-cf27-4b9b-b33a-0f663a6a52a2` — **Active**, 1,176 leads |

Both: 5 steps (A/B on step 1), 3/4/5/4-day gaps, Mon-Fri 09:00-18:00
`America/Argentina/La_Rioja` (Instantly's timezone enum has no
`.../Buenos_Aires` — same story as `Europe/Isle_of_Man` for the UK campaign),
30/day, stop-on-reply ON, open/link tracking OFF, `stop_for_company` ON, and the
8 lightest-loaded shared mailboxes (leadgenpulse / landingmate / landingverse /
havengenesis / marketifyapp — the daniel@/eric@ daniks boxes already carry 12-14
campaigns each).

Funnel: 26,078 Maps places + 1,239 SERP domains + 1,919 CACE members → 7,818
merged → 7,776 fresh → 5,566 Argentine → 4,606 with an email → 2,899 addresses
after cleaning and the 2-per-domain cap. DataForSEO spend: **$5.66** total
(Maps $4.80 over two rounds, SERP $0.86).

Tier A (Amazon-explicit) is only 423 of 7,776 domains. That is the finding, not
a shortfall — see the marketplace note at the top.

**Company-name enrichment.** Bulk-insert only carries the address, so every lead
initially fell back to "tu agencia" / "la marca". `data/ar_enrich.tsv`
(`email⇥company⇥website`) was transferred by clipboard and applied with
`PATCH /api/v2/leads/{id}` `{company_name, website}` — which writes
`payload.companyName`, the field `{{companyName}}` actually reads. **2,398 of
2,898 leads now carry a real business name**, verified exact against the source
with zero mismatches. The remaining 500 keep the neutral fallback on purpose:
their only available "name" was a listicle headline.

## Moving data into the Instantly tab

Two obvious routes are dead ends here, both confirmed twice:

* **`file_upload` (Chrome MCP)** silently drops its `paths` argument — the tool
  errors with `expected array, received undefined` no matter what path is given.
* **A localhost file server** cannot be reached from `app.instantly.ai`. Chrome's
  Private Network Access blocks a public https page from fetching `127.0.0.1`
  even with `Access-Control-Allow-Private-Network: true` on both the preflight
  and the response. It hangs, then fails.

What works is the **clipboard**, with two non-obvious requirements:

1. **`pbcopy` must run under a UTF-8 locale.** Plain `pbcopy < file` re-read the
   UTF-8 bytes as Mac Roman, so "Germán" arrived as "Germ√°n". Every accented
   Argentine company name would have shipped mojibake into live subject lines.
   Always `LC_ALL=en_US.UTF-8 pbcopy < file`.
2. **The textarea must be focused from JS** — `ta.focus(); ta.setSelectionRange(0,
   ta.value.length)`. A mouse click on it does not take focus, and `Cmd+A` then
   selects the whole *page* instead of the field, so the paste no-ops or appends.

And the rule that caught both problems: **hash the field against the source
before every commit.** For pure-ASCII lead lists a plain sha256 of the trimmed
text is enough. For anything with accents, compare an **order-independent XOR
fold of per-row SHA-256 digests** — a straight sorted-join digest will differ
between Python and JS purely from collation order and tells you nothing.

The macOS clipboard is shared with any other Claude session running in this repo
and **gets overwritten mid-flight** — it happened three times during this build
(twice with another agent's draft email). Never paste-then-import blind.

## Instantly

Campaigns are created through the internal API from a logged-in `app.instantly.ai`
tab, not the web editor — typing `{{` in the editor fires a variable autocomplete
that swallows the merge tag, which is why the MX and UK campaigns ended up with
literal "equipo"/"your brand". `ar6_build_sequences.py` emits the exact
`sequences` JSON shape (`[{steps:[{type,delay,variants:[{subject,body}]}]}]`,
empty subject = same thread) for `POST /api/v2/campaigns`.
