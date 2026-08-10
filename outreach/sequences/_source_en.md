# Daniks.AI White-Label — outbound sequence (EN source of truth)

Pulled verbatim from live Instantly campaign `3fd1489a-…` on 2026-07-07.
Pauses between steps: **3 / 4 / 5 / 4** days. Variables kept exactly as Instantly
expects: `{{firstName|there}}`, `{{companyName|…}}`, `{{sendingAccountFirstName}}`.
Steps 2/3/5 reuse the previous email's subject (same thread); Step 4 is a new subject.

---

## Step 1 — Variant A
**Subject:** White-label Amazon PPC for {{companyName|your agency}}

Hi {{firstName|there}},

I look after agency partnerships at Daniks.AI — an Amazon Ads autopilot we built for our own FBA brands before opening it up. Today it manages $50M+ in ad spend for 1,000+ sellers.

We've just launched the Daniks.AI Agency plan for teams like {{companyName|yours}}: one $999/month subscription covers your whole client roster — unlimited seller accounts and a white-label portal (your logo, your domain, your reports). You set a target ACoS per client; the AI runs campaign creation, bids, keywords and negatives 24/7 on full autopilot — zero hands-on work for your team.

You keep the clients, the strategy and the margin. We stay invisible.

Want the one-pager? Just reply "send it" and it's yours.

{{sendingAccountFirstName}}

Not relevant? Reply "no thanks" and I won't follow up.

---

## Step 1 — Variant B
**Subject:** {{companyName|your agency}} + Daniks.AI (white label)

Hi {{firstName|there}},

Quick question: how many more Amazon accounts could {{companyName|your team}} take on if nobody had to touch bids or search terms again?

That's exactly what Daniks.AI does. It's an Amazon Ads autopilot we built for our own FBA brands first — today it manages $50M+ in ad spend for 1,000+ sellers. You set a target ACoS per client and the AI handles campaigns, bids, keywords and negatives 24/7 — zero manual work on your side. For agencies it's one $999/month Daniks.AI Agency subscription for your entire roster: unlimited seller accounts, white-label portal, your brand on everything your clients see.

Want the one-pager? Just reply "send it" and it's yours.

{{sendingAccountFirstName}}

Not relevant? Reply "no thanks" and I won't follow up.

---

## Step 2 (day 3) — same subject/thread

Hi {{firstName|there}},

The math I'd run if I were in your seat:

— A good PPC specialist costs $4K–$8.5K/month and tops out around 10–15 accounts.
— Stacking per-client tools: 5 clients on our per-brand Growth tier would be $1,495/month.
— The Daniks.AI Agency plan is $999 flat for the whole roster — up to $200K/month in client ad sales included, a flat 0.5% above that. Break-even sits at roughly 4 active clients.

Not hypothetical: one agency already runs 8 client accounts on Daniks.AI — $4K/month less in specialist payroll, and ACoS down 4 points across the board. Their team just sets the ACoS target per client; the autopilot does everything else.

Your clients see your brand and your reports; your margin is whatever you charge on top.

Reply "numbers" and I'll run the exact math for your roster size — takes me five minutes.

{{sendingAccountFirstName}}

---

## Step 3 (day 7) — same subject/thread

Hi {{firstName|there}},

Fair to be skeptical — every AI tool promises autopilot. Two things that make Daniks.AI different:

1) We're sellers first. The agent that would run your client accounts is the same one running our own Amazon brands and our largest customers'. It's ACoS-based: you set a target ACoS per client, and it handles campaign creation, bids, keywords and negatives 24/7 — no dashboards to babysit, zero manual work for your team. That's how it got to $50M+ under management.

2) Setup is about an hour of your time in total: a 30-minute kick-off where we provision your white-label portal (your logo, your domain, your support email), then clients connect with the same 1-click flow our sellers use.

If you'd rather see it than read about it: reply "demo" and we'll find 30 minutes that suit you — no deck, no discovery-call theatre.

{{sendingAccountFirstName}}

---

## Step 4 (day 12) — NEW subject
**Subject:** {{companyName|your brand}} on the dashboard?

Hi {{firstName|there}},

Different angle: instead of me describing white label in a cold email, let us show you Daniks.AI live.

Reply with your logo — or just your website — and on a 30-minute walkthrough we'll open the agency dashboard set up exactly as your clients would see it: your brand, your domain, your reports. The only control your team ever touches is the target ACoS per client — Daniks.AI runs everything else on full autopilot.

Pricing is public and flat: $999/month for the whole roster, anything above $200K/month in client ad sales at 0.5%.

{{sendingAccountFirstName}}

---

## Step 5 (day 16) — same subject/thread (breakup)

Hi {{firstName|there}},

Last one from me — I'll stop emailing {{companyName|you}} after this.

If handing the Amazon PPC grind to a white-label autopilot ever becomes interesting — more clients on the same headcount, ACoS-based, zero manual work for your team, your brand on everything — that's Daniks.AI. Just reply any time and I'll pick it right up.

Either way, good luck with the roster.

{{sendingAccountFirstName}}

---

## Subsequence — "Reply handler" (fires when a lead is marked Interested)

Hi {{firstName|there}},

Great to hear from you — here's the short version of the Daniks.AI Agency plan:

— $999/month covers your whole client roster (up to $200K/month in client ad-attributed sales, a flat 0.5% above that, cancel anytime).
— White-label portal: your logo, your domain, your colours, your support email. Clients never see Daniks.AI branding.
— Full autopilot, ACoS-based: you set a target ACoS per client and the AI agent handles campaign creation, bids, keywords and negatives 24/7 — zero manual work for your team.
— Unlimited seller accounts, one Stripe invoice; setup is about an hour of your time, break-even at roughly 4 active clients.

Full details with the pricing table: https://daniks.ai/agency

Happy to walk you through it under your brand — would Tuesday or Thursday afternoon (your time) suit for a 30-minute call? If not, just name a window that works and we'll fit in.

{{sendingAccountFirstName}}
