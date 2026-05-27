# SEO Guidelines for TheFBAGirl Content

This document outlines SEO requirements and best practices for all TheFBAGirl content. It works alongside `brand-voice.md` (voice), `style-guide.md` (style), `target-keywords.md` (keywords), and `internal-links-map.md` (links).

TheFBAGirl competes in the Amazon FBA education niche against high-DR tool blogs (Jungle Scout, Helium 10) and established operator brands (EcomCrew). Our SEO edge comes from: operator voice, time-current content, YouTube/blog pairing, honest tool reviews, and underserved niches (EU FBA, 2026 policy changes). These guidelines prioritize those edges.

## Content Length Requirements

### Target Word Counts
- **Standard blog post**: 1,500–2,500 words (target: 2,000).
- **Pillar / comprehensive guides**: 2,500–4,500 words.
- **Tutorials**: 1,500–2,500 words (match to complexity).
- **Reviews**: 1,500–2,000 words minimum (honest pros/cons demand depth).
- **News articles**: 800–1,500 words (time-sensitive; brevity is a feature).
- **Lifehacks**: 1,000–1,800 words (list + supporting detail).

### Maximum Length
- **Most articles**: Cap at 3,000 words. Longer = lower finish rate.
- **Pillar content**: Cap at 4,500 words. Break larger topics into a series.
- Quality > quantity. A 2,000-word article with real numbers beats a 3,500-word article padded with fluff.

### Why Length Matters (Realistically)
- Longer content correlates with higher rankings *only when depth is real*.
- Padded content loses to concise content in 2026's helpful-content-era SERPs.
- Specific numbers, frameworks, and examples make length justified.

## Keyword Optimization

### Keyword Research Requirements
Before writing any article:
1. Identify the primary keyword from `target-keywords.md`.
2. Confirm search intent (informational / commercial / transactional).
3. Pull SERP data via `/research-serp [keyword]` (DataForSEO integration).
4. Identify 3–5 secondary keywords from the same cluster.
5. List 5–10 LSI/semantic terms.
6. Check competitor coverage (`competitor-analysis.md`).

### Keyword Density Guidelines
- **Primary keyword**: 1–2% density.
  - 2,000-word article → 20–40 uses of the primary keyword or close variants.
  - Natural integration only. Never force it.
- **Secondary keywords**: 0.5–1% each.
- **LSI keywords**: Naturally sprinkled. Don't count; just include the terms a topical expert would use.

### Critical Keyword Placement
Primary keyword MUST appear in:
- [ ] H1 headline (naturally, preferably near the front).
- [ ] First 100 words of the article.
- [ ] At least 2–3 H2 subheadings (or close variations).
- [ ] Last paragraph / conclusion.
- [ ] Meta title (frontmatter `title`).
- [ ] Meta description (frontmatter `description`).
- [ ] URL slug (matches file name).
- [ ] At least one `alt` text on an image where natural.

### Keyword Integration Best Practices
- **Write for humans first**: Draft the article, then adjust placement.
- **Use variations**: "Amazon PPC strategy" → "PPC campaigns on Amazon" → "Amazon ads."
- **Question formats**: "How to lower ACoS" alongside "lowering ACoS on Amazon."
- **Semantic family**: For "Amazon PPC," include ACoS, TACoS, Sponsored Products, bid, campaign, placement, keyword match types.

### Keyword Stuffing — Forbidden

❌ "Amazon PPC strategy matters. With the right Amazon PPC strategy, Amazon sellers can use Amazon PPC strategy to grow Amazon PPC campaigns. My Amazon PPC strategy guide will show you Amazon PPC strategy tactics."

✅ "Amazon PPC is the engine that launches most private label products — and it's also where sellers burn the most money. The three-phase framework below is how I structure every campaign, whether I'm launching a new ASIN or optimizing a three-year-old listing."

## Content Structure Requirements

### Heading Hierarchy

