# Reactivation — signed up, never connected Amazon account (EN)

**Instantly campaign**: «Daniks.AI Reactivation — Signed Up, Never Connected»,
id `6275b37f-b8f3-4222-87d9-ff8b53c857ba`, built 2026-08-10, status **Draft**.
3 steps + schedule + options + **177 leads imported** (verified server-side).

**One thing blocks launch: no sender is selected** — see "Sender problem" below.
This is a real decision, not an oversight.

Leads went in via the internal API from the page console (the UI CSV upload is
broken — same workaround as [IN] campaign): `POST /backend-alt/api/v2/leads`
with `{campaign, email, first_name, custom_variables:{joined_phrase},
skip_if_in_workspace:true, skip_if_in_campaign:true}`, 5 parallel workers,
zero errors. Verified `joined_phrase` lands in the lead payload.

**7 of 184 were skipped as workspace duplicates** — and where they already sit
is itself a finding: `luis.tome@mathfel.de` and `callistaevacosmetics@gmail.com`
are in «Daniks.AI Amazon Sellers [DE Companies]»; `merakvic@`, `ana.isabel.gmu@`,
`reyrod2501@`, `libeforyoulibe@`, `atlanticabrands@` are in «[ES Companies]».
These are people who already registered on daniks.ai being cold-pitched as
strangers. Worth suppressing registered users from the cold Sellers campaigns.

## Sender problem (read before launching)

Instantly has NO mailbox on the real `daniks.ai` domain. The only Daniks-looking
senders connected are cold-outreach lookalikes: `daniks-ai.com`, `daniks.io`,
`getdaniks.ai`, `trydaniks.com` (daniel@ / eric@ personas). Those are fine for
strangers, wrong for this list: these 189 people registered on daniks.ai, know
the real domain, and a mail from "Alex, Founder, Daniks.AI" arriving from
`daniks-ai.com` reads as a phishing clone of the product they signed up for.

Options, best first:
1. Connect a real `daniks.ai` mailbox (alex@ or ekaterina@) to Instantly and
   send from it. Warm list, low volume (30/day) — no warmup risk.
2. Send this sequence from the product's own transactional/marketing mail
   instead of Instantly — same argument, and it keeps the thread on-brand.
3. Use a lookalike domain anyway — cheapest, but burns trust on a warm list.
   Not recommended.

**Segment**: daniks.ai registered users with a real (non-demo) seller record but
NO Amazon Ads API token, NO SP-API token, never had a trial (`had_trial=false`),
not unsubscribed. 189 leads as of 2026-08-10 (list:
`data/instantly_reactivation_never_connected.csv`, gitignored).

**Nature**: these are WARM leads — they created an account themselves. Tone is
"founder checking in", not cold pitch. Short sequence (3 steps), personal
sender, no heavy sales pressure.

