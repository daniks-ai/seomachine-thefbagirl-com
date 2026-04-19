# Daily Auto-Publish Pipeline

Fully automated pipeline: pick a topic (or start from a YouTube video), research, write, review, generate image, publish to the [thefbagirl.com](https://thefbagirl.com) Astro repo, commit & push. CI/CD deploys automatically.

## Usage

Four modes, selected by what you pass in `$ARGUMENTS`:

**Mode A — Autonomous topic selection (default, for daily cron)**
```
/daily-publish
```
Pipeline picks the next best topic from the YouTube video pipeline and keyword clusters.

**Mode B — Seed from a YouTube video (auto-scrape transcript)**
```
/daily-publish https://www.youtube.com/watch?v=NCQcvIrg8Yw
/daily-publish https://youtu.be/NCQcvIrg8Yw
/daily-publish https://www.youtube.com/shorts/abc123xyz
/daily-publish NCQcvIrg8Yw
```
Pipeline fetches video metadata via YouTube Data API and scrapes the transcript via `youtube-transcript-api`.

**Mode C — YouTube video + user-provided transcript (highest quality)**
```
/daily-publish https://youtu.be/NCQcvIrg8Yw /path/to/transcript.txt
/daily-publish NCQcvIrg8Yw ~/Downloads/vine-transcript.md
```
Pipeline fetches metadata from the URL (title, description, channel ID, publish date) but uses **the provided transcript** instead of scraping. Use this when you have a professionally transcribed, manually-cleaned, or longer-form transcript than what YouTube auto-captions produce. The provided transcript is authoritative.

**Mode D — Transcript only (no YouTube URL)**
```
/daily-publish /path/to/transcript.txt
/daily-publish ~/Downloads/new-video-transcript.md
```
Pipeline derives title, primary keyword, and topic entirely from the transcript content. Useful when the video is unpublished, a draft, a private upload, or you simply do not need YouTube metadata. The article publishes without a `youtubeVideoId` — no video embed.

---

### Argument parsing

`$ARGUMENTS` is whitespace-separated. For each token, classify:
1. **YouTube URL** (`youtube.com/watch?v=`, `youtu.be/`, `youtube.com/shorts/`, `youtube.com/embed/`) → extract the 11-char video ID.
2. **Bare video ID** matching `^[A-Za-z0-9_-]{11}$` AND not an existing file path → video ID.
3. **Existing readable file path** → transcript path. Accept `.txt`, `.md`, `.json`, `.srt`, `.vtt`. Resolve `~` and relative paths.

Mode selection:
| video_id | transcript_path | Mode |
|---|---|---|
| none | none | A |
| set | none | B |
| set | set | C |
| none | set | D |

If classification is ambiguous (two tokens both look like file paths, or a bare-ID collides with an existing 11-char filename), prefer the file-path interpretation for the token that resolves to a real file, and report the decision in the final status.

---

**In all modes**: this command is designed to run unattended via `claude -p`. **Do NOT ask the user any questions. Make all decisions autonomously.** If a step fails critically, save progress and stop — leave a clear status message.

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

### Step 1: Pick a topic (Mode A) OR parse the input (Modes B / C / D)

Classify `$ARGUMENTS` per the parsing rules at the top of this file. Branch to the matching mode below.

#### Mode A — Autonomous topic selection (no arguments)

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

#### Mode B — Seed from a specific YouTube video

The argument is a YouTube URL or a bare 11-character video ID. Extract the video ID using these patterns (in order):

| Input format | Example | Extract |
|---|---|---|
| Full watch URL | `https://www.youtube.com/watch?v=NCQcvIrg8Yw` | `NCQcvIrg8Yw` |
| Short URL | `https://youtu.be/NCQcvIrg8Yw` | `NCQcvIrg8Yw` |
| Shorts URL | `https://www.youtube.com/shorts/NCQcvIrg8Yw` | `NCQcvIrg8Yw` |
| Embed URL | `https://www.youtube.com/embed/NCQcvIrg8Yw` | `NCQcvIrg8Yw` |
| Bare ID | `NCQcvIrg8Yw` | `NCQcvIrg8Yw` |

Validate: the ID must match `^[A-Za-z0-9_-]{11}$`. Strip any trailing query params (`&t=30s`, `&list=...`, etc.).

**Fetch video metadata** via YouTube Data API (key in `data_sources/config/.env` as `YOUTUBE_API_KEY`):

```bash
VIDEO_ID="[extracted-id]"
YT_KEY=$(grep YOUTUBE_API_KEY data_sources/config/.env | cut -d= -f2)
curl -s "https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails,statistics&id=$VIDEO_ID&key=$YT_KEY" \
  | python3 -m json.tool > research/video-$VIDEO_ID.json
```

From the response, extract:
- `snippet.title` — video title (primary seed for article title and keyword)
- `snippet.description` — video description (secondary content seed; may contain links and chapter markers)
- `snippet.channelId` — must equal `UCPx3JO2j6hycfM_zGSqbYPA` (Katia's channel). If it does not match, **stop** and report: the command only seeds articles from Katia's own channel to maintain voice authenticity.
- `snippet.publishedAt` — video publish date
- `snippet.tags` — any tags attached to the video (optional keyword signals)
- `contentDetails.duration` — video length (useful for framing "watch the 8-minute walkthrough")

**Fetch the video transcript** via `youtube-transcript-api` — this is the highest-signal input for voice match. Use Katia's actual spoken words as the primary reference for the article body:

```bash
python3 -c "
from youtube_transcript_api import YouTubeTranscriptApi
import json, sys
video_id = '$VIDEO_ID'
try:
    transcript = YouTubeTranscriptApi().fetch(video_id)
    segments = transcript.to_raw_data()
    full_text = ' '.join(s['text'] for s in segments)
    out = {
        'video_id': video_id,
        'segments': len(segments),
        'word_count': len(full_text.split()),
        'full_text': full_text,
        'timed_segments': segments,
    }
    with open(f'research/transcript-{video_id}.json', 'w') as f:
        json.dump(out, f, indent=2)
    print(f'Transcript saved: {out[\"word_count\"]} words, {out[\"segments\"]} segments')
except Exception as e:
    print(f'TRANSCRIPT_FETCH_FAILED: {e}', file=sys.stderr)
    sys.exit(1)
"
```

**If transcript fetch fails** (no captions, auto-captions disabled, video is very new and YouTube has not transcribed it yet): continue with title + description only — do NOT stop. Note the failure in the final summary and flag that the article's voice match may be weaker without transcript grounding.

**If transcript succeeds**: save it to `research/transcript-$VIDEO_ID.json`. The write step (Step 3) must use this as the primary source for:
- Voice calibration (Katia's actual word choices, sentence rhythms, filler phrases like "frankly," "here is the uncomfortable truth")
- Specific examples and numbers mentioned in the video
- The order in which Katia presents the topic (follow her structure where it makes sense)
- Personal anecdotes she shared (use as mini-stories with minor polish, never fabricate new ones beyond what's in the transcript)

The transcript is raw speech — expect filler words, repetitions, and grammar looseness. The article is a polished written version: keep the substance, tighten the prose. Never paste transcript text verbatim; always rewrite for written register.

#### Mode C — YouTube video + user-provided transcript

Same as Mode B for metadata (fetch title, description, channel ID, etc. from YouTube Data API and run the duplicate check).

**Skip the `youtube-transcript-api` scrape.** Load the user-provided transcript instead using the normalizer below. The provided transcript is authoritative — it overrides anything YouTube's auto-captions would have returned.

Save the normalized transcript to `research/transcript-$VIDEO_ID.json` using the same schema as Mode B so downstream steps do not need to branch:
```json
{
  "video_id": "...",
  "source": "user-provided",
  "original_path": "/path/to/...",
  "word_count": 1697,
  "full_text": "..."
}
```

Note in the final status that the user-provided transcript was used. This also means the article reliability bar is higher — user-provided transcripts are usually cleaner than auto-captions, so voice match should be tighter.

#### Mode D — Transcript only (no YouTube URL)

Skip all YouTube API calls. Load the user-provided transcript using the normalizer below.

**Derive the topic and primary keyword from the transcript content**:
1. Read the full transcript. Identify the core subject (usually established in the first 10–30% of the text).
2. Pick a 2–4 word noun phrase as the primary keyword. Cross-check against `context/target-keywords.md` clusters — prefer an existing cluster match.
3. Pick the target collection (`blog` / `tutorials` / `news` / `reviews` / `lifehacks`) based on how the transcript is structured:
   - Step-by-step walkthrough → `tutorials`
   - Opinion / strategic analysis → `blog`
   - Tool discussion → `reviews`
   - News / policy / fee announcement → `news`
   - Workflow / productivity / mindset → `lifehacks`
4. Generate a file slug (kebab-case, 3–6 words, includes keyword, includes year if time-sensitive).

**Important**: in Mode D the frontmatter has NO `youtubeVideoId` or `youtubeVideoTitle` (leave them out entirely — they are optional in the schema). The article body must NOT reference a video ("watch the full walkthrough" language is forbidden). Internal links and YouTube-channel CTAs still apply.

Save `topics/from-transcript-[YYYY-MM-DD].md` with:
- Derived title
- Primary keyword
- Target collection + category
- Mapped cluster
- Suggested slug
- Transcript source path and word count
- 2–3 sentence reasoning

Then save the normalized transcript to `research/transcript-[slug].json` using:
```json
{
  "video_id": null,
  "source": "user-provided",
  "original_path": "/path/to/...",
  "word_count": 1697,
  "full_text": "..."
}
```

#### Transcript normalizer (for Modes C and D)

The user may provide the transcript in any of these formats. Normalize to plain-text `full_text`:

| Format | Handling |
|---|---|
| `.txt` | Read as-is. Collapse all whitespace runs to single spaces; strip BOM. |
| `.md` | Parse markdown. Strip frontmatter (if any YAML block at top), strip headings, collapse lists into sentences. Keep the body text only. |
| `.json` | Expect either (a) youtube-transcript-api shape `[{"text": "...", "start": ..., "duration": ...}, ...]`, (b) a whisper/assemblyAI shape `{"segments": [{"text": "..."}]}`, or (c) an object with a top-level `full_text` or `transcript` field. Extract text in that order of precedence. |
| `.srt` / `.vtt` | Strip cue indices, timestamps (`HH:MM:SS,mmm` / `HH:MM:SS.mmm`), and WEBVTT headers. Join caption text in order. Collapse whitespace. |

Normalizer snippet (inline, runnable):
```bash
python3 -c "
import sys, re, json, pathlib
path = pathlib.Path('$TRANSCRIPT_PATH').expanduser()
raw = path.read_text(encoding='utf-8-sig')
ext = path.suffix.lower()
if ext == '.json':
    data = json.loads(raw)
    if isinstance(data, list):
        text = ' '.join(seg.get('text','') for seg in data)
    elif isinstance(data, dict):
        if 'full_text' in data: text = data['full_text']
        elif 'transcript' in data: text = data['transcript']
        elif 'segments' in data: text = ' '.join(s.get('text','') for s in data['segments'])
        else: text = json.dumps(data)
    else:
        text = str(data)
elif ext in ('.srt', '.vtt'):
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped: continue
        if stripped.upper().startswith('WEBVTT'): continue
        if re.match(r'^\d+$', stripped): continue
        if re.match(r'^\d{2}:\d{2}:\d{2}[.,]\d{3}', stripped): continue
        if '-->' in stripped: continue
        lines.append(stripped)
    text = ' '.join(lines)
elif ext == '.md':
    # Strip frontmatter
    body = re.sub(r'^---\n.*?\n---\n', '', raw, count=1, flags=re.DOTALL)
    # Strip headings, list markers, code fences
    body = re.sub(r'^#+\s*', '', body, flags=re.MULTILINE)
    body = re.sub(r'^[-*]\s+', '', body, flags=re.MULTILINE)
    body = re.sub(r'\`\`\`.*?\`\`\`', '', body, flags=re.DOTALL)
    text = body
else:
    text = raw
# Normalize whitespace
text = re.sub(r'\s+', ' ', text).strip()
out = {
    'video_id': '$VIDEO_ID' or None,
    'source': 'user-provided',
    'original_path': str(path),
    'word_count': len(text.split()),
    'full_text': text,
}
out_path = 'research/transcript-' + ('$VIDEO_ID' or '$SLUG') + '.json'
pathlib.Path(out_path).write_text(json.dumps(out, indent=2))
print(f'Normalized {out[\"word_count\"]} words to {out_path}')
"
```

**Check for duplicates**: search `context/target-keywords.md` `YouTube Video → Article Pipeline` table AND the published articles under `/Users/ync/poryadok/sources/thefbagirl-com/src/content/*/` for existing frontmatter with `youtubeVideoId: "$VIDEO_ID"`. If found, the article already exists — stop and report the URL of the existing article. Do not silently overwrite.

**Derive the primary keyword** from the video title:
- Strip emoji, decorative punctuation, and promotional prefixes (e.g., "🔥 ", "Amazon FBA for Beginners: ", "NEW: ").
- Identify the 2–4 word noun phrase that is the core search target.
- Example: `"🍇 Amazon Vine Program Explained: How to Enroll, What It Costs & Get 30 Reviews (FBA Seller Guide)"` → primary keyword: `Amazon Vine program`.
- Cross-check the derived keyword against `context/target-keywords.md` clusters. If it maps to a known cluster, use that cluster's existing pillar/supporting structure. If it is new, note that this article will seed a new cluster.

**Pick the target collection** based on video content type:
- Tutorial / walkthrough → `tutorials` (set `difficulty` and `estimatedTime` in frontmatter)
- Tool review → `reviews` (set `toolName`, `toolUrl`, `rating`, `pros`, `cons`, `verdict`)
- Amazon policy / fee / news → `news`
- Productivity / workflow / mindset → `lifehacks`
- Strategy, analysis, opinion, everything else → `blog`

**Output**: Save `topics/from-video-$VIDEO_ID-[YYYY-MM-DD].md` with:
- Full video title (from YouTube API)
- Video ID and URL
- Primary keyword (derived)
- Target collection
- Target category enum value
- Mapped cluster from `target-keywords.md` (or "new cluster")
- Suggested file slug
- 2–3 sentence reasoning for the framing chosen

The rest of the pipeline (Steps 2–14) runs identically in both modes. The key difference: in Mode B, every draft and every agent report must frontmatter-set `youtubeVideoId: "$VIDEO_ID"` and `youtubeVideoTitle: "[raw title]"`, and the article body must reference the video ("Watch the full walkthrough in the video above") in the natural place(s) the voice guide specifies.

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

**In Modes B, C, and D (any mode with a transcript)**: the transcript at `research/transcript-*.json` is the **primary** source of truth for both content and voice. Read it in full before writing. Specifically:
- Use Katia's exact examples, numbers, and ASIN details from the transcript. Never substitute invented numbers when she gave real ones on camera.
- Preserve her narrative order where it makes sense for a written article.
- Quote characteristic phrasings (e.g., "here is the uncomfortable truth," "frankly," "I have seen sellers...") to lock voice match.
- Expand on points she mentioned briefly if SERP research shows they deserve depth.
- Skip filler, tangents, and throat-clearing from the transcript.
- Never paste raw transcript sentences — rewrite for written register (tighter, no filler).
- The article should read as the written sibling of the video (or of the raw thought, in Mode D), not a transcription. A reader who watched the video and then reads the article should find reinforcement + extra depth, not repetition.

**Quality hierarchy between modes**:
- **Mode C (user-provided transcript)** is the highest-fidelity mode. Treat the provided transcript as ground truth — if it contradicts SERP research or your training intuitions, the transcript wins.
- **Mode B (scraped transcript)** has auto-caption artifacts (run-together numbers like "1,0 or 1,11" that actually meant "1,010 or 1,011", missing punctuation, misheard jargon). Use judgment to reconstruct obvious transcription errors while preserving the substance.
- **Mode D (transcript only)** — no video to reference. Do not write phrases like "in the video above" or "watch the full walkthrough." The transcript is the source, but the article stands alone.
- **Mode A (no transcript)**: rely on `context/writing-examples.md` and general brand voice.

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