#### H1 (Title) — Frontmatter `title`
- **One H1 per article** — the frontmatter title.
- Include primary keyword naturally.
- **Max 70 characters** (content collection schema enforces this).
- Benefit-focused or curiosity-hook.
- Must answer "why should I read this?" in itself.

#### H2 (Main Sections)
- **4–7 H2 sections** in standard articles.
- At least 2–3 should include keyword or close variation.
- Sentence case by default (see `style-guide.md`); Title Case when naming a framework ("The Three-Phase Campaign Structure").
- H2s should read as a table of contents — a skimmer should get the article's arc from headers alone.

#### H3 (Subsections)
- Nested under H2s. Never skip H2 → H4.
- Break complex sections into 2–4 subsections.
- More specific than H2s.

### Article Structure Template

```markdown
# [H1: Compelling Title with Primary Keyword — ≤70 chars]

[Opening hook — 1-2 sentences. Specific scenario, surprising number, or personal admission.]

[Problem statement — 2-3 sentences. Name the pain.]

[Promise — 2-3 sentences. What they'll learn/do.]

[Direct-answer sentence for AI SEO if "best/how/top" query — see AI Search Optimization below.]

> **Key Takeaways**
> - [Specific claim 1]
> - [Specific claim 2]
> - [Specific claim 3]
> - [Specific claim 4]

## [H2: First Main Section — Keyword Variation]

[Body: 250-350 words. Specific examples, numbers, frameworks.]

### [H3: Subsection if section > 350 words]

## [H2: Second Main Section]

[Body]

## [H2: Third Main Section — Keyword Variation]

[Body]

## [H2: Common Mistakes / Pitfalls] (optional but high-value)

## [H2: Your Next Steps / Conclusion]

[Recap — 2-4 bullet points or short paragraph]
[Next step — what to do this week]
[CTA — YouTube video / newsletter / related article]
```

## Meta Elements

### Meta Title (frontmatter `title`)
- **Length**: ≤ 70 characters (schema max). Aim for 50–60 to ensure no SERP truncation.
- **Primary keyword**: Included naturally near the front when possible.
- **Compelling**: Encourages clicks. Not "Blog Post About PPC."
- **Unique**: Different from every other article on thefbagirl.com.

**Formats that work**:
- `[Primary Keyword]: [Benefit or Specific Promise]`
- `How to [Goal] (Without [Common Mistake])`
- `[Number] [Specific Thing] That [Outcome]`
- `[Topic] in 2026: [Honest Take / Specific Angle]`

**Examples**:
- ✅ "The Ultimate Amazon PPC Strategy Guide for 2026"
- ✅ "7 Listing Optimization Tips That Actually Boost Sales"
- ✅ "Amazon FBA: US vs Europe — The Brutal Truth"
- ❌ "Amazon PPC Tips" (too vague)
- ❌ "Learn Everything About Amazon PPC Strategy and Grow Your Business Today Faster" (too long)

### Meta Description (frontmatter `description`)
- **Length**: ≤ 160 characters (schema max). Aim for 150–160.
- **Primary keyword**: Include naturally.
- **Value proposition**: Clear benefit.
- **Call-to-action verb**: Learn, Master, Discover, Get, Find out.
- **Complete sentence** — no cut-offs.

**Formula**: `[Promise / Hook]. [What's inside — specific]. [Optional CTA verb].`

**Examples**:
- ✅ "Master Amazon PPC advertising with proven strategies for keyword targeting, campaign structure, ACoS optimization, and bid management." (153 chars)
- ✅ "My honest comparison of selling on Amazon US versus Europe, including the mistakes I made starting in Germany." (115 chars)
- ❌ "This is a blog post about Amazon FBA where we discuss many topics for sellers." (vague, no value prop)

### URL Slug
- **Requirements**:
  - Lowercase only.
  - Hyphens (never underscores).
  - Includes primary keyword.
  - 3–6 words.
  - Matches the MDX file name exactly.

