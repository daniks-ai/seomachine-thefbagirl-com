# Daniks.AI — direct outbound sequence to Indian Amazon sellers (en-IN)

Segment: **IN-SELLERS** — India-based brands/sellers running their own store and
selling on Amazon (amazon.in, and/or amazon.com via Global Selling). Direct
product offer (not white-label): Amazon Ads autopilot, free 2-week A/B trial,
from $49/mo.

Tone: plain-spoken operator English, no hype, no guru language. Waits:
**3 / 4 / 5 / 4** days. Steps 2/3/5 share the step-1 subject/thread; step 4
opens a new subject.

India-specific decisions (same reasoning as `outreach/sequences/india-en.md`):
- **English, not Hindi.** Every site in this list is English; a cold email in
  Hindi from a foreign SaaS reads as spam.
- **Price in USD, compare in ₹.** Billing is USD through Stripe, so the price
  stays `$49`, but the cost comparison uses the Indian market rate for PPC help
  (₹15,000–40,000/month per account) — the US "$4K–8.5K/mo specialist" framing
  is off by an order of magnitude here and instantly outs an unedited template.
- **Both marketplaces named.** amazon.in is supported by the platform (INR
  marketplace `A21TJRUUN4KGV`); the published ACoS case is not labelled as an
  amazon.in result, because our track record sits on .com/EU accounts. If a
  reply asks directly, the reply handler answers it straight.
- **No `{{vars}}` in the body.** Leads are imported without enrichment columns
  and page titles are too noisy to use as company names — literal "there" /
  "your brand" only.

---

## Step 1 — Variant A
**Subject:** Your Amazon PPC on autopilot

Hi there,

Writing because you sell your brand online in India — and if Amazon is one of your channels, this could take a weekly chore off your plate.

Daniks.AI is an Amazon Ads autopilot. We built it for our own brand first (Daniks, cookware) before opening it to other sellers; today it manages over $50M in ad spend across 1,000+ seller accounts.

How it works: you set a target ACoS per product, and the AI runs the campaigns, bids, keywords and negatives around the clock. Nothing to babysit.

The part most sellers like: we don't touch your existing campaigns. Ours run in parallel, you compare both sides in your own account, and the 2-week trial is free. From $49/mo after that.

Interested? Reply "yes" and I'll send the details.

{{sendingAccountFirstName}}

Not for you? Reply "no thanks" and I won't follow up again.

---

## Step 1 — Variant B
**Subject:** Who runs your Amazon ads right now?

Hi there,

A direct question: how many hours a week go into bids, keywords and negatives on your Amazon account — yours, or an agency's?

We ran into the same wall as sellers ourselves (we own the Daniks cookware brand), so we built Daniks.AI: an AI agent that runs Amazon Ads to a target ACoS you set per product. It now manages over $50M in ad spend for 1,000+ sellers.

The trial is risk-free: your current campaigns stay exactly as they are, ours run alongside them for 2 weeks free, and you compare. From $49/mo after.

Reply "yes" and I'll send you how to start — it's the official Amazon Ads API, about 10 minutes to connect.

{{sendingAccountFirstName}}

Not for you? Reply "no thanks" and I won't follow up again.

---

## Step 2 (day 3) — same subject/thread

Hi there,

The numbers, in case they're useful:

— PPC help in India runs ₹15,000–40,000 a month per account for a freelancer or a small agency, and the bigger agencies add a percentage of your ad spend on top.
— Daniks.AI is $49/mo with ad spend up to $5,000/mo, or $129/mo up to $15,000/mo. No percentage of your spend, ever.
— Recent client case: ACoS went from 46% to 21% and sales doubled.

And the trial is a genuine A/B test — we switch nothing of yours off, we launch campaigns in parallel, and you see both results side by side in your own account. 2 weeks, free.

Reply "yes" and I'll have it set up for you this week.

{{sendingAccountFirstName}}

---

## Step 3 (day 7) — same subject/thread

Hi there,

Fair to be sceptical — every tool with "AI" in the name promises the same thing. Two things you can check yourself:

1) We're sellers first. The same agent we're offering you runs ads for our own Daniks cookware brand and for our largest clients. That's why it works on a number you set — target ACoS — instead of a black box.

2) We're a verified partner in the Amazon Ads Partner Directory ("1Click Ads by Daniks.AI" — look it up in Amazon's own directory). The connection is the official Amazon Ads API with Amazon's standard authorisation, and you can revoke it at any time.

Works on amazon.in as well as amazon.com if you export through Global Selling.

If you'd rather see it running before connecting anything, reply "demo" and we'll book 20 minutes.

{{sendingAccountFirstName}}

---

## Step 4 (day 12) — NEW subject
**Subject:** A/B: your campaigns vs Daniks.AI — 2 weeks, free

Hi there,

One concrete proposal: let the AI compete against your current setup.

— Your campaigns keep running exactly as they are. We touch nothing.
— Daniks.AI launches its own campaigns in parallel, to the target ACoS you set.
— After 2 weeks you compare sales and ACoS on both sides in your own account, and decide.

Setup is about 10 minutes over the official Amazon Ads API. If the AI doesn't win, you disconnect and nothing has changed. If it wins, from $49/mo.

Reply "yes" and we'll get started.

{{sendingAccountFirstName}}

---

## Step 5 (day 16) — same subject/thread (close)

Hi there,

Last one from me — I won't email again after this.

If manual Amazon PPC ever becomes something you'd rather hand off — target ACoS, 24/7 autopilot, free 2-week A/B trial that leaves your campaigns alone — that's Daniks.AI: https://daniks.ai

Reply whenever it's relevant and I'll pick it straight up. Either way, best of luck with the brand.

{{sendingAccountFirstName}}

---

## Sub-sequence — "Reply handler" (run manually from Unibox)

Answers to the questions this segment actually asks. Canonical facts live in the
`daniks-offer-facts` memory — do not improvise pricing or cases.

**"Does it work on amazon.in?"**
Yes — the India marketplace is supported (INR). Straight answer on results: the
numbers we publish come from .com and EU accounts, since that's where most of
our sellers are. The mechanics are the same, and the 2-week A/B trial is exactly
how you find out on your own catalogue without paying for the answer.

**"How much does it cost?"**
$49/mo up to $5,000/mo of ad spend, $129/mo up to $15,000/mo. Billing is in USD.
No percentage of ad spend, no setup fee, cancel anytime.

**"What do you need from me?"**
Amazon Ads API authorisation (~10 minutes, Amazon's own consent screen) and a
target ACoS per product. Nothing else, and access can be revoked from your side
at any time.

**"We already have an agency."**
That's the case the A/B trial was built for. The agency's campaigns keep
running; ours run in parallel for two weeks; you compare in your own account.
Nobody has to be fired to run the test.

**"Send a demo."**
Book 20 minutes: https://daniks.ai — or offer the trial directly, it's faster.

**Not interested / unsubscribe.**
Confirm once, mark the lead Not Interested, no further email.
