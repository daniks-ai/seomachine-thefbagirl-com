# Daniks.AI KDP — outbound sequence (indie publishers & book brands with own catalogs, EN)

Segment: `instantly_import_kdp_publishers_r4.csv` — presses and brands that advertise
their OWN titles on Amazon (digital-first genre presses, indie/nonfiction houses,
planner/coloring/workbook brands, poetry presses). Direct-customer offer, NOT white-label.
Modeled on `sequence-kdp-services-en.md`: pauses **3 / 4 / 5 / 4** days, steps 2/3/5 same
thread, step 4 new subject, zero links in cold emails (link only in reply handler).
Facts (canonical, 2026-08): $50M+ managed spend, 1,000+ accounts; KDP case ACoS 46%→21%
with 2x sales; start = A/B trial 2 weeks free, existing campaigns untouched; plans from
$49/mo (up to $5k ad spend) / $129/mo (up to $15k); target-ACoS autopilot; official
Amazon Ads API, ~10-min setup, access revocable; we're Amazon sellers ourselves (Daniks
cookware brand); Verified listing in Amazon Ads Partner Directory.

---

## Step 1 — Variant A
**Subject:** Amazon Ads on autopilot for {{companyName|your}} catalog

Hi {{firstName|there}},

I look after partnerships at Daniks.AI — an Amazon Ads autopilot managing $50M+ in spend across 1,000+ accounts. It now runs KDP and book campaigns end to end, and the book results are strong: in a recent client case ACoS dropped from 46% to 21% while sales doubled.

The mechanic is simple: you set a target ACoS per title (or one for the whole account) and the AI handles campaign creation, bids, keywords and negatives 24/7. Every title in the catalog gets watched — not just the frontlist you have time for.

The way we start removes the risk: we don't touch your existing campaigns. We launch ours in parallel, free for 2 weeks, and you compare the numbers side by side. After that it's from $49/month.

Want the trial? Just reply "trial" and I'll set it up.

{{sendingAccountFirstName}}

Not relevant? Reply "no thanks" and I won't follow up.

---

## Step 1 — Variant B
**Subject:** how many of {{companyName|your}} titles have ads running right now?

Hi {{firstName|there}},

Honest question — because for most presses the answer is "the newest ones, and whatever we had time for." Catalog-wide Amazon ads need constant babysitting, so the backlist just sits there.

Daniks.AI is an Amazon Ads autopilot ($50M+ managed spend, 1,000+ accounts) that now runs book campaigns. You set a target ACoS per title or per account; the AI runs campaigns, bids, keywords and negatives 24/7 across the whole catalog. Recent book client: ACoS from 46% to 21%, sales x2.

Zero-risk start: your current campaigns stay untouched, we run ours in parallel for 2 weeks free, you keep whichever wins. Plans from $49/month after.

Reply "trial" and I'll get you set up.

{{sendingAccountFirstName}}

Not relevant? Reply "no thanks" and I won't follow up.

---

## Step 2 (day 3) — same subject/thread

Hi {{firstName|there}},

The math I'd run in your seat:

— A PPC freelancer or in-house hire runs $2K–$8K/month and still only watches the titles they have hours for.
— Daniks.AI is $49/month with up to $5K/month ad spend ($129 up to $15K) — for the entire catalog, every marketplace, 24/7.
— Books punish sloppy ads twice: royalties are thin, so an unwatched campaign burns money fast. An autopilot that never sleeps is worth more per title than anywhere else on Amazon.

And you don't have to take my word for the "it works on books" part — ACoS 46%→21% with doubled sales is a real client's number, and the free 2-week A/B against your current setup will give you your own.

Reply "numbers" and I'll estimate the impact for a catalog your size.

{{sendingAccountFirstName}}

---

## Step 3 (day 7) — same subject/thread

Hi {{firstName|there}},

Fair to be skeptical — every AI tool promises autopilot. Three things that make Daniks.AI different:

1) We're Amazon sellers ourselves — we own Daniks, a large cookware brand — so the autopilot was built for our own money first, then opened to clients.

2) We're a Verified partner in Amazon's Ads Partner Directory ("1Click Ads by Daniks.AI") and connect through the official Amazon Ads API: standard Amazon authorization, ~10 minutes to set up, access revocable by you at any time. Nobody logs into your KDP account.

3) The trial is a real A/B, not a demo: your campaigns keep running, ours run in parallel for 2 weeks, and the report shows both sides' ACoS and sales. Most clients see the gap within those two weeks.

Reply "trial" and we'll start this week.

{{sendingAccountFirstName}}

---

## Step 4 (day 12) — NEW subject
**Subject:** a 2-week A/B on {{companyName|your}} own numbers

Hi {{firstName|there}},

Different angle: instead of claims in a cold email, run us against your current setup.

The offer — free for 2 weeks: your existing campaigns stay exactly as they are; Daniks.AI launches its own in parallel on a target ACoS you choose; at the end you compare ACoS and sales side by side and keep whichever wins. Setup is ~10 minutes through the official Amazon Ads API.

If the autopilot wins, plans start at $49/month for the whole catalog. If it doesn't, you've lost nothing and keep the data.

Reply "trial" to start, or "numbers" if you'd like the catalog math first.

{{sendingAccountFirstName}}

---

## Step 5 (day 16) — same subject/thread (breakup)

Hi {{firstName|there}},

Last one from me — I'll stop emailing {{companyName|you}} after this.

If catalog-wide Amazon ads on a target ACoS — without the babysitting — ever becomes interesting, that's Daniks.AI: 2-week free A/B next to your current campaigns, from $49/month after, official Amazon API. Just reply any time and I'll pick it right up.

Either way, good luck with the list.

{{sendingAccountFirstName}}

---

## Subsequence — "Reply handler" (fires when a lead is marked Interested)

Hi {{firstName|there}},

Great to hear from you — here's the short version:

— Start = free 2-week A/B test: your existing campaigns stay untouched, we launch ours in parallel, you compare ACoS and sales directly.
— Plans after the trial: $49/month (ad spend up to $5K/mo), $129/month (up to $15K/mo); larger tiers available. Cancel anytime.
— Full autopilot on target ACoS: campaign creation, bids, keywords, negatives — 24/7, per title or per account.
— Connection via the official Amazon Ads API (we're a Verified Amazon Ads partner) — ~10 minutes, standard Amazon authorization, revocable any time.
— Recent book client: ACoS 46% → 21%, sales doubled.

Details: https://daniks.ai

To start the trial I just need which marketplace(s) you sell in and a rough monthly ad spend — reply with those and we'll have you running this week. Happy to do a 20-minute call instead if you prefer.

{{sendingAccountFirstName}}