**Examples**:
- ✅ `/blog/amazon-ppc-strategy-guide-2026`
- ✅ `/blog/the-fifty-cent-mistake-amazon-sellers`
- ✅ `/reviews/helium-10-review`
- ❌ `/blog/post-2026-03-22-ppc-strategy-guide`
- ❌ `/blog/amazon_ppc_strategy` (underscores)

## Internal Linking Strategy

### Requirements (adjusted for TheFBAGirl)
- **Minimum**: 3 internal links per article.
- **Optimal**: 4–5 internal links.
- **Maximum**: 7 internal links (only for pillar articles > 3,000 words).

### Link Types

#### 1. Pillar Content (1–2 links)
- Link to cluster pillars on related topics. See `internal-links-map.md`.

#### 2. Related Blog / Tutorial / Review (2–3 links)
- Cross-collection linking is encouraged: Blog → Tutorial, Tutorial → Review, News → Blog.

#### 3. News (when time-sensitive context helps)
- Link to `/news/amazon-fee-changes-2026` (or the current-year news pillar) when fees, policy, or rules are referenced.

#### 4. Review (when a tool is mentioned)
- Don't mention a tool without linking to the review.

### Anchor Text
- ✅ Descriptive: "my [three-phase campaign structure]"
- ✅ Natural: "I wrote up [the True COGS breakdown] with a worked example"
- ❌ Generic: "click here" / "read more"
- ❌ Repeat exact-match anchors across an article (vary the phrasing).

### Link Placement
- Place at least one internal link in the first 500 words.
- Distribute throughout the article.
- Never more than 2 links per paragraph.
- Every new article published → add to `internal-links-map.md`.

## External Linking Strategy

### Requirements
- **Minimum**: 2 external authority links per article.
- **Optimal**: 3–4.
- **Purpose**: Add credibility, cite sources, support claims.

### Good External Targets (Amazon FBA niche)
- **Amazon Seller Central help pages** — authoritative on fees, policies, program rules.
- **Amazon Ads documentation** — for advertising specifics.
- **Amazon Revenue Calculator** — for fee estimation.
- **Jungle Scout annual "State of the Amazon Seller" report** — for industry data.
- **EU tax authorities / OSS scheme docs** — for VAT / EU content.
- **Helium 10 Podcast / Seriously Simple Podcast transcripts** — when referencing industry insights.
- **Statista, eMarketer, Digital Commerce 360** — for broader e-commerce stats.

### Avoid
- Random blogs with no authority.
- Affiliate links in body (use Amazon / tool affiliate links only in review pages with disclosure).
- Outdated sources (>2 years old for fee/policy data).

### Attributes
- Default: no special attributes (dofollow).
- **Affiliate links** (tool reviews): use `rel="sponsored"` — the WordPress publisher handles this when the review schema has `affiliateUrl`.
- **User-generated content links**: `rel="nofollow"`.

## Readability Optimization

### Target Reading Level
- **Goal**: 8th–10th grade Flesch-Kincaid.
- FBA audience includes many non-native English speakers; plain language wins.

### Sentence Structure
- **Average length**: 15–20 words.
- **Maximum**: 25 words — break longer ones.
- **Variety**: Mix short punchy sentences (for takeaways) with longer explanatory ones (for frameworks).
- **Active voice**: 80%+. "Amazon raised storage fees" > "Storage fees were raised."

### Paragraph Structure
- 2–4 sentences per paragraph.
- One idea per paragraph.
- Short paragraphs scan well on mobile (where majority of Amazon sellers read).

### Formatting for Scannability
- Subheadings every 300–400 words.
- Bulleted/numbered lists for steps, rankings, collections.
- **Bold** on key concepts, tier labels, critical numbers.
- Plenty of white space.

### Transition Words (one per paragraph, natural)
- Addition: Additionally, Furthermore, Also.
- Contrast: However, But here's the thing, On the other hand.
- Cause/effect: Therefore, As a result, Because of this.
- Example: For instance, Take [specific example].
- Time: First, Next, Finally, After two weeks.

## Content Quality Standards (E-E-A-T)

