# Amazon India sellers — direct outreach

Direct-to-seller cold outreach: India-based online retailers, offering the
daniks.ai product (Amazon Ads autopilot — free 2-week A/B trial, from $49/mo).
Not the white-label/agency motion — that one lives in
`outreach/sequences/india-en.md` and the `[IN] … PPC Agencies` campaign.

Built 2026-08-12 on the request "собери обширную базу Амазон-продавцов (4000
емейлов) в Индии и запусти cold outreach".

## Why this pipeline looks nothing like mx-sellers / uk-sellers

Those two scrape the marketplace itself. That does not work here:

- **amazon.in seller pages carry no email.** `/sp?seller=<ID>` returns a shell
  whose "Detailed Seller Information" block is loaded client-side, and the
  legacy `/gp/aag/details` and `at-a-glance` endpoints now just redirect. Even
  with the block rendered you get a business name and address, never an address
  you can mail. `/s?k=` search 503s after the first request from a residential
  IP, so brand-level verification against Amazon is not available in bulk
  either (DuckDuckGo `site:amazon.in` rate-limits after ~60 queries).
- So the sellers are reached through **their own websites**, which do publish
  emails, and the job becomes: enumerate Indian online shops at scale.

## The funnel

| stage | script | what it does | result |
|---|---|---|---|
| 0 | `in0_universe.py` | CrUX top-1M origins **for India** (free, traffic-ranked) minus marketplaces/media/gov/edu | 150k `.in` + 539k `.com`-etc |
| 1 | `in1_dns.py` | raw-UDP DNS over the whole universe, ~2,300 lookups/s | 688k A records, platform tagged by IP |
| 2 | `in2_crawl.py` | async homepage crawl + contact-page chase, extracts emails and signals | 687,719 crawled, 110k with an address |
| 2b | `in2b_platform.py` | is a **store engine** installed (Shopify/WooCommerce/Magento/…)? | 68,290 shops |
| 2c | `in2c_retail.py` | does it sell **physical goods** (shipping/COD/returns, no service verticals)? | 34,249 retailers |
| 3 | `in3_build_csv.py` | clean, MX-validate, tier, dedupe vs all of `outreach/` | **21,040 leads**, 4,000 shipped |

`in1_serp.py` is a DataForSEO SERP discovery grid, parked: the shared DataForSEO
balance went negative mid-build (another pipeline drained it), and CrUX turned
out to be both free and larger. Keep it for a round where the balance is topped
up — 1,090 queries, ~$5.

## What the measurements said (worth knowing before repeating this)

- **Brute force over the popular Indian web is the wrong funnel.** The first 400
  `.in` domains by traffic qualified 0.5%: the head of the list is news, banks,
  services. The head is also where Decathlon/Levi's/Mamaearth live, so stage 3
  now skips the top 4,000 ranks outright — enterprise `care@` queues are not
  buying a $49/mo autopilot.
- **9% of random `.in` domains resolve to Shopify** (23.227.38.0/24), and a DNS
  lookup is ~100x cheaper than an HTTP GET. Platform-by-IP is the cheap way in,
  but it undercounts badly: in the end WooCommerce (10k) outnumbered Shopify
  (6k) among candidates, and Cloudflare-fronted shops hide their platform
  entirely. Detect the engine in the HTML, use DNS only to prioritise.
- **72% of Indian Shopify stores publish an email** once contact pages are
  chased. Homepage-only was 43%.
- **Only ~2.4% of them link to Amazon.** That is not evidence they don't sell
  there — D2C stores suppress marketplace links on purpose. Hence the tiers.
- **A store engine is not a shop.** Coaching institutes, spas, hotels, NGOs and
  marketing agencies all run WooCommerce; a cart+price test let a government
  labour-board portal and a tech-news site into the list. Stage 2c exists
  because of that.

## Lead tiers

- **A — 219** explicit Amazon product/store link or "buy on Amazon" copy.
- **B — 377** bare `amazon.in` / `amazon.com` mention.
- **C — 20,444** Indian physical-goods store, no Amazon evidence on the site.

The shipped 4,000 = all of A + all of B + the top 3,404 of C, ranked by branded
(non-freemail) address first, then traffic rank. One address per company —
never two mailboxes at the same shop, which doubles complaint risk on shared
sending mailboxes for no extra reach.

**Tier C is a judgement call, and it is the reason the copy self-qualifies.**
Step 1 opens with "if Amazon is one of your channels" rather than asserting that
the reader sells on Amazon, because for tier C we genuinely cannot verify it.
If reply data shows tier C converting badly, rebuild with `--min-tier B` and
grow the pool with more `.com` crawling instead.

## Performance notes (the crawler was 20x too slow at first)

Both fixed in `in2_crawl.py`, both worth remembering:

- aiohttp's default resolver runs `getaddrinfo` on a ~14-thread pool; over dead
  domains that throttled the crawl to **under 1 host/s**. `DictResolver` feeds
  it stage-1's A records instead.
