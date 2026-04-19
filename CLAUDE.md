# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SEO Machine is an open-source Claude Code workspace for creating SEO-optimized blog content. It combines custom commands, specialized agents, and Python-based analytics to research, write, optimize, and publish articles for any business.

## Setup

```bash
pip install -r data_sources/requirements.txt
```

API credentials are configured in `data_sources/config/.env` (GA4, GSC, DataForSEO, WordPress). GA4 service account credentials go in `credentials/ga4-credentials.json`.

## Commands

All commands are defined in `.claude/commands/` and invoked as slash commands:

- `/research [topic]` - Keyword/competitor research, generates brief in `research/`
- `/write [topic]` - Create full article in `drafts/`, auto-triggers optimization agents
- `/rewrite [topic]` - Update existing content, saves to `rewrites/`
- `/optimize [file]` - Final SEO polish pass
- `/analyze-existing [URL or file]` - Content health audit
- `/performance-review` - Analytics-driven content priorities
- `/publish-draft [file]` - Publish to WordPress via REST API
- `/article [topic]` - Simplified article creation
- `/cluster [topic]` - Build complete topic cluster strategy with pillar + supporting articles + linking map
- `/priorities` - Content prioritization matrix
- `/research-serp`, `/research-gaps`, `/research-trending`, `/research-performance`, `/research-topics` - Specialized research commands
- `/research-ai-citations [topic]` - AI citation audit: generates prompts, clusters them, audits which sources AI cites
- `/repurpose [file]` - Adapts article for LinkedIn, Medium, Reddit, Quora distribution
- `/landing-write`, `/landing-audit`, `/landing-research`, `/landing-publish`, `/landing-competitor` - Landing page commands
- `/daily-publish [arg]` - End-to-end automated pipeline: topic pick → research → write → optimize → image → publish to target Astro repo → commit/push. Four input modes: (A) autonomous, (B) YouTube URL/ID, (C) URL + transcript file, (D) transcript file only. See `.claude/commands/daily-publish.md`. Designed for `claude -p` / cron.

## Architecture

### Command-Agent Model

**Commands** (`.claude/commands/`) orchestrate workflows. **Agents** (`.claude/agents/`) are specialized roles invoked by commands. After `/write`, these agents auto-run: SEO Optimizer, Meta Creator, Internal Linker, Keyword Mapper.

Key agents: `content-analyzer.md`, `seo-optimizer.md`, `meta-creator.md`, `internal-linker.md`, `keyword-mapper.md`, `editor.md`, `headline-generator.md`, `cro-analyst.md`, `performance.md`, `cluster-strategist.md`.

### Python Analysis Pipeline

Located in `data_sources/modules/`. The Content Analyzer chains:
1. `search_intent_analyzer.py` - Query intent classification
2. `keyword_analyzer.py` - Density, distribution, stuffing detection
3. `content_length_comparator.py` - Benchmarks against top 10 SERP results
4. `readability_scorer.py` - Flesch Reading Ease, grade level
5. `seo_quality_rater.py` - Comprehensive 0-100 SEO score

### Data Integrations

- `google_analytics.py` - GA4 traffic/engagement data
- `google_search_console.py` - Rankings and impressions
- `dataforseo.py` - SERP positions, keyword metrics
- `data_aggregator.py` - Combines all sources into unified analytics
- `wordpress_publisher.py` - Publishes to WordPress with Yoast SEO metadata

### Opportunity Scoring

`opportunity_scorer.py` uses 8 weighted factors: Volume (25%), Position (20%), Intent (20%), Competition (15%), Cluster (10%), CTR (5%), Freshness (5%), Trend (5%).

## Running Python Scripts

```bash
# Research & analysis scripts (run from repo root)
python3 research_quick_wins.py
python3 research_competitor_gaps.py
python3 research_performance_matrix.py
python3 research_priorities_comprehensive.py
python3 research_serp_analysis.py
python3 research_topic_clusters.py
python3 research_trending.py
python3 seo_baseline_analysis.py
python3 seo_bofu_rankings.py
python3 seo_competitor_analysis.py

# Test API connectivity
python3 test_dataforseo.py
```

