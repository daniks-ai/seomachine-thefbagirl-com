# Daily UK-seller collection — routine runbook

You are a scheduled run of the "slow daily" Amazon-UK seller collection for the
daniks.ai outreach. Each run does ONE small, gentle scraping burst (bounded, so it
stops before Amazon hard-throttles the IP), enriches the new sellers to emails, and
adds any genuinely-new emails to the live Instantly campaign. Slow but steady.

Repo dir: `outreach/uk-sellers/` (run all commands from the repo root
`/Users/ync/poryadok/sources/seomachine-thefbagirl-com`).
Full context: read `outreach/uk-sellers/README.md` and memory `uk-sellers-outreach`.

**Hard dependency:** this needs the in-app **Browser pane** (real residential IP +
cookies — plain curl gets 503 from Amazon) and, for the last step, the user's
logged-in **Chrome** (Instantly). If neither browser is reachable, do steps you can
and report what was skipped. Do NOT commit/push anything — lead data stays local.

## Steps

1. **Open the browser pane** on Amazon UK:
   `preview_start {url: "https://www.amazon.co.uk/"}` (or navigate an existing tab there).

2. **Inject the worker**: Read `outreach/uk-sellers/browser_worker.js` and run its full
   contents via the Browser `javascript_tool` on that tab. Expect `"uk-worker-installed"`.
   NOTE: the worker's default bounds are 40 new sellers / 4 captchas / 25 min; for the
   daily drip that's fine — it almost always stops on captchas first.

3. **Seed already-seen sellers** (so you don't re-profile old ones): read
   `outreach/uk-sellers/data/seen_sellers.txt`. Inject via
   `window.__seedSeen([...ids])`. If the file has more than ~1500 ids, call
   `__seedSeen` in chunks of ~1500.

4. **Start**: `window.__ukStart()` → `"started"`.

5. **Poll** `window.__ukStatus()` every ~90 seconds (background sleep between polls,
   not a busy wait). Wait until `finished:true` (or ~27 min elapsed, then call
   `window.__ukStop()`).
   - If `stats.cap >= 3` and `newUk` is 0-1, Amazon is throttling today — that's
     expected; just proceed with whatever was collected (possibly nothing).

6. **Drain**: `window.__ukDrain()` → JSON `{uk:[...], seen:[...]}`. Write it verbatim
   to a scratchpad file, e.g. `<scratchpad>/uk_drain.json`.

7. **Enrich + build** (one command; does domain-discovery → email-harvest →
   strict-validated CSV, all repo-relative, dedup vs everything already collected):
   ```bash
   python3 outreach/uk-sellers/daily_collect.py < <scratchpad>/uk_drain.json
   ```
   It prints a summary line and, between `=== NEW_EMAILS_TO_ADD ===` and `=== END ===`,
   the list of **new** validated emails not yet in the campaign. Often 0-5 per day.

8. **Add new emails to the campaign** (only if the list is non-empty AND Chrome is
   connected to Instantly): in Chrome open
   `https://app.instantly.ai/app/campaign/addb69b7-b109-4e28-a24b-badb61e53524/leads`
   → **Add Leads** → **Enter Emails Manually** → paste the new emails (one per line,
   plain — the sequence uses literal fallbacks, no columns needed) → keep
   "check duplicates across all" ON, "Verify leads" OFF → **Import emails** → **Ok**.
   Do NOT touch the Sequences tab (its rich-text editor is fragile — see mx-sellers
   README gotchas; same applies here).

9. **Mark them added** so tomorrow's run won't re-surface them — append the imported
   emails to the ledger:
   ```bash
   printf '%s\n' <email1> <email2> ... >> outreach/uk-sellers/data/campaign_added_emails.txt
   ```
   (If step 8 was skipped because Chrome wasn't connected, do NOT mark them — leave
   them for the next run / manual add, and say so in the report.)

10. **Report** one short line: sellers seen, new GB sellers, new emails found, how many
    imported to the campaign, and whether Amazon throttled. Run
    `python3 outreach/uk-sellers/daily_collect.py --status` for the running totals.

## Notes
- Keep it gentle. Never remove the bounded stop conditions or lower the sleeps — the
  whole point is to stay under Amazon's per-IP throttle so this can run for weeks.
- The campaign id is `addb69b7-b109-4e28-a24b-badb61e53524` ("Daniks.AI — Amazon Sellers UK").
- This shares the residential IP with the MX daily routine (`outreach/mx-sellers/`,
  scheduled ~12:24 local) — keep the two runs at least an hour apart.
- Yield is naturally low (~30-50% of profiled sellers on amazon.co.uk are GB, but only
  ~⅙ convert to a corroborated email). Strict validation is intentional — protects the
  shared senders; do not loosen `build_uk_csv.py` checks to inflate volume.
