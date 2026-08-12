# Daniks.AI White-Label — India sequence (EN, adapted)

Adaptation of `_source_en.md` for the live `[IN]` campaign
(`df7d6bbb-c9f3-422c-94e1-64aa7daac453`). **Language stays English, pricing stays
USD** — see "Why not Hindi / rupees" at the bottom.

Changed: **Step 1 (both variants)** and **Step 2 (full rewrite)**.
Steps 3, 4, 5 and the reply-handler are unchanged from `_source_en.md` — they
carry no US-specific economics.

Pauses unchanged: **3 / 4 / 5 / 4** days. Variables exactly as Instantly expects:
`{{firstName|there}}`, `{{companyName|…}}`, `{{sendingAccountFirstName}}`.

---

## Step 1 — Variant A
**Subject:** White-label Amazon PPC for {{companyName|your agency}}

Hi {{firstName|there}},

I look after agency partnerships at Daniks.AI — an Amazon Ads autopilot we built for our own FBA brands before opening it up. It now manages $50M+ in ad spend across 1,000+ sellers.

Why I'm writing to {{companyName|your team}} specifically: most agencies we talk to are capped not by demand but by how many accounts one experienced person can actually keep an eye on. Daniks.AI takes that ceiling out. You set a target ACoS per client and the AI runs campaign creation, bids, keywords and negatives 24/7 — including the hours your team is offline, which for a US client is most of their selling day.

For agencies it's one $999/month subscription covering the entire roster: unlimited seller accounts, white-label portal, your logo and your domain on everything the client sees. You keep the clients, the strategy and the margin. We stay invisible.

Want the one-pager? Just reply "send it" and it's yours.

{{sendingAccountFirstName}}

Not relevant? Reply "no thanks" and I won't follow up.

---

## Step 1 — Variant B
**Subject:** {{companyName|your agency}} + Daniks.AI (white label)

Hi {{firstName|there}},

Quick question: how many more Amazon accounts could {{companyName|your team}} take on if nobody had to touch bids or search terms again?

That's what Daniks.AI does. It's an Amazon Ads autopilot we built for our own FBA brands first — today it manages $50M+ in ad spend for 1,000+ sellers. You set a target ACoS per client; the AI handles campaigns, bids, keywords and negatives around the clock, so no account sits unmanaged in the gap between your team's hours and the client's peak hours.

For agencies it's one $999/month Daniks.AI Agency subscription for the whole roster: unlimited seller accounts, white-label portal, your brand on everything your clients see.

Want the one-pager? Just reply "send it" and it's yours.

{{sendingAccountFirstName}}

Not relevant? Reply "no thanks" and I won't follow up.

---

## Step 2 (day 3) — same subject/thread  [FULL REWRITE]

Hi {{firstName|there}},

Following up with the math — though the honest version of it depends on how {{companyName|your agency}} is set up.

Daniks.AI Agency is $999/month flat for your whole roster: every seller account you manage, one invoice, cancel anytime (that covers up to $200K/month in client ad sales, a flat 0.5% above that).

So the number that matters isn't $999 — it's $999 divided by your account count. Ten accounts puts it near $100 per client per month; twenty puts it near $50. Set that against what you bill per account and the decision makes itself. And if you're running fewer than about five accounts today, it probably doesn't pay for itself yet — I'd rather say that now than after a call.

What changes in practice: one agency on the plan runs 8 client accounts with ACoS down 4 points across the board, and their team's only recurring input is the target ACoS per client. No dashboards to babysit, no bid sheets, and no dead hours between your analysts logging off and the client's marketplace getting busy.

Your clients see your brand and your reports. Your margin is whatever you charge on top.

Reply "numbers" and I'll run it against your actual roster size — takes me five minutes.

{{sendingAccountFirstName}}

---

## Steps 3–5 + reply handler

Unchanged — use `_source_en.md` verbatim.

---

## Why not Hindi / rupees (decision, 2026-08-10)

**Hindi: no.** All 327 agency sites in the lead base are English — company names,
body copy, contact addresses. India is multilingual and the list is heavy on
Bangalore / Hyderabad / Chennai, where Hindi is not the local language. A cold
B2B email in Hindi from a foreign SaaS reads as machine-translated spam.

**Rupees: no.** Billing is USD via Stripe, so an INR price implies an INR invoice
that doesn't exist, at a rate that moves. More to the point, $999 reads as small
to a US agency and ₹85–88k/month reads as a heavy line item — spelling it out in
INR works against us. The fix is the denominator (cost per account), not the
currency, which is what the Step 2 rewrite does.

**What actually broke the US copy for India:** the original Step 2 argued from
"a good PPC specialist costs $4K–8.5K/month". Indian salaries are lower by roughly
an order of magnitude, so that line identifies the email as an unedited US
template on the second touch. Removed entirely; the payroll-savings framing of the
8-account case study went with it (the account count and the 4-point ACoS drop
stayed — those hold anywhere).

**amazon.in:** the marketplace is supported by the platform (`A21TJRUUN4KGV`, INR),
but it is not active in any accessible seller account, so we have no results to
show there. Deliberately not mentioned in the copy — if a domestic-only agency
asks, say the marketplace is supported and our track record is on .com/EU.

**Open segmentation gap:** the list mixes agencies serving Western sellers
(offshore delivery, USD revenue — $999 is normal for them) with agencies serving
only amazon.in sellers at ₹15–40k per account, for whom $999 is the revenue of
two or three clients. The Step 2 "fewer than five accounts and it doesn't pay"
line lets them self-qualify, but a real split by website signals (does the site
target amazon.com / global clients?) is a separate pass worth doing.
