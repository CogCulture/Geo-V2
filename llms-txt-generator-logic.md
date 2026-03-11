# llms.txt Generator — Full Logic & Implementation Guide

> A complete technical reference for building a production-grade llms.txt generator that crawls all available pages of a website and produces a spec-compliant, LLM-optimized file. Intended for integration into a GEO (Generative Engine Optimization) product.

---

## Table of Contents

1. [What is llms.txt?](#1-what-is-llmstxt)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Phase 1 — URL Discovery & Sitemap Crawling](#3-phase-1--url-discovery--sitemap-crawling)
4. [Phase 2 — Page Content Extraction](#4-phase-2--page-content-extraction)
5. [Phase 3 — Page-Level Analysis with Claude](#5-phase-3--page-level-analysis-with-claude)
6. [Phase 4 — Site-Wide Synthesis & llms.txt Generation](#6-phase-4--site-wide-synthesis--llmstxt-generation)
7. [The System Prompt (Full)](#7-the-system-prompt-full)
8. [llms.txt File Format Spec](#8-llmstxt-file-format-spec)
9. [Categorization & Sectioning Logic](#9-categorization--sectioning-logic)
10. [Scoring & Prioritization Logic](#10-scoring--prioritization-logic)
11. [Handling Edge Cases](#11-handling-edge-cases)
12. [API Integration Reference](#12-api-integration-reference)
13. [Rate Limiting & Cost Management](#13-rate-limiting--cost-management)
14. [Full Implementation Pseudocode](#14-full-implementation-pseudocode)
15. [Output Quality Checklist](#15-output-quality-checklist)

---

## 1. What is llms.txt?

The `llms.txt` standard (defined at [llmstxt.org](https://llmstxt.org)) is a plain Markdown file placed at `https://yourdomain.com/llms.txt`. It tells LLMs (like Claude, GPT, Gemini) what a website is about, how it's structured, and which pages are most important — enabling LLMs to reason about and cite the site accurately.

### Why it matters for GEO

- **Generative Engine Optimization** depends on LLMs understanding your site's authority and structure
- Without `llms.txt`, LLMs must guess — often incorrectly — what your site covers
- A well-formed `llms.txt` increases the probability that an LLM cites your site accurately and frequently
- It is the SEO `robots.txt` equivalent for the AI era

### File placement

```
https://example.com/llms.txt        ← primary
https://example.com/llms-full.txt   ← optional extended version with all pages
```

---

## 2. High-Level Architecture

The generator works in four sequential phases:

```
INPUT: Website URL
        │
        ▼
┌─────────────────────────┐
│  Phase 1: URL Discovery │  ← sitemap.xml, robots.txt, recursive crawl
│  Output: list of URLs   │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────────┐
│  Phase 2: Content Extraction│  ← fetch each URL, strip HTML, extract text
│  Output: page data objects  │
└────────────┬────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  Phase 3: Per-Page Claude Analysis│  ← classify, summarize, score each page
│  Output: structured page metadata│
└────────────┬─────────────────────┘
             │
             ▼
┌───────────────────────────────────────┐
│  Phase 4: Site-Wide Synthesis (Claude)│  ← generate final llms.txt
│  Output: llms.txt file content        │
└───────────────────────────────────────┘
        │
        ▼
OUTPUT: /llms.txt content (Markdown)
```

---

## 3. Phase 1 — URL Discovery & Sitemap Crawling

### Step 1.1 — Check robots.txt

Fetch `https://domain.com/robots.txt` first. This file:
- Lists `Disallow` paths (skip these pages — don't include in llms.txt)
- Often contains `Sitemap:` directives pointing to sitemap files

```
GET https://example.com/robots.txt
Parse lines:
  - "Sitemap: <url>" → add to sitemap queue
  - "Disallow: /path" → add to exclusion list
```

### Step 1.2 — Fetch Sitemap(s)

Try these URLs in order:
1. Any sitemaps found in robots.txt
2. `https://domain.com/sitemap.xml`
3. `https://domain.com/sitemap_index.xml`
4. `https://domain.com/sitemap/`

**Sitemap index files** (sitemap of sitemaps) list child sitemaps — recursively fetch each one.

Parse `<loc>` tags from sitemap XML to extract all page URLs.

```xml
<!-- sitemap.xml structure -->
<urlset>
  <url>
    <loc>https://example.com/about</loc>
    <priority>0.8</priority>           ← use this as initial importance signal
    <changefreq>monthly</changefreq>
    <lastmod>2024-11-01</lastmod>      ← use for freshness scoring
  </url>
</urlset>
```

Store: `{ url, priority, lastmod }` per entry.

### Step 1.3 — Fallback: Recursive Link Crawl

If no sitemap exists, crawl the site by:
1. Starting at the root URL
2. Fetching each page
3. Extracting all `<a href="...">` tags where `href` is on the same domain
4. Adding new URLs to a queue
5. Repeat up to a configurable max depth (recommend: 3 levels) and max pages (recommend: 500)

**De-duplication rules:**
- Normalize URLs: strip trailing slashes, lowercase, remove `#fragments` and common tracking params (`?utm_*`, `?ref=`, etc.)
- Track visited URLs in a `Set` to avoid loops

### Step 1.4 — URL Filtering

Before processing, filter out URLs that should NOT appear in llms.txt:

| Filter | Reason |
|--------|--------|
| Matches `robots.txt Disallow` | Respect crawl rules |
| Login/auth pages (`/login`, `/signin`, `/dashboard`) | Not useful to LLMs |
| Admin pages (`/admin`, `/wp-admin`) | Private |
| API endpoints (`/api/`, `.json`, `.xml`) | Not human-readable pages |
| Media files (`.jpg`, `.png`, `.pdf`, `.zip`) | Not pages |
| Pagination (`?page=2`, `/page/3/`) | Redundant |
| Duplicate content (canonical check) | Avoid duplicates |
| Tag/category archives without unique content | Low value |

### Step 1.5 — Output of Phase 1

```json
[
  {
    "url": "https://example.com/docs/getting-started",
    "priority": 0.9,
    "lastmod": "2024-10-15",
    "depth": 1,
    "source": "sitemap"
  },
  ...
]
```

---

## 4. Phase 2 — Page Content Extraction

For each URL discovered in Phase 1, fetch and extract structured content.

### Step 2.1 — HTTP Fetch

```
GET <url>
Headers:
  User-Agent: "LLMs-txt-generator/1.0 (GEO tool; contact@yourdomain.com)"
  Accept: text/html
Timeout: 10 seconds
Follow redirects: yes (max 3)
```

Track final URL after redirects — update the URL if a redirect occurred.

### Step 2.2 — HTML Parsing & Content Extraction

Parse the HTML response. Extract the following signals:

**Metadata (from `<head>`):**
- `<title>` tag → page title
- `<meta name="description">` → short description
- `<meta property="og:title">` → social title (often cleaner)
- `<meta property="og:description">` → social description
- `<link rel="canonical">` → canonical URL (skip page if canonical ≠ current URL)
- `<meta name="robots">` with `noindex` → skip this page

**Structural signals (from `<body>`):**
- `<h1>` text → primary topic of page
- `<h2>` texts → subtopics / section names
- `<nav>` links → site navigation structure (helps with categorization)
- `<main>` or `<article>` content → main body text
- `<footer>` links → often reveals site sections

**Breadcrumbs** (if present via `<nav aria-label="breadcrumb">` or schema.org `BreadcrumbList`):
- Reveals page hierarchy, e.g. `Docs > API Reference > Authentication`

**Content extraction:**
Strip all HTML tags and retain only readable text from the main content area (`<main>`, `<article>`, `#content`, `.post-content`, or fallback to `<body>`). Remove: scripts, styles, nav bars, headers, footers, cookie banners, ads.

Limit extracted text to **~2000 characters** — enough for Claude to understand the page without hitting token limits.

### Step 2.3 — Page Type Detection (Heuristic)

Before sending to Claude, apply fast heuristics to classify the page type:

| Heuristic | Detected Type |
|-----------|--------------|
| URL path contains `/docs/`, `/documentation/`, `/guide/` | `documentation` |
| URL path contains `/blog/`, `/posts/`, `/articles/` | `blog` |
| URL path contains `/api/`, `/reference/` | `api-reference` |
| URL path contains `/pricing/`, `/plans/` | `pricing` |
| URL path is `/` or `/home` | `homepage` |
| URL path contains `/about/`, `/team/`, `/company/` | `about` |
| URL path contains `/changelog/`, `/releases/` | `changelog` |
| URL path contains `/tutorials/`, `/learn/` | `tutorial` |
| `<article>` tag present + date metadata | `blog` |
| `<table>` with many rows + code blocks | `api-reference` |

This heuristic type is passed to Claude as a hint (not a hard classification).

### Step 2.4 — Output of Phase 2

```json
{
  "url": "https://example.com/docs/authentication",
  "finalUrl": "https://example.com/docs/authentication",
  "title": "Authentication — Example Docs",
  "ogTitle": "Authentication",
  "description": "Learn how to authenticate API requests using API keys or OAuth2.",
  "h1": "Authentication",
  "h2s": ["API Keys", "OAuth2", "JWT Tokens"],
  "bodyText": "Authentication is required for all API requests. You can use...",
  "heuristicType": "documentation",
  "lastmod": "2024-10-15",
  "priority": 0.9,
  "depth": 2,
  "canonicalMatch": true
}
```

---

## 5. Phase 3 — Per-Page Analysis with Claude

Send batches of pages to Claude for structured analysis. This phase extracts clean, LLM-optimized metadata for every page.

### Step 3.1 — Batching Strategy

Do NOT send one page per API call — that's extremely expensive. Instead, batch pages:
- **Batch size:** 10–20 pages per API call (depending on average page text length)
- **Token budget per batch:** Keep input under 80,000 tokens total
- For very large sites (500+ pages), process in parallel with a concurrency limit of 5

### Step 3.2 — Per-Page Analysis Prompt

```
System:
You are a technical content analyst specializing in LLM indexing.
For each page provided, output ONLY a JSON array. No explanation.
Each element must have exactly these fields:
{
  "url": "exact URL",
  "title": "clean, concise title (max 60 chars)",
  "description": "1-sentence description optimized for LLM understanding (max 120 chars)",
  "section": one of: ["Documentation", "API Reference", "Blog", "Tutorials", 
                       "Pricing", "About", "Changelog", "Homepage", "Legal", "Other"],
  "importance": integer 1-10 (10 = most important for LLMs to know about),
  "include": boolean (false if page adds no value for LLMs: privacy policy, 404s, tag archives, etc.)
}

User:
Analyze these pages and return the JSON array:

<pages>
[
  {
    "url": "https://example.com/docs/authentication",
    "title": "Authentication — Example Docs",
    "description": "Learn how to authenticate API requests...",
    "h1": "Authentication",
    "h2s": ["API Keys", "OAuth2"],
    "bodyText": "Authentication is required for all API requests...",
    "heuristicType": "documentation"
  },
  ... (up to 20 pages)
]
</pages>
```

### Step 3.3 — Importance Scoring Criteria (instruct Claude to use these)

| Signal | Importance Boost |
|--------|-----------------|
| Homepage | +3 |
| Has `priority >= 0.8` in sitemap | +2 |
| Is in main navigation | +2 |
| Depth 1 (direct child of root) | +1 |
| Core product/feature page | +2 |
| Has unique, dense content (API reference, full guide) | +2 |
| Recently modified (`lastmod` within 90 days) | +1 |
| Thin content (<300 words) | -2 |
| Blog post older than 2 years | -1 |
| Is a tag/category/archive page | -3 |
| Is legal/privacy/terms page | -2 |

### Step 3.4 — Output of Phase 3

```json
[
  {
    "url": "https://example.com/docs/authentication",
    "title": "Authentication",
    "description": "How to authenticate API requests using API keys or OAuth2.",
    "section": "API Reference",
    "importance": 9,
    "include": true
  },
  {
    "url": "https://example.com/privacy-policy",
    "title": "Privacy Policy",
    "description": "Legal privacy policy.",
    "section": "Legal",
    "importance": 2,
    "include": false
  }
]
```

---

## 6. Phase 4 — Site-Wide Synthesis & llms.txt Generation

With all page metadata collected, send a single final request to Claude to generate the complete `llms.txt`.

### Step 4.1 — Pre-processing Before Final Prompt

Before sending to Claude:

1. **Filter:** Keep only pages where `include: true`
2. **Sort within each section:** By `importance` descending
3. **Cap per section:** Max 30 links per section (configurable) to avoid bloat
4. **Identify top-level sections:** Group pages by their `section` field
5. **Compute site summary signals:**
   - Total pages found
   - Unique sections present
   - Most important pages (top 5 by importance score)
   - Site's apparent primary purpose (inferred from homepage + top pages)

### Step 4.2 — Final Synthesis Prompt

```
System: (see Section 7 — Full System Prompt)

User:
Generate a complete llms.txt file for this website.

Domain: example.com
Total pages analyzed: 247
Pages to include: 183

Site overview signals:
- Homepage title: "Example — The Developer Platform"
- Homepage description: "Build, ship, and scale APIs with Example's developer platform."
- Primary sections detected: Documentation, API Reference, Blog, Pricing, About, Changelog

Top 5 most important pages:
1. https://example.com/ — Homepage (importance: 10)
2. https://example.com/docs/quickstart — Quickstart Guide (importance: 9)
3. https://example.com/api/reference — API Reference (importance: 9)
4. https://example.com/pricing — Pricing (importance: 8)
5. https://example.com/docs/authentication — Authentication (importance: 8)

All pages (grouped by section, sorted by importance):

## Documentation
- [Quickstart Guide](https://example.com/docs/quickstart): Get started in 5 minutes. [importance:9]
- [Authentication](https://example.com/docs/authentication): Authenticate using API keys or OAuth2. [importance:8]
... (all documentation pages)

## API Reference
- [REST API Overview](https://example.com/api/reference): Full REST API reference. [importance:9]
...

## Blog
- [Announcing v2.0](https://example.com/blog/v2-announcement): Major platform update announcement. [importance:6]
...

(all other sections)

Now generate the best possible llms.txt. Follow the llmstxt.org spec exactly.
```

### Step 4.3 — Post-Processing

After Claude returns the llms.txt content:

1. **Validate structure:** Ensure the file starts with `# ` (H1), has a `>` blockquote, and contains at least one `##` section
2. **Check all URLs:** Verify every URL in the output was in the original page list (Claude shouldn't hallucinate URLs)
3. **Trim excess:** If file exceeds ~10,000 characters, trim lower-importance entries from each section
4. **Sanitize:** Remove any trailing whitespace, normalize line endings to `\n`

---

## 7. The System Prompt (Full)

Use this system prompt for the final llms.txt generation call (Phase 4):

```
You are an expert technical writer specializing in the llms.txt standard for Generative Engine Optimization (GEO).

Your task is to generate the best possible llms.txt file for a website, given a complete analysis of all its pages.

## The llms.txt Standard

A valid llms.txt file has this exact structure:

# [Site or Project Name]

> [One-sentence blockquote: what this site is, who it's for, and what it does. Be precise and dense with information.]

[Optional: 1-3 short paragraphs of additional context. Use these to explain the site's purpose, primary audience, key capabilities, or important concepts an LLM should know. Do NOT use bullet points here — prose only.]

## [Section Name]

- [Page Title](URL): Brief description of what this page contains and why it's useful.
- [Page Title](URL): Brief description.

## [Another Section]

- [Page Title](URL): Description.

[Repeat for all sections]

## Rules for generating excellent llms.txt

TITLES:
- Use the clean page title, not the full browser tab title (strip " — Site Name" suffixes)
- Keep titles under 60 characters

DESCRIPTIONS:
- Each link description must be specific and useful, not generic
- BAD: "Learn more about our features"
- GOOD: "Full REST API reference with request/response examples for all endpoints"
- GOOD: "How to authenticate using API keys, OAuth2, or JWT tokens"
- Aim for 10-20 words per description

BLOCKQUOTE:
- This is the most important line — LLMs use it to decide if this site is relevant to cite
- Include: what the product/site is, primary use case, target audience, key differentiator
- Example: "A developer platform for building, deploying, and scaling REST APIs, with built-in auth, rate limiting, and analytics."

SECTIONS:
- Only include sections that have meaningful content
- Use standard section names where they fit: Documentation, API Reference, Tutorials, Blog, Pricing, About, Changelog
- Order sections by importance to LLMs: core docs/API first, then blog/marketing last
- Within each section, order links by importance (most essential first)

WHAT TO EXCLUDE:
- Legal pages (Privacy Policy, Terms of Service, Cookie Policy) — these add no value
- Login/signup/account pages
- Tag archives, pagination pages, search results pages
- Any page with thin or duplicate content

OUTPUT:
- Output ONLY the raw llms.txt content
- Start with "# " (the H1)
- End with the last link line
- No code fences, no explanation, no preamble
```

---

## 8. llms.txt File Format Spec

### Required elements

```markdown
# Site Name
```
- Exactly one H1 at the top
- Use the brand/product name, not a description

```markdown
> Short description of what this site is and does.
```
- Exactly one blockquote immediately after the H1
- This is the primary signal LLMs use for relevance matching

### Optional elements (recommended)

```markdown
Additional prose context paragraphs here.
These can explain background, audience, key concepts.
```
- Plain paragraphs between the blockquote and first section
- No headers, no bullets — prose only

### Section structure

```markdown
## Section Name

- [Page Title](https://example.com/page): Description of what this page is and why it matters.
- [Page Title](https://example.com/page2): Another description.
```

- `##` (H2) for section headers
- Each page as a Markdown link followed by `: description`
- Blank line between sections

### Complete example

```markdown
# Stripe

> Stripe is a payment processing platform for developers and businesses, providing APIs for accepting payments, managing subscriptions, handling payouts, and detecting fraud.

Stripe powers online and in-person commerce for millions of companies worldwide. Its API-first design makes it the standard choice for developers building payment flows, marketplaces, and SaaS subscription billing.

## Documentation

- [Quickstart](https://stripe.com/docs/quickstart): Accept your first payment in 10 minutes with a step-by-step integration guide.
- [API Keys](https://stripe.com/docs/keys): How to create, rotate, and secure API keys for test and production environments.

## API Reference

- [Charges API](https://stripe.com/docs/api/charges): Create and retrieve charges; full request and response schema reference.
- [Customers API](https://stripe.com/docs/api/customers): Create and manage customer objects for recurring billing.

## Pricing

- [Pricing](https://stripe.com/pricing): Per-transaction pricing for all Stripe products with volume discount details.
```

---

## 9. Categorization & Sectioning Logic

### Standard section taxonomy

When grouping pages into sections, use this priority-ordered taxonomy:

| Section Name | What goes here | Priority Order |
|-------------|----------------|----------------|
| `Documentation` | Guides, how-tos, conceptual docs, walkthroughs | 1st |
| `API Reference` | Endpoint references, SDK docs, schema definitions | 2nd |
| `Tutorials` | Step-by-step tutorials, code examples, recipes | 3rd |
| `Changelog` | Release notes, version history, what's new | 4th |
| `Blog` | Articles, announcements, case studies | 5th |
| `Pricing` | Pricing, plans, enterprise tiers | 6th |
| `About` | Company, team, mission, careers | 7th |
| `Legal` | Privacy, ToS, GDPR — **exclude from output** | (excluded) |

### Custom section logic

For certain site types, create specialized sections:

- **SaaS product sites:** Add `Integrations` section for /integrations pages
- **Developer tools:** Add `SDKs & Libraries` for SDK pages
- **E-commerce:** Add `Products` for top-level product category pages
- **News/media:** Add `Topics` for major topic indexes

### Merging thin sections

If a section has fewer than 3 pages, consider:
- Merging it into a related section (e.g., 2 changelog entries can go into `Documentation`)
- Omitting it entirely if the content is low-value
- Never create a section with only 1 entry — fold it elsewhere

---

## 10. Scoring & Prioritization Logic

Every page gets a numeric importance score (1–10). Here is the complete scoring formula:

### Base score

Start at **5** for all pages.

### Additive signals (+)

| Signal | Points |
|--------|--------|
| URL is root `/` (homepage) | +4 |
| Page is in primary navigation (`<nav>`) | +3 |
| Sitemap `priority` is 0.9 or 1.0 | +2 |
| Sitemap `priority` is 0.7–0.8 | +1 |
| URL depth = 1 (e.g., `/docs`) | +2 |
| URL depth = 2 (e.g., `/docs/quickstart`) | +1 |
| `lastmod` within 30 days | +2 |
| `lastmod` within 90 days | +1 |
| Page has 3+ internal links pointing to it (hub page) | +2 |
| H1 matches a common LLM query term for the domain | +1 |
| Page contains code blocks (high technical value) | +1 |
| Page is linked from homepage | +1 |

### Subtractive signals (-)

| Signal | Points |
|--------|--------|
| URL depth >= 4 | -2 |
| Body text < 300 words | -2 |
| `lastmod` older than 2 years | -2 |
| Title contains "404", "Error", "Not Found" | -5 |
| URL contains `/tag/`, `/category/`, `/author/` | -3 |
| Page is a paginated URL (`?page=`, `/page/`) | -4 |
| Page has `noindex` meta tag | -5 |
| Title is generic (e.g., "Home", "Page", "Posts") | -2 |

### Final score clamping

```
finalScore = clamp(baseScore + additive - subtractive, min=1, max=10)
```

Pages with `finalScore <= 2` are excluded from the output automatically.

---

## 11. Handling Edge Cases

### Site has no sitemap
→ Fall back to recursive crawl (Phase 1, Step 1.3). Set max crawl depth to 3 and max pages to 300.

### Site returns 403/blocked to crawlers
→ Use Claude's web search tool to discover pages instead of direct fetching. Prompt: *"List all major pages and sections of example.com"*

### Single-page application (SPA)
→ Many SPAs don't render content for basic HTTP fetches. Solution: use a headless browser (Puppeteer/Playwright) in your backend for the content extraction phase, or fall back to web search discovery.

### Very large site (1000+ pages)
→ Apply a two-pass strategy:
1. First pass: analyze only depth-1 and depth-2 URLs + all URLs with sitemap priority >= 0.7
2. Second pass: for sections with fewer than 5 entries, go deeper into that section

Cap the final llms.txt at **150 links** total — beyond this, switch to `llms-full.txt` strategy (see below).

### Duplicate content / canonical mismatches
→ When a page's `<link rel="canonical">` points to a different URL, use the canonical URL in the output, not the crawled URL.

### Multilingual sites
→ Detect language from `<html lang="">` attribute. Default to the English version (`en`). Create a note in the llms.txt intro paragraph: *"This site is also available in French (/fr) and Spanish (/es)."*

### Private/authenticated pages
→ Detect these by: redirect to `/login`, response contains a login form, or URL matches common auth patterns. Exclude entirely.

### llms-full.txt strategy
For large sites, generate two files:
- `llms.txt` — top 50–80 most important pages (the LLM skimmable version)
- `llms-full.txt` — all 150+ pages with full detail

Reference the full version from the short version:
```markdown
> For a complete index of all pages, see [llms-full.txt](https://example.com/llms-full.txt).
```

---

## 12. API Integration Reference

### Model selection

Always use `claude-sonnet-4-20250514` for all phases. It provides the best balance of cost, speed, and quality for this use case.

### Phase 3 API call (per-page analysis batch)

```javascript
const response = await fetch("https://api.anthropic.com/v1/messages", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "x-api-key": process.env.ANTHROPIC_API_KEY,
    "anthropic-version": "2023-06-01"
  },
  body: JSON.stringify({
    model: "claude-sonnet-4-20250514",
    max_tokens: 4096,
    system: PAGE_ANALYSIS_SYSTEM_PROMPT,
    messages: [
      {
        role: "user",
        content: `Analyze these pages and return a JSON array:\n\n${JSON.stringify(pageBatch, null, 2)}`
      }
    ]
  })
});

const data = await response.json();
const text = data.content[0].text.trim();
// Strip any accidental ```json fences
const cleaned = text.replace(/^```json\n?/, "").replace(/\n?```$/, "");
const pageMetadata = JSON.parse(cleaned);
```

### Phase 4 API call (final generation) — with web search

```javascript
const response = await fetch("https://api.anthropic.com/v1/messages", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "x-api-key": process.env.ANTHROPIC_API_KEY,
    "anthropic-version": "2023-06-01"
  },
  body: JSON.stringify({
    model: "claude-sonnet-4-20250514",
    max_tokens: 4096,
    system: LLMS_TXT_GENERATION_SYSTEM_PROMPT,
    tools: [
      { type: "web_search_20250305", name: "web_search" }  // optional: let Claude verify site info
    ],
    messages: [
      {
        role: "user",
        content: buildFinalPrompt(domain, siteOverview, allPageMetadata)
      }
    ]
  })
});

const data = await response.json();
// Collect all text blocks (web search may produce multiple content blocks)
const llmsTxtContent = data.content
  .filter(block => block.type === "text")
  .map(block => block.text)
  .join("\n")
  .trim();
```

### Error handling

```javascript
// Always wrap API calls
try {
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 429) {
      // Rate limited — wait and retry with exponential backoff
      await sleep(retryDelay);
      retryDelay *= 2;
      continue;
    }
    throw new Error(`API error ${response.status}: ${data.error?.message}`);
  }
  return data;
} catch (err) {
  console.error("Claude API call failed:", err);
  throw err;
}
```

---

## 13. Rate Limiting & Cost Management

### Token estimation

| Phase | Tokens per call | Calls for 200-page site | Total tokens |
|-------|----------------|------------------------|--------------|
| Phase 3 (per-page analysis) | ~8,000 in / ~2,000 out | 10–15 batches | ~150k in / ~30k out |
| Phase 4 (final generation) | ~15,000 in / ~3,000 out | 1 | ~15k in / ~3k out |
| **Total** | | | **~165k in / ~33k out** |

At Sonnet 4 pricing (~$3/MTok input, ~$15/MTok output), a 200-page site costs approximately **$0.50–$1.00** per generation.

### Caching strategy

Cache page content extractions (Phase 2 output) aggressively:
- Cache key: `hash(url + lastmod)` 
- TTL: 7 days for static content, 1 day for frequently updated pages
- Store in Redis or a simple file cache
- Re-fetch only if `lastmod` has changed since last crawl

Cache the final llms.txt with a 24-hour TTL. Offer users a "regenerate" button to bust the cache.

### Concurrency limits

- Phase 2 (HTTP fetching): max 10 concurrent requests per domain (be polite)
- Phase 3 (Claude API calls): max 5 concurrent API calls
- Add 200ms delay between page fetches to avoid overwhelming small servers

---

## 14. Full Implementation Pseudocode

```
function generateLlmsTxt(inputUrl):

  # Normalize input
  domain = extractDomain(inputUrl)
  baseUrl = "https://" + domain

  # PHASE 1: URL Discovery
  exclusions = fetchRobotsTxt(baseUrl)
  sitemapUrls = discoverSitemaps(baseUrl, exclusions)
  
  if sitemapUrls.isEmpty():
    allUrls = recursiveCrawl(baseUrl, maxDepth=3, maxPages=300, exclusions)
  else:
    allUrls = parseSitemaps(sitemapUrls)
  
  filteredUrls = filterUrls(allUrls, exclusions)
  # filteredUrls is list of { url, priority, lastmod, depth }

  # PHASE 2: Content Extraction
  pageData = []
  for url in filteredUrls [concurrency=10]:
    html = fetchPage(url)
    if html.isError(): continue
    extracted = extractContent(html)  # title, og, h1, h2s, bodyText, canonicalMatch
    if not extracted.canonicalMatch: continue
    if extracted.noindex: continue
    pageData.append({ ...url, ...extracted, heuristicType: detectType(url, extracted) })

  # PHASE 3: Per-Page Analysis
  batches = chunkArray(pageData, size=15)
  analyzedPages = []
  
  for batch in batches [concurrency=5]:
    result = callClaude(
      systemPrompt = PAGE_ANALYSIS_SYSTEM_PROMPT,
      userContent = buildBatchPrompt(batch)
    )
    parsed = parseJSON(result)
    analyzedPages.extend(parsed)

  # Filter and sort
  includedPages = analyzedPages.filter(p => p.include && p.importance > 2)
  groupedBySection = groupBy(includedPages, "section")
  for section in groupedBySection:
    section.pages = sortBy(section.pages, "importance", desc).slice(0, 30)

  # PHASE 4: Final Synthesis
  siteOverview = {
    domain,
    totalAnalyzed: pageData.length,
    totalIncluded: includedPages.length,
    homepageTitle: findHomepage(analyzedPages).title,
    homepageDescription: findHomepage(analyzedPages).description,
    sections: Object.keys(groupedBySection)
  }

  llmsTxtContent = callClaude(
    systemPrompt = LLMS_TXT_GENERATION_SYSTEM_PROMPT,
    tools = [webSearch],
    userContent = buildFinalPrompt(siteOverview, groupedBySection)
  )

  # Post-processing
  validated = validateLlmsTxtStructure(llmsTxtContent)
  sanitized = sanitize(validated)

  return sanitized
```

---

## 15. Output Quality Checklist

Before returning the llms.txt to the user, validate:

### Structure validation
- [ ] File starts with exactly one `# ` H1
- [ ] H1 is followed by a `>` blockquote
- [ ] At least one `## ` section exists
- [ ] Each section has at least one `- [...](...):` link
- [ ] No broken or hallucinated URLs (all URLs must exist in the original crawl)

### Content quality
- [ ] Blockquote is specific and dense (not generic like "Welcome to our website")
- [ ] Each link description is unique and informative (not "Learn more" or "Click here")
- [ ] No legal pages (Privacy Policy, Terms, Cookie Notice) included
- [ ] No paginated or archive URLs included
- [ ] Homepage is the first link OR the intro clearly describes the site
- [ ] Section order puts technical content (Docs, API) before marketing (Blog, About)

### Length guidelines
- [ ] Total file length: 1,000–8,000 characters (sweet spot for LLM consumption)
- [ ] If > 8,000 characters: trim lower-importance entries, consider `llms-full.txt`
- [ ] If < 500 characters: site may be too small or crawl failed — flag to user

### Final output format
```
# Site Name

> Precise one-sentence description.

Optional context paragraph.

## Documentation

- [Page](url): Description.

## API Reference

- [Page](url): Description.
```

---

*This document covers the complete logic pipeline for generating production-quality llms.txt files. For GEO integration, expose this as a background job with webhook callback, store results per domain with a 24-hour cache, and surface the output directly in your GEO dashboard alongside other optimization signals.*
