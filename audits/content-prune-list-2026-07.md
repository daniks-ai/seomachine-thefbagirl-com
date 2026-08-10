# Content Prune List — July 2026

**Date:** 2026-07-05
**Context:** Sitewide demotion since June 12 (impressions −95%, no recovery). Root cause: bulk publishing + promotional saturation. **53 of 343 articles (15% of the site) are about Daniks.AI** — the owner's own product. This document lists what to consolidate, noindex, or deepen to shift the site's profile from "scaled promo content" back to "curated operator blog."

**Data basis:** GSC 90-day impressions per page (pulled 2026-07-05), word counts, git publish dates. "0 impr" for pages published before June 1 means the page had a fair chance and earned nothing.

**Cadence rule applies to pruning too:** batch the changes into 2–3 deploys, not 50 single edits. Removal/noindex of junk is safe to do in one batch — Google treats pruning as a quality signal, not a content flood.

---

## Tier 1 — Daniks vs-article clones (June 11 + 16 bulk, all 0 impressions) — 16 files

These are the articles that triggered the demotion. Every one has **0 impressions in 90 days**. The EN May originals (which have impressions) stay; the June clones go.

### RU clones → consolidate into ONE roundup, then remove originals (301 → roundup)
RU search demand for these US tools is near zero; 8 separate clones are pure promo mass.

| File | Words | Action |
|---|---|---|
| blog/daniks-ai-vs-ad-badger-amazon-ppc-sravnenie-2026.mdx | 1464 | merge → RU roundup |
| blog/daniks-ai-vs-helium-10-adtomic-amazon-ppc-sravnenie-2026.mdx | 2522 | merge → RU roundup |
| blog/daniks-ai-vs-pacvue-amazon-ppc-sravnenie-2026.mdx | 2220 | merge → RU roundup |
| blog/daniks-ai-vs-perpetua-amazon-ppc-sravnenie-2026.mdx | 1588 | merge → RU roundup |
| blog/daniks-ai-vs-quartile-amazon-ppc-sravnenie-2026.mdx | 2206 | merge → RU roundup |
| blog/daniks-ai-vs-scale-insights-amazon-ppc-sravnenie-2026.mdx | 1207 | merge → RU roundup |
| blog/daniks-ai-vs-teikametrics-amazon-ppc-sravnenie-2026.mdx | 2189 | merge → RU roundup |
| blog/daniks-ai-vs-sellerapp-amazon-ppc-sravnenie-2026.mdx (Jun 16) | 1390 | merge → RU roundup |

