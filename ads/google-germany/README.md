# Daniks.AI — Google Ads for German Amazon Sellers

**Product:** Daniks.AI — Amazon Ads full autopilot (set target ACoS → AI runs bids/keywords/campaigns 24/7).
**Landing page:** `https://daniks.ai/de/` (fully localized DE, **du-form** — ad copy matches). Anchors verified live: `#pricing`, `#features`, `#achievements`, `#how-it-works`; demo page `https://daniks.ai/de/meet/alex` (200).
**Offer:** 14-day free trial; paid Lite $49 / Plus $129 / Growth $299 mo (USD on the DE page too).
**Proof:** 1,000+ sellers · 10K+ SKUs · **Amazon Ads Verified Partner** · founder's own Top-1 DE cookware brand on Amazon.de.
**Audience:** German Amazon sellers (amazon.de = world's #2 marketplace) drowning in manual PPC / bad ACoS / expensive agencies.
**Replica of:** `ads/google-japan/` playbook (campaign `24019338665`, live since 2026-07-10), adapted to DE keyword data.

---

## What the DE keyword data says (DataForSEO, Germany/de, 2026-07-10)

| Cluster | Volume/mo | CPC signal | Verdict |
|---|---|---|---|
| **Competitor brands** — adference 880, adspert 480, bidx 390, amalytix 320, sellics 70 | ~2,000 | **$0.02–3.19** (!) | ✅ The DE goldmine. Both BidX and Adference are German — searchers are exactly our ICP. Cheap clicks. |
| **Agentur** — amazon agentur 880, ppc agentur 210, ads agentur 170, advertising agentur 170 | ~1,400 | **$50–60** (agencies bid hard) | ⚠️ Run with modest caps → bottom-of-page is fine; "kosten/preise" modifiers are the sweet spot ("KI statt Agentur ab $49"). |
| **Tools** — amazon ppc 390, ppc tool 70, ppc software 50, amazon acos 70 | ~700 | $16–19 stated, real entry lower | ✅ Core intent, run capped. |
| **Automatisierung/ACoS verbs** — acos senken 10, ppc automatisierung 10, werbung automatisieren ~0 | <100 | — | ⚠️ Near-zero volume (JP déjà vu: expect "Low search volume" flags). Keep small, exact intent. |
| **Broad** — amazon werbung 1,900 | 1,900 | $14.64, LOW comp | ⚠️ Mixed intent; phrase match + low bid + heavy negatives only. |

Key difference vs JP: **the competitor ad group leads here**, not generic automation. `perpetua` (880) is ambiguous (also a typeface/name) — we bid only `perpetua amazon`, not the bare brand.

---

## Plan (mirrors JP)

Launch **Search only**: one campaign, **5 tightly-themed ad groups** (JP's 4 + Wettbewerber), aggressive negatives, modest budget. Get to ~30 trial conversions, read search terms, then consider PMax / Demand Gen. DACH cold outreach (Instantly DE influencer campaign) runs in parallel → letter + ad = recognition.

## Budget & bidding

- **Start:** $10–15/day (account bills USD).
- **Ladder:** Maximize Clicks with **max-CPC cap $3.00** → at 15–20 conversions switch to Maximize Conversions → at 30+ add tCPA (~$25–40/trial).
- Keyword-level CPCs in `keywords.csv` are reference values for Editor import / manual fallback; under Maximize Clicks the strategy-level cap governs.
- Agentur ad group competes against $50 CPCs — we will sit at page bottom. That's intentional: the searcher comparing agencies sees "ab $49/Monat statt Agentur-Honorar".

## Targeting

- **Location:** Germany (Presence). **Phase 2:** add Austria + Switzerland (same language, ~15–20% extra volume) once search terms look clean.
- **Languages:** German **+ English** (many sellers run Seller Central in EN).
- **Networks:** Search only; Search partners **OFF**, Display **OFF**. AI Max **OFF**, broad-match toggle **OFF**, auto-assets **OFF** (same as JP audit settings).

## Conversion tracking (lesson from JP — do BEFORE trusting data)

JP audit found all 3 Sign-ups primary actions showing "No recent conversions" — tag never verified end-to-end. Same GA4 import serves DE. **Before switching to Max Conversions, run a test signup from `/de/`** and confirm the event lands in Google Ads. Maximize Clicks doesn't need it, so launch isn't blocked.

- **UTM template:** `?utm_source=google&utm_medium=cpc&utm_campaign=de_amazonppc_search&utm_content={adgroupid}&utm_term={keyword}`
- Enhanced Conversions on; Consent Mode v2 already live sitewide (regional consent shipped 2026-07-06 — Germany gets full consent banner, expect some measurement loss).

## Trademark note (Wettbewerber ad group)

Bidding on competitor brand keywords is allowed; **using their trademarks in ad copy is not**. The RSA for that group uses generic copy ("Die KI-Alternative für PPC"). If Google later restricts a keyword, drop it — don't appeal with TM text.

## Launch checklist

- [ ] Campaign built from `search-build.md` + `keywords.csv` (name: `GOOG_Search_DE_AmazonPPC_Autopilot`)
- [ ] Negatives from `negatives.csv` applied campaign-level
- [ ] Germany (Presence) · DE+EN languages · partners/Display OFF
- [ ] Budget $10/day · Maximize Clicks, cap $3.00
- [ ] 4 sitelinks + 8 callouts + structured snippet (campaign-level, DE — override EN account-level)
- [ ] Final URL `https://daniks.ai/de/` + UTM template
- [ ] Test signup from /de/ → verify Sign-ups conversion fires (JP still pending this!)
- [ ] Week 1: search-term report daily (esp. `amazon werbung` and bare competitor terms), add negatives; don't touch bids for 5 days
- [ ] Passkey steps (publish, budget changes) — user only

## Files

- `search-build.md` — campaign structure, 5 ad groups, RSA copy (DE, du-form), extensions
- `keywords.csv` — Editor import (Campaign/Ad Group/Keyword/Match Type/Max CPC)
- `negatives.csv` — campaign-level negative list (DE)
