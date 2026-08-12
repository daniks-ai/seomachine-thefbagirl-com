# Reactivation — signed up, never connected Amazon account (EN)

**Instantly campaign**: «Daniks.AI Reactivation — Signed Up, Never Connected»,
id `6275b37f-b8f3-4222-87d9-ff8b53c857ba`, built and **LAUNCHED 2026-08-10**
(status Active). 3 steps + schedule + options + **134 leads** + sender
`daniel@daniks.io`. Activated via `POST /api/v2/campaigns/{id}/activate`.

Sequence text is maintained via the API (`PATCH /api/v2/campaigns/{id}` with the
full `sequences` array) — far more reliable than the WYSIWYG editor.

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

## Sender: daniel@daniks.io (user's decision, 2026-08-10)

Instantly has NO mailbox on the real `daniks.ai` domain — only cold-outreach
lookalikes: `daniks-ai.com`, `daniks.io`, `getdaniks.ai`, `trydaniks.com`, each
with daniel@ / eric@ / nick@ personas (Daniel Harris, Eric Bennett, Nick Foster),
all active, warmup on, 15-17/day. The risk was raised — a warm list that knows
the real domain may read a lookalike as a phishing clone — and the user chose to
send from a lookalike anyway. Best available option going forward is still to
connect a real `daniks.ai` mailbox.

`daniks.io` picked of the four: it reads as an ordinary alternate TLD for the
company name, while `daniks-ai.com` is the textbook typosquat shape and
`get-`/`try-` prefixes read as pure cold outreach. All four are equally healthy,
so the choice is purely about how it looks to the recipient.

**Signature had to change**: the mailbox sends as "Daniel Harris", so signing
"Alex, Founder" would have been incoherent. Emails are now signed **Daniel**,
and the call-to-action explicitly books time with Alex the founder — which
matches what `daniks.ai/meet/alex` actually is.

**Segment**: daniks.ai registered users with a real (non-demo) seller record but
NO Amazon Ads API token, NO SP-API token, never had a trial (`had_trial=false`),
not unsubscribed, minus internal accounts, minus the junk Nov-2025 cohort.
**134 leads live** (full 184-row list kept in
`data/instantly_reactivation_never_connected.csv`, gitignored).

**Nature**: these are WARM leads — they created an account themselves. Tone is
"founder checking in", not cold pitch. Short sequence (3 steps), personal
sender, no heavy sales pressure.

**Personalization vars**: `first_name` (rows with a junk/empty name were filled
with the literal "there" so `Hi {{firstName}},` always reads right — no Instantly
fallback config needed), `joined_phrase` ("in July" / "back in February"),
`signup_date`.

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

Or if it's easier to just talk it through, book a short call with Alex, our
founder — 15 minutes, no pitch: https://daniks.ai/meet/alex

Daniel
Daniks.AI

---

## Step 2 — +4 days (same thread)

Hi {{firstName}},

Quick follow-up. If you tried to connect back then and something got in the
way — wrong account, permissions, or just not being sure what we'd do with the
access — reply here and I'll walk you through it personally.

Nothing has changed on our side: the first two weeks are free, no card charge,
and your existing campaigns stay exactly as they are.

Happy to do it live instead — grab a short call with our founder Alex and he'll
show it on a screen: https://daniks.ai/meet/alex

Daniel

---

## Step 3 — +6 days (same thread)

Hi {{firstName}},

Last note from me, promise.

If you're still managing PPC by hand — or paying an agency a percentage of ad
spend — it's worth one look at a side-by-side test on your own account. After
the free two weeks it's a flat subscription from $49/mo, not a cut of your spend.

Connect: https://daniks.ai
Or book a short call with Alex, our founder: https://daniks.ai/meet/alex

And if Amazon ads just aren't a priority right now, no hard feelings — your
account will be there when you come back.

Daniel
Daniks.AI

---

## Campaign settings (as configured 2026-08-10)

- Sender: **daniel@daniks.io** (single mailbox, 15/day cap → 134 leads drain in ~9 sending days). ✅
- Schedule: 9:00 AM–6:00 PM Eastern, Mon–Fri. ✅ saved
- Stop sending on reply: Enabled. ✅
- Open tracking: Disabled (warm list, protect deliverability). ✅
- Campaign daily limit: 30 (effective cap is the mailbox: 15/day). ✅
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

## Nov-2025 cohort — REMOVED from the campaign (2026-08-10)

The single biggest cohort is Nov 2025 (45 signups), and it does not look like
Amazon sellers. It's full of school/student addresses (`36576@llschools.net`,
`1009326@pdsb.net`, `irelyn.balfour32@thorntonacademy.org`, `im410s@spiritsd.ca`,
`759103@student.dusd.net`) and teen-style handles (`charleeunicorn@icloud.com`,
`dirtyhead710@`, `deathmetallog@`). Reads like a junk/bot signup wave or
misdirected traffic, not prospects.

**43 of them were deleted from the campaign on the user's instruction**, taking
it from 177 to 134 leads. They are still in the CSV — if the cohort ever needs
re-adding, they are the rows with `joined_phrase = "back in November"`.

Delete method (the bulk endpoint does not exist): `DELETE
/backend-alt/api/v2/leads/{id}` with the `x-workspace-id` header and **no
content-type header and no body** — sending `content-type: application/json`
returns 400 whether the body is empty, `{}`, or null.
