# Daniks.AI — Google Ads: Competitor Search EN (US + UK + CA)

**Strategy table row 3.** Highest-intent traffic in the niche: people already using (or evaluating) a competitor PPC tool and searching for alternatives, pricing, or reviews. Volumes are tiny, conversion is high.

**Product:** Daniks.AI — Amazon Ads full autopilot (set target ACoS → AI runs bids/keywords/campaigns 24/7).
**Offer:** 14-day free trial; flat pricing Lite $49 / Plus $129 / Growth $299 per month — **no percentage of ad spend** (the #1 pain with Pacvue/Quartile/Perpetua-class tools).
**Proof:** 1,000+ sellers · 10K+ SKUs · Amazon Ads Verified Partner.
**Replica of:** `ads/google-japan/` playbook (campaign `24019338665`, live 2026-07-10) + `ads/google-germany/` structure, adapted to EN competitor-brand data.

---

## Landing pages (all verified 200 on 2026-07-10)

Each competitor ad group goes to its dedicated vs-page (message match → better QS on brand terms):

| Ad group | Final URL |
|---|---|
| Perpetua | `https://daniks.ai/blog/daniks-vs-perpetua-amazon-ppc-2026` |
| Pacvue | `https://daniks.ai/blog/daniks-vs-pacvue-amazon-ppc-2026` |
| Quartile | `https://daniks.ai/blog/daniks-vs-quartile-amazon-ppc-2026` |
| Helium10-Adtomic | `https://daniks.ai/blog/daniks-vs-helium10-adtomic-amazon-ppc-2026` |
| Teikametrics | `https://daniks.ai/blog/daniks-vs-teikametrics-amazon-ppc-2026` |
| Other-Tools | `https://daniks.ai/` (no vs-page for Sellozo/Scale Insights/Intentwise → homepage trial CTA) |

Sitelink target: `https://daniks.ai/blog/best-amazon-ppc-tools-2026` (covers Perpetua, Pacvue, Quartile, Teikametrics, Adtomic, Adspert).

---

## What the EN keyword data says (DataForSEO, US/UK/CA, 2026-07-10)

| Cluster | US vol/mo | CPC signal | Verdict |
|---|---|---|---|
| **Pacvue** — bare 2,900 (+390 UK, 170 CA), pricing 20 @ $100, competitors 20 @ $140 | ~3,000 | $15–140 | ✅ Biggest brand. Enterprise tool with % -of-spend pricing + minimums — our flat $49 is the knife. Bare term phrase at capped bid = bottom-of-page is fine. |
| **Teikametrics** — bare 1,000, reviews 90, pricing 20 | ~1,100 | $24–30 | ✅ Unambiguous brand, healthy volume. |
| **Sellozo** — bare 260, reviews 20 | ~300 | $6–50 | ✅ SMB tool, closest ICP overlap. No vs-page → homepage. |
| **Scale Insights** 480 / **Intentwise** 390 / **Ad Badger** 170 / **Adspert** 170 | ~1,200 | $5–22 | ✅ Long tail of tools, one ad group. |
| **Quartile** — quartile amazon 70, reviews 40, pricing 20 | ~150 | $25–56 | ✅ Only modified terms (bare "quartile" = statistics). |
| **Adtomic/Helium 10** — adtomic 50, h10 adtomic 40 | ~120 | $17–27 | ✅ **Adtomic was sunset Feb 2025**, replaced by "Helium 10 Ads" (Pacvue engine, 2% fee over $5K spend on Diamond). Confused/annoyed users = ready demand. |
| **Perpetua** — amazon 40, software 50, pricing 10 @ $135 | ~150 | $30–135 | ✅ Only modified terms (bare "perpetua" = typeface/name). Sellics folded into Perpetua → `sellics alternative` lands here too. |
| **"X alternative(s)"** long-tails | 0 measured | — | ⚠️ DataForSEO shows no volume — expect "Low search volume" flags (JP/DE déjà vu). Keep them anyway: phrase-match brand terms will catch the real alternative-queries. |
| **Skipped**: bare `trellis amazon` (880 — garden trellis shoppers), bare `bidx` (4,400 US — ambiguous non-tool entity; BidX is DACH-focused anyway), bare `perpetua`/`quartile` | — | — | ❌ Ambiguity burns budget. |

## Helium 10 Adtomic status check (2026-07-10)

Adtomic discontinued; replaced Feb 2025 by **Helium 10 Ads** — a Pacvue-powered rebuild bundled into Platinum/Diamond plans, with a 2% fee on PPC spend over $5K/mo (Diamond). Sources: [helium10.com launch post](https://www.helium10.com/blog/helium-10-ads/), [revenuegeeks.com/helium-10-ads](https://revenuegeeks.com/helium-10-ads/), [atom11 pricing breakdown](https://www.atom11.co/blog/helium-10-pricing). Ad-copy angle for that group: "your PPC tool got replaced — switch to something stable" (no trademarks in copy).

---

## Budget & bidding

- **Start:** $8/day (top of the $5–8 strategy range; account bills USD).
- **Maximize Clicks with max-CPC cap $4.00.** Stated CPCs ($25–140) are top-of-page estimates on tiny volumes — capped bids get bottom-of-page placement, which is fine: an alternative-seeker reads the whole page.
- **Ladder:** at 15–20 conversions → Maximize Conversions; at 30+ → tCPA. Same as DE plan.

## Targeting

- **Locations:** United States, United Kingdom, Canada — **Presence** (not interest).
- **Languages:** English.
- **Networks:** Search only; Search partners OFF, Display OFF, AI Max OFF, broad-match toggle OFF, auto-assets OFF (JP audit settings).

## Conversion tracking (still pending from JP!)

Same GA4-imported Sign-ups actions serve this campaign. JP audit (2026-07-10) found all 3 primary actions showing "No recent conversions" — test signup never completed. Maximize Clicks doesn't need it, so launch isn't blocked, but **don't switch to Max Conversions until a test signup from `/` is verified in Google Ads**.

- **Final URL suffix (campaign-level):** `utm_source=google&utm_medium=cpc&utm_campaign=en_competitors_search&utm_content={adgroupid}&utm_term={keyword}`

## Trademark rules (whole campaign is competitor keywords)

Bidding on competitor brand keywords is allowed; **using their trademarks in ad copy is not**. All RSAs use generic copy ("The AI Alternative for Amazon PPC"). If Google restricts a keyword, drop it — don't appeal with TM text. Display path uses `/Compare/PPC-Autopilot` — no brand names.

## Launch checklist

- [ ] Campaign built from `search-build.md` + `keywords.csv` (name: `GOOG_Search_EN_Competitors_US-UK-CA`)
- [ ] Negatives from `negatives.csv` applied campaign-level
- [ ] US+UK+CA (Presence) · English · partners/Display OFF · AI Max OFF
- [ ] Budget $8/day · Maximize Clicks, cap $4.00
- [ ] 4 sitelinks + 8 callouts + structured snippet (campaign-level EN)
- [ ] Per-ad-group Final URLs (vs-pages) + campaign Final URL suffix
- [ ] Test signup → verify Sign-ups conversion fires (carried over from JP, still open)
- [ ] Week 1: search-term report daily (esp. bare `pacvue`, `m19 amazon`, `quartile *`), add negatives; don't touch bids for 5 days
- [ ] Passkey steps (publish, budget changes) — user only

## Files

- `search-build.md` — campaign structure, 6 ad groups, RSA copy (EN, trademark-safe), extensions
- `keywords.csv` — Editor import (Campaign/Ad Group/Keyword/Match Type/Max CPC)
- `negatives.csv` — campaign-level negative list (EN + ambiguity guards)