### Experience
- First-person operator voice: Katia's actual selling experience.
- "I've tried X across multiple businesses" beats "studies show."

### Expertise
- Accurate fee structures (match current Amazon schedule).
- Accurate tool feature descriptions (revisit tool reviews quarterly).
- Specific-category nuances called out when relevant.

### Authoritativeness
- Author attribution: `author: "FBA Girl"` in frontmatter.
- Cite Amazon's own documentation when claiming how a program/fee/rule works.
- Link to the YouTube channel where the author is visibly teaching the topic: @AmazonFBAGirl for EN/DE content, @Amazon_FBA_Seller for RU content.

### Trustworthiness
- No overpromising ("make six figures in 90 days").
- Acknowledge trade-offs openly.
- Affiliate disclosure when relevant (`affiliateDisclosure: true` in review schema).
- Update outdated content — especially fee / policy articles that age fast.

### Content Originality
- Never plagiarize.
- Use Katia's actual experience (Amazon.de launch, cookware brand, multi-business perspective) for unique angles.
- Reference competitor coverage to ensure comprehensiveness; differentiate by voice + specificity.

### Factual Accuracy
- Verify fee numbers against Amazon's current published schedule.
- Verify tool pricing against current tool websites.
- Include "as of [month YYYY]" when quoting time-sensitive data.

## Image Optimization

### Cover Image
- **Photorealistic only** — DSLR-style. No cartoon / illustration / digital-art.
- Stored in `./images/` next to the MDX file.
- `coverImage` field must reference it; `coverImageAlt` required.
- Use the `generate-cover-image` skill (Gemini Nano Banana 2) — always include "no text or lettering" in the prompt.

### File Names
- Descriptive, kebab-case. `amazon-ppc-strategy-2026.jpg`, not `IMG_1234.jpg`.

### Alt Text
- Describes what the image shows.
- Keyword included naturally when relevant.
- ≤125 characters.
- No "image of" / "photo of" — implied.

### Placement
- Cover image at the top (handled by layout).
- In-body images break up long sections.
- Screenshots of Seller Central / tool dashboards where they clarify the text.

## Featured Snippet & PAA Optimization

### Question-Based Snippets
- Include the question as an H2 or H3.
- Answer concisely in 40–60 words immediately after.
- Then expand.

**Example**:
```markdown
## What is a good ACoS on Amazon?

A good ACoS depends on your product margin. Most Amazon sellers target an ACoS between 15% and 30%. A high-margin product ($30 selling price, $5 COGS) can sustain 30%+ ACoS profitably. A thin-margin product ($12 selling price, $7 COGS) needs ACoS under 15% to stay in the black.

[Expand with nuance...]
```

### List-Based Snippets
- Numbered steps or bulleted collections.
- Keep items to 1–2 sentences each.
- 5–8 items ideal.

### Table-Based Snippets
- Comparison charts (tool pricing, fee tiers, marketplace differences).
- Clean headers, organized data.

### Definition Snippets
- Define the term in the first sentence after the heading.
- 40–60 word definition; expand after.

## Mobile Optimization

