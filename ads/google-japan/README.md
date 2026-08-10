# Daniks.AI — Google Ads for Japanese Amazon Sellers

**Product:** Daniks.AI — Amazon広告 full autopilot (set target ACoS → AI runs bids/keywords/campaigns 24/7).
**Landing page:** `https://daniks.ai/ja/` (fully localized JA: hero, pricing, Verified Partner proof, CTA).
**Offer:** 14-day free trial, no card friction; paid Lite $49 / Plus $129 / Growth $299 mo.
**Proof to lean on:** 1,000+ sellers · 10K+ SKUs · **Amazon Ads Verified Partner** · own Amazon brand w/ 2,000+ reviews.
**Audience:** Japanese Amazon sellers (Seller Central / 物販・EC事業者) drowning in manual PPC / bad ACoS.

---

## The ways to advertise on Google (proposed) — and the plan

| # | Channel | Intent | When to run | Verdict |
|---|---------|--------|-------------|---------|
| 1 | **Search — problem/solution keywords** | Highest (they're searching "Amazon 広告 自動化") | **Now — start here** | ✅ Launch first |
| 2 | **Search — competitor/brand** (Perpetua, Pacvue, 運用代行) | High | Phase 2 | ⚠️ Small budget, low JP volume, TM-policy care |
| 3 | **Performance Max** | Mixed (auto across Search/Display/YT/Gmail/Discover) | After ~30 conversions + assets ready | 🔜 Phase 2 scale |
| 4 | **Demand Gen / YouTube** | Low (demand creation) | Phase 3 | 🔜 Reuse video creative; awareness |
| 5 | **Display / RLSA retargeting** | Warm | After traffic exists | 🔜 Retarget /ja/ + blog readers |
| 6 | **Yahoo! JAPAN Ads (Search)** | High | Parallel to #1 | ➕ ~20% JP search share, older/biz demo — mirror the same build |

**Recommendation:** launch **#1 Search only** — one campaign, four tightly-themed ad groups, aggressive negatives, modest budget. Get to ~30 trial conversions, read the search-term report, *then* layer Performance Max (#3) and Demand Gen/YouTube (#4). Don't fragment budget across five campaign types on day one — the algorithm needs concentrated conversion signal. This also fits the current cautious posture: cheap, measurable, high-intent first.

Why Search first for this product: buying intent is explicit and searchable in Japanese, the offer (free trial) converts cold traffic, and CPCs in this B2B niche are reachable. PMax/YouTube waste spend until you have conversion data to feed them.

---

## Budget & bidding

- **Start:** ¥5,000/day (~$33) on the Search campaign. ≈ ¥150,000/mo (~$1,000).
- **Bid strategy ladder:**
  1. Launch on **Maximize Clicks with a max-CPC cap (¥150–250)** *or* Manual CPC — buy data cheaply, avoid tCPA starving on zero history.
  2. At **15–20 conversions** → switch to **Maximize Conversions**.
  3. At **30+ conversions** → add a **Target CPA** (start ¥4,000–6,000 for a trial start; tighten as data comes in).
- **Unit economics sanity:** trial → paid at $49–299/mo recurring. Even a ¥6,000 (~$40) cost-per-trial pays back fast at Growth-tier retention. Watch **trial→paid rate**, not just cost-per-trial.

---

## Conversion tracking (do this BEFORE launch)

Primary and secondary conversions already have GA4 key events wired on the site (regional consent + GA4 key events + Ads conversions were shipped 2026-07-06). Confirm/extend:

- **Primary conversion:** `無料トライアル開始` (trial signup / account created) — mark as the *only* "Primary" conversion action for bidding.
- **Secondary:** `デモを予約` (demo booking) — track as Secondary (observe, don't bid).
- Link **Google Ads ↔ GA4**, import the key events as conversion actions, verify with a real test signup before spending.
- **UTM template** (campaign-level "Tracking template" or manual on final URLs):
  `?utm_source=google&utm_medium=cpc&utm_campaign=jp_amazonppc_search&utm_content={adgroupid}&utm_term={keyword}`
- Enable **Enhanced Conversions** (hashed email from signup) — recovers JP iOS/consent-mode loss.

---

## Targeting settings

- **Locations:** Japan. (Presence: "people in your targeted locations" — not interest.)
- **Languages:** Japanese **+ English** (many sellers run Seller Central in EN; keyword list covers both `Amazon`/`アマゾン`).
- **Networks:** Search only. **Turn OFF** "Search partners" and "Display Network" at launch (they dilute intent).
- **Schedule:** all-week to start; JST. Read dayparting after 2 weeks.
- **Devices:** all; bid-adjust later (B2B skews desktop for signup completion).

---

## Japan-specific notes

- **Yahoo! JAPAN Search Ads** is a genuine second channel here (~20% search share, older/business users). The exact keyword + ad build in `search-build.md` ports over with minor edits — worth mirroring once Google is stable.
- Include **both scripts** for the brand token: `Amazon` (Latin) and `アマゾン` (katakana) — Japanese searchers use both. Keyword list already does.
- Ad copy respects Google's **double-byte character counting**: full-width chars count as 2, so headlines are kept ≤15 JA chars (30 count) and descriptions ≤45 JA chars (90 count). Google Ads Editor will flag any overflow on import.
- 特定電子メール法 (the opt-in email law that killed the scraping idea) does **not** restrict search ads — this channel is clean for cold reach.

---

## Launch checklist

- [ ] GA4 ↔ Google Ads linked; `無料トライアル開始` imported as **Primary** conversion; tested with a real signup
- [ ] Enhanced Conversions on; Consent Mode v2 confirmed (site already has regional consent)
- [ ] Campaign built from `keywords.csv` + `search-build.md` (or import `daniks-jp-search.csv` in Editor)
- [ ] Negatives applied from `negatives.csv` (attach as a shared negative list — reusable for Yahoo)
- [ ] Search partners + Display **OFF**; Japan location (presence); JA+EN languages
- [ ] Budget ¥5,000/day; Maximize Clicks + max-CPC cap ¥200
- [ ] 4 sitelinks + callouts + structured snippets added (see `search-build.md`)
- [ ] Final URLs → `https://daniks.ai/ja/` with UTM template
- [ ] Week-1: check search-term report daily, add negatives; do NOT touch bids for 5 days (learning)

---

## Files

- `search-build.md` — full build to paste: campaign structure, ad groups, RSA copy (JA), extensions
- `keywords.csv` — Google Ads Editor import (Campaign/Ad Group/Keyword/Match Type/Max CPC)
- `negatives.csv` — negative keyword list