New target: **one** RU article «Лучшие инструменты автоматизации Amazon PPC 2026 — честное сравнение» (counts as 1 of the week's 1–2 publications). 301 all eight URLs to it.

### DE June clones → merge into existing DE pieces or the DE roundup
Keep the May DE vergleich articles that earned impressions (pacvue 6 impr, perpetua 3, stellahive-fallstudie 3). Remove the June additions:

| File | Words | Action |
|---|---|---|
| blog/daniks-ai-vs-ad-badger-amazon-ppc-vergleich-2026.mdx | 2701 | 301 → DE PPC-tools roundup (create, same pattern as RU) |
| blog/daniks-ai-vs-helium-10-adtomic-amazon-ppc-vergleich-2026.mdx | 2635 | 301 → DE roundup |
| blog/daniks-ai-vs-scale-insights-amazon-ppc-vergleich-2026.mdx | 1932 | 301 → DE roundup |
| blog/daniks-ai-vs-sellerapp-amazon-ppc-vergleich-2026.mdx (Jun 16) | 1703 | 301 → DE roundup |
| blog/daniks-ai-vs-teikametrics-amazon-ppc-vergleich-2026.mdx (May, 0 impr) | 2332 | 301 → DE roundup |

### EN June clones → fold into an EN alternatives hub
EN keeps its winners: teikametrics (43 impr), quartile (11), pacvue, perpetua (May). The June/0-impr ones fold into ONE new hub that also closes the #1 AI-citation gap («Perpetua & Teikametrics alternatives — 8 Amazon PPC tools compared»):

| File | Words | Action |
|---|---|---|
| blog/daniks-ai-vs-ad-badger-amazon-ppc-2026.mdx | 2556 | 301 → EN alternatives hub |
| blog/daniks-ai-vs-helium-10-adtomic-amazon-ppc-2026.mdx | 2758 | 301 → EN alternatives hub |
| blog/daniks-ai-vs-scale-insights-amazon-ppc-2026.mdx | 2935 | 301 → EN alternatives hub |
| blog/daniks-ai-vs-sellerapp-amazon-ppc-2026.mdx (Jun 16) | 3031 | 301 → EN alternatives hub |

**Net effect:** 17 promo URLs → 3 roundup/hub pages. Site promo share drops from 15% → ~10%, and the June 11 footprint that tripped the filter is dismantled.

## Tier 2 — Pure promo with no search value — 9 files

| File | Words | Impr | Action |
|---|---|---|---|
| blog/daniks-ai-customer-review-andrew-superb-software.mdx | 555 | 0 | noindex (or merge quote into reviews/daniks-ai-review.mdx) |
| blog/daniks-ai-kundenbewertung-andrew-superb-software.mdx | 545 | 0 | same |
| blog/daniks-ai-otzyv-andrew-superb-software.mdx | 485 | 0 | same |
| blog/why-daniks-ai-exists.mdx | 1203 | 0 | keep content, set noindex — brand story for humans, not SERPs |
| blog/warum-daniks-ai-existiert.mdx | 1198 | 0 | same |
| blog/pochemu-daniks-ai-suschestvuet.mdx | 1091 | 0 | same |
| reviews/daniks-ai-review-ja.mdx | 516 | 0 | too thin to represent the brand — deepen to ≥1500w (within cadence) or noindex until then |
| reviews/daniks-ai-review-zh.mdx | 500 | 0 | same |
| blog/daniks-ai-obzor-ppc-autopilot-amazon.mdx + daniks-ai-erfahrung… (RU/DE reviews duplicated in blog AND reviews collections) | ~1500 | 0 | ✅ **DONE 2026-07-12** — both blog dupes noindexed (c4855d7); canonical reviews per locale stay |

## Tier 3 — Thin + zero impressions + old enough to judge (en/de/ru, pre-June) — 9 files

Improve to ≥1200 words with real substance, merge into a stronger sibling, or noindex. Do NOT delete silently — each needs a 30-second decision:

| File | Words | Suggested action |
|---|---|---|
| blog/amazon-fba-2026-updates-video-series.mdx | 517 | merge into the /videos hub or its paired article |
| reviews/taxdoo-test.mdx | 637 | deepen (DE compliance is our moat — this fits) |
| blog/virtual-bundles-amazon-srednij-chek.mdx | 656 | merge into RU virtual-bundles sibling |
| news/e-commerce-trends-q2-2026-deutschland.mdx | 664 | expired news — noindex or 410 |
| blog/how-to-launch-your-first-amazon-product.mdx | 667 | deepen — core TOFU topic, worth a real rewrite |
| blog/zakupochnaja-cena-marketplejsy.mdx | 702 | merge into RU financials cluster (watch existing cannibalization map) |
| blog/sistematizacija-biznesa-amazon-2026.mdx | 744 | deepen or merge |
| blog/erstes-amazon-produkt-launchen-2026.mdx | 745 | deepen — DE TOFU |
| blog/oshibki-amazon-fba-blokirovka-2026.mdx | 767 | deepen or merge into RU mistakes article |

Also: 44 more en/de/ru articles ≥800w with 0 impressions (pre-June). Do NOT prune these — most are demotion victims, not quality problems. Re-evaluate after recovery.

## ~~Tier 4 — JA/ZH thin mass translations~~ — **VOIDED 2026-07-06**

The "thin" flags were an artifact of the whitespace word counter (`\w+` counts a run of CJK text as one token). A character-based recount shows every JA/ZH article at 2,462–18,141 chars (≈1,200–9,000 word-equivalents) — **nothing is under the threshold**; `amazon-fba-hajimekata` alone is a full ~2,000-word tutorial. No deepening needed. The two JA/ZH daniks reviews flagged in Tier 2 are likewise fine (6,199/4,650 chars) — their noindex/deepen line is withdrawn. Lesson recorded: use char-count ÷ 2 for CJK locales in any future audit.

## Do NOT touch

- **BR/MX** (28+27 articles, median 2100–2300 words) — content quality is fine; the problem is indexation/authority, not thinness. Execute the latam-promotion plan instead.
- **EN May vs-articles with impressions** (teikametrics 43, quartile 11) and all three EN case studies (fornel 18, stellahive 15, tropeza) — these are the promo pieces that actually work.
- **The 44 ≥800w zero-impression en/de/ru articles** — demotion victims; re-check in September.
- **AE/SA pilots** — too new to judge (July 3).

## Execution order (fits the 1–2/week cadence)

1. ~~**Week of Jul 6:** Tier 2 noindexes + Tier 1 removals with 301s~~ ✅ **DONE 2026-07-06** (commit 745cbd0 in thefbagirl-com, push pending). Discovery: the language roundups already existed (`best-amazon-ppc-tools-2026` EN/DE/RU from May 22) and `teikametrics-vs-perpetua-2026` was already published 2026-07-06 — so NO new articles were needed; all 17 clones (EN+RU+DE in one batch, since pruning ≠ publishing) 301 to the existing roundups. Also fixed: `noIndex` frontmatter existed in the schema but was silently ignored — now plumbed through PostLayout + all 9 blog templates + excluded from sitemap.
2. **Week of Jul 6, part 2** ✅ **DONE 2026-07-06** (commit c71dada, pushed): Tier 3 prune-type actions (video-series stub 301→barcode article, expired DE Q2-news noindexed; both YouTube barcode videos — 37msUORxI_E and Short ftjjFWEZLgY — repointed to /news/amazon-barcode-rules-2026/ via Studio) + this week's two rewrites: `how-to-launch-your-first-amazon-product` (667→~1600w) and `erstes-amazon-produkt-launchen-2026` (745→~1500w, DE compliance section linking LUCID page). Bonus fix: noIndex support extended from blog-only to all 5 collections (schema + 36 templates).
3. **Week of Jul 12** ✅ **DONE 2026-07-12** (commit c4855d7, pushed): week-2 noindex batch — Tier-2 leftover blog-dupe reviews (RU/DE) + remaining zero-impression case/vs clones outside the keep list (NordFrost EN/DE/RU, Fornel DE, StellaHive RU kejs, Quartile DE vergleich, DE brand story; ~3 impr sacrificed). Plus hreflang hygiene: alternates.ts now drops noindexed variants from clusters and suppresses clusters on noindexed pages. Decision recorded: **locale pilots (JA/ZH/BR/MX/AE/SA) stay indexed** — launched after the June 12 demotion, didn't cause it; revisit in September or if no recovery by August.
4. **Weeks of Jul 13+ — remaining Tier 3 queue** (1–2 rewrites/week):
   - reviews/taxdoo-test.mdx (637w) — deepen, DE compliance moat
   - blog/virtual-bundles-amazon-srednij-chek.mdx (656w, RU) — deepen or fold into EN guide's RU translation; no RU sibling exists
   - blog/zakupochnaja-cena-marketplejsy.mdx (702w, RU) — deepen; check RU financials cannibalization map first
   - blog/sistematizacija-biznesa-amazon-2026.mdx (744w, RU) — deepen or merge
   - blog/oshibki-amazon-fba-blokirovka-2026.mdx (767w, RU) — deepen or merge into RU mistakes article
5. **September:** re-pull this matrix (`prune_analysis.py` pattern — with CJK-aware char counting) and re-evaluate the 44 held-back articles against post-recovery GSC data.

**Expected profile shift:** promo share 15% → ~9%, zero sub-800-word pages in en/de/ru, JA/ZH sections no longer the thinnest on the domain, June 11 bulk footprint fully dismantled.
