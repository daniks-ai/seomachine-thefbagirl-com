# Daily MX-seller collection — routine runbook

You are a scheduled run of the "slow daily" Amazon-México seller collection for the
daniks.ai outreach. Each run does ONE small, gentle scraping burst (bounded, so it
stops before Amazon hard-throttles the IP), enriches the new sellers to emails, and
adds any genuinely-new emails to the live Instantly campaign. Slow but steady.

Repo dir: `outreach/mx-sellers/` (run all commands from the repo root
`/Users/ync/poryadok/sources/seomachine-thefbagirl-com`).
Full context: read `outreach/mx-sellers/README.md` and memory `mx-sellers-outreach`.

**Hard dependency:** this needs the in-app **Browser pane** (real residential IP +
cookies — plain curl gets 503 from Amazon) and, for the last step, the user's
logged-in **Chrome** (Instantly). If neither browser is reachable, do steps you can
and report what was skipped. Do NOT commit/push anything — lead data stays local.

## Steps

1. **Open the browser pane** on Amazon MX:
   `preview_start {url: "https://www.amazon.com.mx/"}` (or navigate an existing tab there).

2. **Inject the worker**: Read `outreach/mx-sellers/browser_worker.js` and run its full
   contents via the Browser `javascript_tool` on that tab. Expect `"mx-worker-installed"`.

3. **Seed already-seen sellers** (so you don't re-profile old ones): read
   `outreach/mx-sellers/data/seen_sellers.txt`. Inject via
   `window.__seedSeen([...ids])`. If the file has more than ~1500 ids, call
   `__seedSeen` in chunks of ~1500.

3b. **Seed a fresh, diverse ASIN chunk** (so you don't just re-crawl bestsellers,
   which saturates on already-seen sellers). Get the next unprocessed chunk from the
   pre-harvested pool of ~23k products and advance its cursor:
   ```bash
   python3 outreach/mx-sellers/daily_collect.py --next-asins 400
   ```
   (400 ≈ what one bounded burst consumes; the cursor persists so each day advances
   through the pool. Pool ~23k → ~2 months of fresh products before it wraps.)
   Inject the printed ASINs: `window.__seedAsins([...asins])`.
   This is the main lever for finding NEW sellers day over day.

4. **Start**: `window.__mxStart()` → `"started"`.

5. **Poll** `window.__mxStatus()` every ~90 seconds (use a Bash sleep-until loop
   between polls, not a busy wait). It self-stops after **12 new MX sellers, 3
   captcha hits, or 14 minutes** — whichever first. Wait until `finished:true`
   (or ~16 min elapsed, then call `window.__mxStop()`).
   - If `stats.cap >= 3` and `newMx` is 0-1, Amazon is throttling today — that's
     expected; just proceed with whatever was collected (possibly nothing).

6. **Drain**: `window.__mxDrain()` → JSON `{mx:[...], seen:[...]}`. Write it verbatim
   to a temp file, e.g. `/tmp/mx_drain.json`.

7. **Enrich + build** (one command; does domain-discovery → email-harvest →
   strict-validated CSV, all repo-relative, dedup vs everything already collected):
   ```bash
   python3 outreach/mx-sellers/daily_collect.py < /tmp/mx_drain.json
   ```
   It prints a summary line and, between `=== NEW_EMAILS_TO_ADD ===` and `=== END ===`,
   the list of **new** validated emails not yet in the campaign. Often 0-5 per day.

8. **Add new emails to the campaign** (only if the list is non-empty AND Chrome is
   connected to Instantly): in Chrome open
   `https://app.instantly.ai/app/campaign/43f07eca-6cdf-4ce1-866e-4f2c1b0f9038/leads`
   → **Add Leads** → **Enter Emails Manually** → paste the new emails (one per line,
   plain — the sequence uses literal fallbacks, no columns needed) → keep
   "check duplicates across all" ON, "Verify leads" OFF → **Import emails** → **Ok**.
   Do NOT touch the Sequences tab (its rich-text editor is fragile — see README gotchas).

9. **Mark them added** so tomorrow's run won't re-surface them — append the imported
   emails to the ledger:
   ```bash
   printf '%s\n' <email1> <email2> ... >> outreach/mx-sellers/data/campaign_added_emails.txt
   ```
   (If step 8 was skipped because Chrome wasn't connected, do NOT mark them — leave
   them for the next run / manual add, and say so in the report.)

10. **Report** one short line: sellers seen, new MX sellers, new emails found, how many
    imported to the campaign, and whether Amazon throttled. Run
    `python3 outreach/mx-sellers/daily_collect.py --status` for the running totals.

## Notes
- Keep it gentle. Never remove the bounded stop conditions or lower the sleeps — the
  whole point is to stay under Amazon's per-IP throttle so this can run for weeks.
- The campaign id is `43f07eca-6cdf-4ce1-866e-4f2c1b0f9038` ("Daniks.AI — Amazon Sellers MX").
- Yield is naturally low and decays as popular sellers saturate (~2-5 new emails/day,
  less over time). That's the accepted trade-off for a no-proxy, no-cost drip.