- Mobile-first audience (most FBA research happens on phone in-between Seller Central sessions).
- Short paragraphs (2–3 sentences).
- Large fonts by default (handled by the Astro theme's global CSS).
- Tap-friendly links.
- Fast loading — cover image `.jpg` optimized; avoid unnecessary JavaScript.

## AI Search Optimization (GEO/AICO)

AI search engines (ChatGPT, Perplexity, Gemini, Claude) are a major and growing traffic / recommendation channel. For TheFBAGirl's niche, AI recommendations particularly matter on tool-comparison queries and "how to" searches. These guidelines ensure articles perform in both traditional search and AI-generated answers.

### Direct-Answer-First Principle

AI scrapers prioritize the earliest clear answer on the page.

**Rules**:
- Answer the query directly in the first 1–2 sentences for "best / top / how / what is" queries — before the narrative hook.
- Meta description should literally answer the target query in 150–160 chars.
- Don't bury the answer behind 200+ words of context.
- The narrative hook still applies; it comes *after* the direct answer when one is needed.

**Example — AI-optimized direct answer**:
> The best Amazon PPC strategy in 2026 uses a three-phase campaign structure: auto campaigns for discovery, manual exact match for proven keywords, and continuous bid optimization. Here's how each phase works — and the ACoS/TACoS benchmarks to hit.

### TL;DR / Key Takeaways Block

Every article should include a Key Takeaways block **near the top** (after the hook/intro, before the first H2). This gets pulled into AI summaries and helps human readers skim.

**Format**:
```markdown
> **Key Takeaways**
> - [Specific claim with a number or named framework]
> - [Specific claim]
> - [Specific claim]
> - [Specific claim — optional 4th]
> - [Specific claim — optional 5th]
```

**Rules**:
- 3–5 bullets max.
- Each bullet is a complete, standalone claim — not a teaser.
- Use specific numbers, tool names, outcomes — not vague summaries.
- This is NOT a table of contents; it's the article's conclusions up front.

### Authority Signaling for AI

Include in every article:
- **Author attribution**: `author: "FBA Girl"` in frontmatter (default) — named, not "Team."
- **Last updated date**: Use `updatedDate` in the frontmatter when revising.
- **Year in title for time-sensitive topics**: "Best Amazon PPC Strategy 2026."
- **YouTube video embed when one exists** (`youtubeVideoId` frontmatter field is already in the schema). Perplexity and Gemini cross-validate video with article.

### One Idea Per Section

AI models parse content by section. Each H2/H3 should focus on a single clear idea to maximize the chance of targeted citation.

- One concept per heading.
- Use bullet lists and structured formatting within sections.
- Avoid long flowing paragraphs that blend multiple topics.

### Embedded Media for Cross-Validation

- Embed the matching YouTube video when the article has one (`youtubeVideoId` in schema).
- Where useful, embed Amazon Seller Central screenshots or tool dashboards.

### FAQ Sections as Prompt Targets

FAQ sections target Google PAA and match how ChatGPT/Perplexity users phrase queries.

- Write 4–6 FAQ questions per article.
- Questions in natural prompt language ("how do I lower my ACoS?" not "ACoS reduction strategies").
- Answer each in the first sentence, then expand.
- Pull questions from YouTube comments, Reddit, and Google's "People also ask."

### Content Repurposing for AI Citation Surface

AI tools pull from Medium, LinkedIn Pulse, Reddit, Quora, and YouTube transcripts. Use the `/repurpose` command to adapt cornerstone articles across platforms with canonical attribution back to thefbagirl.com. See `ai-citation-targets.md` for priority surfaces.

### AI Citation Audit

Run `/research-ai-citations [topic]` quarterly on each high-priority prompt cluster. Feed findings back into `ai-citation-targets.md` and adjust content strategy accordingly.

## Content Refresh Strategy

### When to Update
- **News/fee/policy articles**: When facts change — e.g., new fee schedule, updated program rules.
- **Tool reviews**: Quarterly, or whenever the tool releases major updates / price changes.
- **Tactical content (PPC, launch, product research)**: Every 6–12 months; always within 12 months for anything dated in the title.
- **Evergreen strategy content**: Annually; refresh examples and add current-year context.

### What to Update
- Frontmatter `updatedDate`.
- Fee / price / policy specifics.
- Screenshots (tools and Seller Central UIs change).
- Example calculations.
- Internal links to newer content.
- CTA if new relevant content exists.

### Update, Don't Replace
- Most refreshes happen in place (edit the existing file) — not new URLs. The existing URL has accumulated authority.
- If the article's premise has changed (e.g., "Amazon FBA is dead" reversal), write a new article and 301 the old one — but this is rare.

## SEO Checklist for Every Article

Before publishing, verify:

### Content
- [ ] 1,500–3,000 words for standard articles (or appropriate for content type).
- [ ] Primary keyword identified and confirmed against `target-keywords.md`.
- [ ] Keyword density 1–2%.
- [ ] 3–5 secondary keywords included.
- [ ] LSI keywords naturally integrated.
- [ ] Unique angle vs. competitor coverage.
- [ ] Factually accurate (fees, tool features, policy specifics).

### Structure
- [ ] One H1 via frontmatter `title`, includes primary keyword.
- [ ] 4–7 H2 sections.
- [ ] 2–3 H2s include keyword variations.
- [ ] Proper H1 → H2 → H3 hierarchy.
- [ ] Keyword in first 100 words.
- [ ] Keyword in conclusion.

### Meta Elements (Frontmatter)
- [ ] `title` ≤70 chars, includes keyword.
- [ ] `description` ≤160 chars, includes keyword + value + CTA verb.
- [ ] `publishDate` ISO format.
- [ ] `updatedDate` if refreshing.
- [ ] `category` matches schema enum.
- [ ] `tags` array populated.
- [ ] `coverImage` + `coverImageAlt` present.
- [ ] `youtubeVideoId` + `youtubeVideoTitle` if video exists.
- [ ] `author: "FBA Girl"` (default, but verify).
- [ ] `affiliateDisclosure: true` for reviews / affiliate-linked articles.
- [ ] URL slug matches file name, includes keyword.

### Links
- [ ] 3–5 internal links (see `internal-links-map.md`).
- [ ] Internal links use descriptive anchor text (not "click here").
- [ ] 2+ external authority links.
- [ ] All links functional.
- [ ] New article added to `internal-links-map.md` after publish.

### Readability
- [ ] 8th–10th grade reading level.
- [ ] Sentences 15–20 words average; max 25.
- [ ] Paragraphs 2–4 sentences.
- [ ] Subheadings every 300–400 words.
- [ ] Lists used for scannability.
- [ ] Active voice predominantly.

### Media
- [ ] Cover image photorealistic (DSLR-style).
- [ ] Alt text descriptive with keyword when natural.
- [ ] Images optimized (.jpg).
- [ ] YouTube video embedded / referenced when available.

### AI Search Optimization
- [ ] Direct answer in first 1–2 sentences (for "best/how/top" queries).
- [ ] TL;DR / Key Takeaways block after intro, before first H2.
- [ ] Meta description answers the target query directly.
- [ ] FAQ section with 4–6 prompt-language questions.
- [ ] At least one embedded YouTube video when available.
- [ ] Year included in title for time-sensitive topics.
- [ ] Named author (`FBA Girl`).
- [ ] Last updated date when applicable.

### Quality
- [ ] No AI-smell words (see `brand-voice.md` list).
- [ ] No guru language.
- [ ] Sources cited with links.
- [ ] Brand voice maintained (see `brand-voice.md` examples).
- [ ] Actionable "this week" takeaway.
- [ ] Clear CTA (YouTube / newsletter / related article).

## SEO Tools & Resources

### Tools Used in TheFBAGirl Pipeline
- **DataForSEO** (via `.env` credentials) — keyword research, SERP analysis, rankings.
- **Google Search Console** (via `.env` credentials) — impressions, rankings, CTR.
- **Google Analytics 4** (via `.env` credentials) — traffic, engagement.
- **YouTube Data API v3** (via `.env` `YOUTUBE_API_KEY`) — channel/video data for content pipeline.

### Reference Resources
- Google's Search Quality Evaluator Guidelines (for E-E-A-T framing).
- Amazon Seller Central help pages (for authoritative fee/policy references).
- Ahrefs blog, Backlinko, Search Engine Journal (for general SEO best practices).
- "State of the Amazon Seller" report (Jungle Scout, annual) — for industry benchmarks.

---

**Remember**: SEO serves the Amazon seller trying to learn, launch, or scale — not the algorithm. A 2,500-word article that honestly answers the seller's question and points them to the right tool/tactic will outperform a 4,500-word SEO-stuffed article every time in the long run. Write the article Katia would want to send a friend who just asked the question.
