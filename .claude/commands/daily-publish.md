# Daily Auto-Publish Pipeline

Fully automated pipeline: pick a topic, research, write, review, generate image, publish to the [thefbagirl.com](https://thefbagirl.com) Astro repo, commit & push. CI/CD deploys automatically.

## Usage
This command is designed to run unattended via `claude -p`. **Do NOT ask the user any questions. Make all decisions autonomously.** If a step fails critically, save progress and stop — leave a clear status message.

## Target repositories
- **Content workspace** (this repo): `/Users/ync/poryadok/sources/seomachine-thefbagirl-com`
- **Website source repo** (publish target): `/Users/ync/poryadok/sources/thefbagirl-com` (Astro 6 + Tailwind 4, deployed to Cloudflare Pages on push to `main`)

## Key context files to read before starting
Read these once at the start to inform all decisions:
- `context/brand-voice.md` — voice pillars and banned phrases
- `context/style-guide.md` — grammar, formatting, terminology
- `context/features.md` — content-format positioning
- `context/seo-guidelines.md` — length, AI SEO rules, direct-answer-first
- `context/target-keywords.md` — 12 clusters + YouTube video → article pipeline
- `context/writing-examples.md` — voice reference with 5 full articles
- `context/internal-links-map.md` — existing URLs for internal linking
- `context/competitor-analysis.md` — differentiation angles
- `context/ai-citation-targets.md` — AI search optimization
- `CLAUDE.md` — pipeline and command overview

## Full pipeline

Execute these steps in order. Variables in `[brackets]` are filled in as you go.

---

### Step 1: Pick a topic autonomously

Choose the next article topic using this priority order. Never ask the user.

1. **Check `topics/` folder** for any pre-planned topic briefs (files named `[topic].md`).
2. **Check `context/target-keywords.md`** `YouTube Video → Article Pipeline` table for videos with matching articles marked "to create" — these are lowest-effort, highest-quality opportunities because the video already exists.
3. **Check `context/target-keywords.md`** `Keyword Opportunity Pipeline → High Priority` list.
4. **Cross-reference `context/internal-links-map.md`** and the target repo's `src/content/blog/`, `src/content/tutorials/`, `src/content/reviews/`, `src/content/news/`, `src/content/lifehacks/` — **do not duplicate** an already-published slug or near-synonym.

Selection criteria:
- Has a clear primary keyword from `target-keywords.md`.
- Has either a matching YouTube video (preferred) or strong SERP opportunity.
- Has informational or commercial intent relevant to Amazon FBA sellers.
- Complements existing content clusters (reinforces cluster authority).

**Output**: Save `topics/auto-selected-[YYYY-MM-DD].md` with:
- Chosen topic title
- Primary keyword
- Target collection (blog / tutorials / news / reviews / lifehacks)
- Target category enum value (must match the Zod schema in target repo's `src/content.config.ts`)
- YouTube video ID if applicable
- Reasoning (2–3 sentences)
- Suggested file slug (kebab-case, 3–6 words, includes keyword, includes year if time-sensitive)

---

### Step 2: SERP research via DataForSEO

Run the SERP analysis for the primary keyword:

```bash
python3 research_serp_analysis.py "[primary keyword]"
```

This uses DataForSEO credentials from `data_sources/config/.env` and saves a brief to `research/serp-analysis-[keyword].md` (or similar).

Use the output to inform:
- Target word count (match or exceed SERP median for the keyword cluster)
- Dominant content format (listicle, how-to, comparison, etc.)
- SERP features to target (featured snippet format, PAA questions, video carousel)
- Competitor coverage gaps
- Freshness signals (include year if needed)

**If DataForSEO fails** (credentials missing, API error, rate limit), continue with context-file-only planning — do **not** stop. Note the failure in the final summary.

Optionally also run:
```bash
python3 research_competitor_gaps.py
python3 research_topic_clusters.py
```
if the SERP analysis suggests deeper cluster research would help.

---

### Step 3: Write the article

Follow every requirement from `context/seo-guidelines.md`, `context/brand-voice.md`, and `context/style-guide.md`. Match the patterns from `context/writing-examples.md` as the ground truth for voice.

Hard requirements:
- **Word count**: 1,500–2,500 for standard posts, 2,500–4,500 for pillar content. Cap at 3,000 unless pillar.
- **Frontmatter** must validate against the target collection's Zod schema in `/Users/ync/poryadok/sources/thefbagirl-com/src/content.config.ts`. Critical fields:
  - `title` ≤ 70 chars
  - `description` ≤ 160 chars (aim for 150–160)
  - `publishDate` ISO format
  - `category` must match the collection's enum exactly
  - `coverImage: ./images/[slug].jpg`
  - `coverImageAlt` (≤125 chars, keyword natural)
  - `youtubeVideoId` + `youtubeVideoTitle` if a matching video exists
  - `author: "FBA Girl"`
  - `affiliateDisclosure: true` for reviews collection or any article with affiliate links
- **Direct-answer-first**: First 1–2 sentences directly answer the target query (AI SEO). Narrative hook comes after.
- **Key Takeaways block** immediately after intro: blockquote with 3–5 bullets, each a standalone specific claim.
- **H2 structure**: 4–7 sections, at least 2–3 containing the exact primary keyword (not just a partial match).
- **Keyword density**: 1–2%. First 100 words, H1 (via frontmatter `title`), 2+ H2s, conclusion.
- **Mini-stories**: 2–3 scenarios with named characters (Sarah, Mike, Maria, James, etc.) and specific outcomes.
- **Contextual CTAs**: 2–3 distributed throughout. First CTA within first 500 words.
- **Internal links**: 4–5 to articles from `context/internal-links-map.md`. Never link to `/blog/` homepage generically — always a specific article.
- **External links**: 2–3 to authoritative sources (Amazon Seller Central, Amazon Ads, Brand Registry, Amazon Revenue Calculator).
- **YouTube video embed** via `youtubeVideoId` if one exists. Reference the video in-text ("Watch the full walkthrough in the video above").
- **FAQ section**: 4–6 questions in natural prompt language (match how ChatGPT/Perplexity users phrase them).
- **Voice**: First-person operator (Katia). No AI-smell words (see banned list in `brand-voice.md`). No guru language.

**Save**: `drafts/[slug]-[YYYY-MM-DD].md`

---

### Step 4: Scrub AI watermarks

Run the content scrubber to remove invisible Unicode markers and AI-telltale phrases:

```bash
python3 data_sources/modules/content_scrubber.py drafts/[slug]-[YYYY-MM-DD].md
```

This runs in-place and reports stats. Verify the stats output; if it errors, fix and retry.

---

### Step 5: Run the 5 optimization agents

Spawn each agent using the Task tool. Each agent analyzes the scrubbed draft and produces a report in `drafts/`:

1. **content-analyzer** → `drafts/content-analysis-[slug]-[YYYY-MM-DD].md` (master synthesis)
2. **seo-optimizer** → `drafts/seo-report-[slug]-[YYYY-MM-DD].md`
3. **meta-creator** → `drafts/meta-options-[slug]-[YYYY-MM-DD].md`
4. **internal-linker** → `drafts/link-suggestions-[slug]-[YYYY-MM-DD].md`
5. **keyword-mapper** → `drafts/keyword-analysis-[slug]-[YYYY-MM-DD].md`

Invoke them in parallel via the Task tool where possible — they are independent.

---

### Step 6: Apply critical fixes

Consolidate critical + high-priority fixes from the 5 reports. Apply them automatically:

- Swap meta description if the recommended option scores better.
- Add any missing external authority links (aim for 3).
- Add any missing internal links (aim for 4–5 total).
- Rename H2s to include the exact primary keyword where needed to hit 2–3/N ratio.
- Split any sentences over 35 words.
- Convert obvious passive constructions to active voice (target < 20% passive).
- Add the exact primary keyword phrase to one FAQ answer and the final paragraph if missing.

**Do NOT** apply the "missing H1 / missing meta title / missing meta description" flags — those are module false positives for MDX frontmatter. The Astro layout renders H1 and meta from frontmatter.

---

### Step 7: Re-score and decide publish-readiness

```bash
python3 data_sources/modules/content_scorer.py drafts/[slug]-[YYYY-MM-DD].md
```

Quality gate: composite score **≥ 70** to proceed. If below after one revision pass, save with a `_REVIEW_NOTES.md` to `review-required/[slug]-[YYYY-MM-DD].md` and **stop** the pipeline. Emit a status message that lists the blocking issues. Do not publish sub-threshold content.

Re-run the scrubber if Step 6 introduced any em-dashes or AI phrases:
```bash
python3 data_sources/modules/content_scrubber.py drafts/[slug]-[YYYY-MM-DD].md
```

---

### Step 8: Generate the cover image (Gemini Nano Banana 2)

Craft a photorealistic DSLR-style image prompt based on the article topic. Always include this prefix:

```
Photorealistic high-resolution photograph, shot on a professional DSLR camera, natural lighting, shallow depth of field, 16:9 aspect ratio, no text or lettering whatsoever, no illustrations or cartoons, real-world scene.
```

Then a topic-specific scene description. Examples from existing articles:
- Vine/reviews → "Overhead flat-lay of a small brown cardboard shipping box being opened... laptop displaying blurred product-review stars..."
- PPC → "Close-up of a laptop screen displaying advertising analytics charts..."
- Fees → "Close-up of a printed financial statement with highlighted fee line items..."

Generate via Gemini (API key lives in the **target repo's** `.env`, NOT this workspace):

```bash
cd /Users/ync/poryadok/sources/thefbagirl-com && \
export $(grep GEMINI_API_KEY .env | xargs) && \
node -e "
const prompt = '[FULL PROMPT STRING]';
fetch('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key=' + process.env.GEMINI_API_KEY, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    contents: [{ parts: [{ text: 'Generate an image: ' + prompt }] }],
    generationConfig: { responseModalities: ['IMAGE', 'TEXT'] },
  }),
})
.then(r => r.json())
.then(d => {
  const img = d.candidates?.[0]?.content?.parts?.find(p => p.inlineData)?.inlineData?.data;
  if (img) {
    require('fs').writeFileSync('src/content/[collection]/images/[slug].jpg', Buffer.from(img, 'base64'));
    console.log('Image saved');
  } else {
    console.error('No image returned', JSON.stringify(d).slice(0, 500));
    process.exit(1);
  }
});
"
```

Where `[collection]` is `blog`, `tutorials`, `news`, `reviews`, or `lifehacks` — matching the content collection.

If image generation fails (API error, quota), do **not** stop. Fall back:
1. Save a placeholder note to `drafts/_image-pending-[slug].md` with the prompt.
2. Skip to Step 9 but **do not push** — leave commit local, flag in final message that image is missing.

---

### Step 9: Copy article to the target repo

```bash
cp drafts/[slug]-[YYYY-MM-DD].md /Users/ync/poryadok/sources/thefbagirl-com/src/content/[collection]/[slug].mdx
```

**Important**: rename to `.mdx` extension (Astro convention for this site). The filename (slug) should be clean — strip the date suffix used in `drafts/`. The URL slug becomes the filename.

Verify the frontmatter fields match the Zod schema for the target collection. If the schema rejects any field, fix and retry before proceeding.

---

### Step 10: Build verification

Run a local build with the YouTube API key to ensure Astro compiles the new article without schema errors:

```bash
cd /Users/ync/poryadok/sources/thefbagirl-com && \
YOUTUBE_API_KEY=$(grep YOUTUBE_API_KEY /Users/ync/poryadok/sources/seomachine-thefbagirl-com/data_sources/config/.env | cut -d= -f2) \
pnpm run build 2>&1 | tail -30
```

If the build fails with an error related to the new article (schema validation, bad image path, broken frontmatter), **stop and fix**. Do not commit a broken build.

If the build fails with an unrelated error (e.g., avatar issue from another author), note it and continue — do not be blocked by pre-existing breakage.

---

### Step 11: Update internal-links-map.md

In this workspace, edit `context/internal-links-map.md` to add an entry for the new article. Place it under the appropriate collection header:

```markdown
### [Article Title]
- **URL**: https://thefbagirl.com/[collection]/[slug]
- **Primary Topic**: [topic summary]
- **When to Link**: [contexts where this should be referenced]
- **Anchor Text Examples**: "[variant 1]", "[variant 2]", "[variant 3]"
```

This ensures future runs of `/daily-publish` and `/write` can link TO this article from new content.

---

### Step 12: Commit and push

In the **target repo**, stage only the new files (never `-A` or `.`):

```bash
cd /Users/ync/poryadok/sources/thefbagirl-com && \
git add src/content/[collection]/[slug].mdx src/content/[collection]/images/[slug].jpg && \
git status
```

Verify only the intended files are staged. Commit:

```bash
git commit -m "$(cat <<'EOF'
Add [short title]

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Commit style matches repo convention: short imperative title, no body needed. Follow the style of recent commits (look at `git log --oneline -10`).

Push to origin main:

```bash
git push origin main
```

The `deploy.yml` GitHub Actions workflow builds the Astro site with the YOUTUBE_API_KEY secret (which fetches the author avatar at build time) and deploys to Cloudflare Pages on the `thefbagirl-com` project.

---

### Step 13: Commit workspace changes

Also commit the workspace updates (new draft, reports, topic file, updated internal-links-map) so the content pipeline is reproducible:

```bash
cd /Users/ync/poryadok/sources/seomachine-thefbagirl-com && \
git add topics/auto-selected-*.md drafts/[slug]-*.md drafts/content-analysis-* drafts/seo-report-* drafts/meta-options-* drafts/link-suggestions-* drafts/keyword-analysis-* context/internal-links-map.md research/serp-analysis-* 2>/dev/null && \
git status
```

Commit only if there are changes (skip if this workspace has no remote or should not be pushed — check `git remote -v` first).

---

### Step 14: Move draft to published

After a successful push to the target repo:

```bash
mv drafts/[slug]-[YYYY-MM-DD].md published/[slug]-[YYYY-MM-DD].md
```

This keeps `drafts/` clean for the next run.

---

## Final output

Emit a concise status message with:
- Chosen topic + primary keyword
- Final composite quality score
- Final SEO score
- Word count
- Cover image: generated ✓ / pending ⚠
- Commit SHA + push status
- URL where the article will be live (`https://thefbagirl.com/[collection]/[slug]`)
- Any warnings (DataForSEO unavailable, module false positives ignored, etc.)

If the run was halted before publish (quality gate fail, image error), state exactly where and why.

---

## Notes for unattended execution

- **Never ask the user** for confirmation. All decisions are autonomous per this spec.
- **Never skip hooks**, never bypass signing, never use `--force` on push.
- **Never** run `git push --force`, `git reset --hard`, `rm -rf`, or `git clean -fd`.
- Permissions are pre-granted in `.claude/settings.json` — the command runs without Bash permission prompts.
- If a required file is missing or a module cannot be imported, install the dep and retry once (using `pip3 install` for Python). If that fails, stop and report.
- If the target repo has uncommitted work from another source (`git status` shows unexpected changes), stop and report — do not commit over it.

## Scheduling

To run daily, set up a cron or `launchd` job that invokes:

```bash
cd /Users/ync/poryadok/sources/seomachine-thefbagirl-com && claude -p "/daily-publish"
```

Recommended cadence: once per day, off-peak hours (e.g., 4am local time) so any issues surface with time to review before the workday.