- `EMAIL_RE.findall()` over a whole page is **quadratic** — the local-part class
  eats an inline base64 blob before backtracking to find an "@" — costing
  ~120ms/page, and a bare `\s+at\s+` munged-email alternation cost as much
  again. With an "@"-anchored window scan and bracketed-only munging, the crawl
  went 2/s → **47/s per process** (~185/s across 4 shards). The CPU-blocked
  event loop was also what made 44% of healthy hosts "time out"; success went
  56% → 99%.

## Address hygiene applied in stage 3

Role accounts (careers/hr/legal/nodal/…), `%20`-prefixed and `%3cstrong%3e`
URL-encoding artifacts, `info@www.brand.in` (mail domains have no www label),
plus-addressed crawler traps (`+claude-searchbot@anthropic.com` was in there),
social-network handles, and every address already present anywhere in
`outreach/` (40,405 of them). Then an MX query per email domain — that alone
dropped ~7%.

## Campaign

`sequence-sellers-in.md` — en-IN, 5 steps (waits 3/4/5/4) + A/B on step 1 +
reply handler. English and USD by design; the cost comparison is in rupees
(₹15,000–40,000/mo is what PPC help actually costs in India — the US
"$4K–8.5K/mo specialist" line would out an unedited template instantly).

Instantly campaign **«Daniks.AI — Amazon Sellers India»**, id
`637c42b4-96a0-4d21-8abd-537dc9fe173f`, **ACTIVE since 2026-08-12**, Mon–Fri
09:00–18:00 `Asia/Kolkata`, 19 mailboxes that no other active campaign was using
(~470/day spare capacity), daily limit 250, stop-on-reply on, tracking off,
text-only. Workspace contact quota is fine — the plan was raised to 50,000 and
only ~25,000 were used.

## Import: done — 5,234 leads in the campaign

`in4_import.py` does it with an Instantly API key (Settings → Integrations; the
value is shown once at creation). Key `in-sellers-import` exists in the
workspace — revoke it there if it is no longer wanted. The key is read from a
file, never argv, and is not stored in this repo.

```bash
python3 outreach/in-sellers/in4_import.py --key-file ~/.instantly_key \
    --csv data/instantly_IN_SELLERS.csv
python3 outreach/in-sellers/in4_import.py --key-file ~/.instantly_key --verify
python3 outreach/in-sellers/in4_import.py --key-file ~/.instantly_key \
    --prune-against data/instantly_IN_POOL.csv --apply
```

Gotchas: `api.instantly.ai` sits behind Cloudflare and **403s the default
python-urllib User-Agent** — send a browser one. There is no bulk endpoint, so
4,000 leads take ~35 min at 8 workers. And the response's `campaign` field is
*not* a reliable added-vs-skipped signal on the public API (it reported all 4,000
as "added" while the server silently deduped) — trust `--verify` instead.

`--prune-against` removes leads the current filter set would no longer accept:
the pool CSV is every address that survives every filter, so "in the campaign but
not in the pool" is exactly the reject list. It also catches second addresses at
a company whose chosen address changed between builds. One DELETE call clears at
most ~50, so run it twice.

**Final state:** 5,234 leads = the 4,000 shipped list plus 1,234 still-valid
addresses from earlier import rounds; every one of them is in the 21,040 pool.

### Bug worth remembering (it cost ~3,400 of the best leads for a while)

The truncated-local filter rejects a local part that is a tail of a role word
(`are@` from "care", `ndia@` from "india"). Adding `customersupport` and
`customercare` to that word list silently made it reject every legitimate
`support@`, `care@`, `service@` and `mail@` — the most common valid addresses
there are. The pool fell 21,040 → 17,621 and a prune dry-run happily proposed
deleting `support@aquaultra.in` and friends. The test must skip locals that are
themselves role words.

## Historical: why the first 1,972 went in through the browser

`data/instantly_IN_SELLERS.csv` is the shipped 4,000; `data/instantly_IN_POOL.csv`
is the full 21,040 pool for top-ups.

The first round had no API key, and the transport options were all dead ends. Instantly has no bulk-insert endpoint (only
`POST /api/v2/leads`, one lead per call), the internal API authenticates by
session cookie, and there is no way to hand a local file to the browser tab:

- `fetch('http://127.0.0.1:…')` from the https app — blocked as mixed content.
- clipboard → `navigator.clipboard.readText()` — hangs on a permission prompt
  that renders outside the capturable viewport; a synthetic Cmd+V does not touch
  the system clipboard.
- the `file_upload` browser tool — rejects its own `paths` argument here.
- pasting the addresses into a `javascript_tool` call — works (that is how the
  1,972 got in, 10 workers, zero errors), but it pushes the lead list through
  the model's context, and the shell classifier now (correctly) blocks dumping
  bulk email lists to stdout.

This is why `in4_import.py` exists: with an API key the import runs locally and
the lead list never passes through a browser tab or the model's context at all.