**Personalization vars**: `first_name` (47 rows with a junk/empty name were
filled with the literal "there" so `Hi {{firstName}},` always reads right —
no Instantly fallback config needed), `joined_phrase` ("in July" / "back in
November"), `signup_date`.

**Instantly gotcha**: typing `{{firstName}}` into the rich-text editor gets
eaten by the variable autocomplete. Use the `<>` code-view toggle at the bottom
of the editor and paste raw `<div>` HTML instead. Also: clicking Save re-selects
Step 1, so re-click the target step before typing the next body — otherwise the
new text lands in Step 1.

**Links**: app login `https://daniks.ai` · book a call
`https://daniks.ai/meet/alex` (verified live 2026-08-10).

**Canonical offer facts used** (per daniks-offer-facts memory): 2 free trial
weeks, A/B parallel launch (existing campaigns untouched), ~10-min connect via
official Amazon Ads API + revoke anytime, target-ACoS mechanic, own cookware
brand Daniks, from $49/mo.

---

## Step 1 — Day 0

**Subject:** you stopped one step short of the free trial

Hi {{firstName}},

You signed up for Daniks {{joined_phrase}} but never connected your Amazon
account — so it's just been sitting there, and we never got the chance to show
you anything.

If Amazon PPC is still on your plate, here's what the two free weeks look like:

- You connect through the standard Amazon Ads login — about 10 minutes, and you
  can revoke access at any moment.
- We don't touch your existing campaigns. Ours launch in parallel, and you
  compare the results side by side on your own account.
- You set a target ACoS per product; campaigns, bids, keywords and negatives
  are on us, 24/7.

Two weeks is usually enough to see the difference. We run our own cookware
brand (Daniks) on Amazon the same way, so it's our money on the line too.

Pick it back up here: https://daniks.ai

Prefer to talk to a human first? Grab a slot: https://daniks.ai/meet/alex

Alex
Founder, Daniks.AI

---

## Step 2 — Day 4 (same thread)

Hi {{firstName}},

Quick follow-up. If you tried to connect back then and something got in the
way — wrong account, permissions, just wasn't sure what we'd do with the
access — reply here and I'll walk you through it personally.

Nothing has changed on our side: the first two weeks are free, no card charge,
and your existing campaigns stay exactly as they are.

Or book 15 minutes and I'll show it on a screen: https://daniks.ai/meet/alex

Alex

---

## Step 3 — Day 10 (same thread)

Hi {{firstName}},

Last note from me, promise.

If you're still managing PPC by hand — or paying an agency a % of ad spend —
it's worth one look at a side-by-side test on your own account. After the free
two weeks it's a flat subscription from $49/mo, not a cut of your spend.

Connect: https://daniks.ai · Talk first: https://daniks.ai/meet/alex

And if Amazon ads just aren't a priority right now, no hard feelings — your
account will be there when you come back.

Alex
Founder, Daniks.AI

---

## Campaign settings (as configured 2026-08-10)

- **Senders: NOT SET** — blocked on the sender problem above.
- Schedule: 9:00 AM–6:00 PM Eastern, Mon–Fri. ✅ saved
- Stop sending on reply: Enabled. ✅
- Open tracking: Disabled (warm list, protect deliverability). ✅
- Daily limit: 30/day → 189 leads drain in ~7 sending days. ✅
- Step delays: Step 1 → +4 days → Step 2 → +6 days → Step 3. Steps 2-3 reuse
  the Step 1 subject (empty subject = same thread). ✅

Excluded by the SQL, do not re-add: `had_trial=true` (17 users — they DID
activate once, they need a different message), SP-API-only connectors (2),
unsubscribed announcements (0 today), demo sellers, test_stripe@daniks.com.

## Segment counts behind the list (2026-08-10)

Of 389 real registered users: 181 connected the Ads API, 206 never did. Of
those 206 — 17 had a trial anyway, 2 connected SP-API only, leaving 189 who
signed up and did nothing. Minus 5 internal/test accounts (`support@daniks.ai`,
`alex-amazon@daniks.ai`, `test_fp@daniks.ai`, `poryadok.cloud@gmail.com`,
`abc123@testing.com`) = **184 real leads**, of which 177 imported.
40 never even confirmed their email. Signups span 2025-11-14 → 2026-08-10.

Note on `auth_user`: in this DB **every** user row has `is_staff = true`, so
that column is useless as a staff filter — exclude internal accounts by address.

## Suspicious Nov-2025 cohort — decide before launching

The single biggest cohort is Nov 2025 (45 signups), and it does not look like
Amazon sellers. It's full of school/student addresses (`36576@llschools.net`,
`1009326@pdsb.net`, `irelyn.balfour32@thorntonacademy.org`, `im410s@spiritsd.ca`,
`759103@student.dusd.net`) and teen-style handles (`charleeunicorn@icloud.com`,
`dirtyhead710@`, `deathmetallog@`). Reads like a junk/bot signup wave or
misdirected traffic, not prospects.

They are imported, but consider filtering them out before launch: they add
~25% volume with near-zero conversion odds and above-average spam-complaint
risk, which matters more than usual because this is a warm-list send from a
domain we care about. Filter in Instantly by `joined_phrase = "back in November"`.