## Content Pipeline

`topics/` (ideas) → `research/` (briefs) → `drafts/` (articles) → `review-required/` (pending review) → `published/` (final)

Rewrites go to `rewrites/`. Landing pages go to `landing-pages/`. Audits go to `audits/`. Repurposed content goes to `repurposed/`.

## Context Files

`context/` contains brand guidelines that inform all content generation:
- `brand-voice.md` - Tone, messaging pillars
- `style-guide.md` - Grammar, formatting standards
- `seo-guidelines.md` - Keyword and structure rules
- `internal-links-map.md` - Key pages for internal linking
- `features.md` - Product features
- `competitor-analysis.md` - Competitive intelligence
- `cro-best-practices.md` - Conversion optimization guidelines
- `ai-citation-targets.md` - Directories/platforms where your brand should be cited by AI tools
- `reddit-strategy.md` - Reddit engagement strategy for AI SEO and community visibility

## TheFBAGirl Publishing Setup (this workspace's target)

This workspace publishes to the **thefbagirl.com** Astro site, not WordPress. The WordPress integration upstream in SEO Machine is unused here.

- **Target repo**: `/Users/ync/poryadok/sources/thefbagirl-com` (Astro 6 + Tailwind 4, deployed to Cloudflare Pages on push to `main` via `.github/workflows/deploy.yml`). Remote: `git@github.com:daniks-ai/thefbagirl-com.git`. Push works as GitHub user `ekaterina-rubtcova`.
- **Content format**: `.mdx` files in `src/content/{blog,tutorials,news,reviews,lifehacks}/`. Frontmatter must validate against the Zod schema in the target repo's `src/content.config.ts` — strict category enum, `title` ≤70 chars, `description` ≤160 chars, `coverImage` path required.
- **Cover images**: Generated via Gemini Nano Banana 2 (`gemini-3.1-flash-image-preview`). `GEMINI_API_KEY` lives in the **target repo's** `.env`, not this workspace. Photorealistic DSLR-style only — never cartoon/illustration.
- **Brand**: TheFBAGirl / Katia / YouTube `@AmazonFBAGirl` (channel ID `UCPx3JO2j6hycfM_zGSqbYPA`). Amazon FBA education niche. Every article should pair with or reference the YouTube channel; CTAs prefer YouTube subscribe > newsletter > related article > affiliate. Never push a course.
- **Author avatar**: `src/assets/images/fba-girl-avatar.jpg` is `.gitignored` and fetched at build time via `scripts/fetch-youtube.ts` using `YOUTUBE_API_KEY`. Do not commit the JPG. Local builds without the key fail on this file; CI has the secret.
- **Video → article workflow**: `/daily-publish` Modes B/C/D use the YouTube video transcript as the primary voice source. Mode B scrapes via `youtube-transcript-api`; Modes C/D use a user-provided transcript file (`.txt` / `.md` / `.json` / `.srt` / `.vtt`), which is higher-fidelity and preferred when available.
- **Context files are populated** (not templates) with TheFBAGirl-specific voice, keywords, competitors, and style rules. When writing, match `context/writing-examples.md` as ground truth for voice — no AI-smell words, no guru language, first-person operator voice.

## Runtime setup notes

- Python deps include `textstat`, `numpy`, `scikit-learn`, `beautifulsoup4`, `youtube-transcript-api`, and Google API client libs. Install with `pip install -r data_sources/requirements.txt`.
- `.claude/settings.json` pre-grants the bash patterns needed for unattended `/daily-publish` runs (python, pnpm, node, curl to Google/YouTube/DataForSEO domains, safe git ops). Destructive ops (`rm -rf`, `git push --force`, `git reset --hard`) are explicitly denied.
- Known fixes applied to the upstream codebase: `content_scrubber.py` stats dict now initializes `ai_phrases_replaced`. Still-imperfect: the scrubber's `[Uu]tilize(?:s|d)?` regex collapses "utilized" → "use" (losing past-tense) — watch for broken grammar after scrub.
