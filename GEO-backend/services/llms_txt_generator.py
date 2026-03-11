"""
llms.txt Generator Service
==========================
A production-grade llms.txt generator that crawls a website and produces 
a spec-compliant, LLM-optimized llms.txt file.

Phases:
  1. URL Discovery (robots.txt, sitemap, recursive crawl)
  2. Content Extraction (fetch pages, extract metadata & text)
  3. Per-Page Analysis with Claude (classify, summarize, score)
  4. Site-Wide Synthesis & llms.txt Generation (Claude)
"""

import os
import re
import json
import math
import asyncio
import logging
import hashlib
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin, urldefrag
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup
import contextlib

logger = logging.getLogger(__name__)

# ─── Paid.ai / OpenTelemetry Tracing ──────────────────────────────────────────
# Try importing the using_attributes context manager for Paid.ai trace grouping.
# If not installed, Claude calls still work — they just won't have user metadata.
try:
    from openinference.instrumentation import using_attributes
except ImportError:
    using_attributes = None


def _build_paid_context(user_id: str = None):
    """Build a context manager that attaches Paid.ai trace attributes to all
    Anthropic API calls made inside it.  Falls back to a no-op when the
    openinference library is unavailable or no user_id is provided."""
    @contextlib.contextmanager
    def _ctx():
        if using_attributes and user_id:
            with using_attributes(
                user_id=user_id,
                session_id=user_id,
                metadata={
                    "externalCustomerId": user_id,
                    "externalProductId": "llms_txt_generator",
                },
                tags=["llms_txt_generator"],
            ):
                yield
        else:
            yield
    return _ctx()


# ─── Configuration ─────────────────────────────────────────────────────────────

MAX_PAGES = 30
MAX_CRAWL_DEPTH = 3
FETCH_TIMEOUT = 10
CONCURRENT_FETCHES = 10
CONCURRENT_API_CALLS = 5
BATCH_SIZE = 15
MAX_BODY_TEXT_CHARS = 2000
MAX_LINKS_PER_SECTION = 30
USER_AGENT = "LLMs-txt-generator/1.0 (GEO tool)"

# URL patterns to exclude
EXCLUDE_PATTERNS = [
    r'/login', r'/signin', r'/signup', r'/register', r'/dashboard',
    r'/admin', r'/wp-admin', r'/wp-login',
    r'/api/', r'\.json$', r'\.xml$',
    r'\.jpg$', r'\.jpeg$', r'\.png$', r'\.gif$', r'\.svg$', r'\.webp$',
    r'\.pdf$', r'\.zip$', r'\.tar$', r'\.gz$',
    r'\.css$', r'\.js$', r'\.woff', r'\.ttf', r'\.eot',
    r'\?page=', r'/page/\d+',
    r'/tag/', r'/category/', r'/author/',
    r'\?utm_', r'\?ref=', r'\?fbclid',
    r'/cart', r'/checkout', r'/account',
    r'/search', r'/feed', r'/rss',
]

# ─── Phase 1: URL Discovery ───────────────────────────────────────────────────

def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication."""
    url = urldefrag(url)[0]  # Remove fragment
    url = url.rstrip('/')
    url = url.lower()
    # Remove common tracking params
    parsed = urlparse(url)
    if parsed.query:
        params = parsed.query.split('&')
        filtered = [p for p in params if not any(p.startswith(prefix) for prefix in ['utm_', 'ref=', 'fbclid=', 'gclid='])]
        clean_query = '&'.join(filtered)
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_query:
            url += f"?{clean_query}"
    return url


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc or parsed.path.split('/')[0]


def fetch_robots_txt(base_url: str) -> Tuple[List[str], List[str]]:
    """Fetch robots.txt and extract disallow paths and sitemap URLs."""
    disallow_paths = []
    sitemap_urls = []
    
    try:
        resp = requests.get(f"{base_url}/robots.txt", timeout=FETCH_TIMEOUT, 
                          headers={"User-Agent": USER_AGENT})
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                line = line.strip()
                if line.lower().startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        disallow_paths.append(path)
                elif line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    # Re-join in case the URL had a colon
                    if not sitemap_url.startswith("http"):
                        sitemap_url = "Sitemap:" + sitemap_url
                        sitemap_url = sitemap_url.split("Sitemap:", 1)[1].strip()
                    sitemap_urls.append(sitemap_url)
            logger.info(f"  robots.txt: {len(disallow_paths)} disallow, {len(sitemap_urls)} sitemaps")
    except Exception as e:
        logger.warning(f"  Could not fetch robots.txt: {e}")
    
    return disallow_paths, sitemap_urls


def parse_sitemap(url: str, visited: set = None) -> List[Dict]:
    """Parse a sitemap XML and return list of URL entries."""
    if visited is None:
        visited = set()
    
    if url in visited:
        return []
    visited.add(url)
    
    entries = []
    try:
        resp = requests.get(url, timeout=FETCH_TIMEOUT, headers={"User-Agent": USER_AGENT})
        if resp.status_code != 200:
            return []
        
        # Try to parse as XML
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            return []
        
        # Handle namespace
        ns = ''
        if root.tag.startswith('{'):
            ns = root.tag.split('}')[0] + '}'
        
        # Check if this is a sitemap index
        sitemap_tags = root.findall(f'{ns}sitemap')
        if sitemap_tags:
            for sitemap in sitemap_tags:
                loc = sitemap.find(f'{ns}loc')
                if loc is not None and loc.text:
                    entries.extend(parse_sitemap(loc.text.strip(), visited))
            return entries
        
        # Parse URL entries
        for url_elem in root.findall(f'{ns}url'):
            loc = url_elem.find(f'{ns}loc')
            if loc is None or not loc.text:
                continue
            
            entry = {"url": loc.text.strip(), "priority": 0.5, "lastmod": None, "source": "sitemap"}
            
            priority = url_elem.find(f'{ns}priority')
            if priority is not None and priority.text:
                try:
                    entry["priority"] = float(priority.text)
                except ValueError:
                    pass
            
            lastmod = url_elem.find(f'{ns}lastmod')
            if lastmod is not None and lastmod.text:
                entry["lastmod"] = lastmod.text.strip()
            
            entries.append(entry)
        
        logger.info(f"  Sitemap {url}: {len(entries)} URLs")
    except Exception as e:
        logger.warning(f"  Error parsing sitemap {url}: {e}")
    
    return entries


def discover_urls(base_url: str) -> List[Dict]:
    """Phase 1: Discover all URLs from a website."""
    domain = extract_domain(base_url)
    logger.info(f"Phase 1: URL Discovery for {domain}")
    
    # Step 1.1: Check robots.txt
    disallow_paths, sitemap_urls = fetch_robots_txt(base_url)
    
    # Step 1.2: Try sitemaps
    all_entries = []
    
    # Add sitemaps from robots.txt
    for sitemap_url in sitemap_urls:
        all_entries.extend(parse_sitemap(sitemap_url))
    
    # Try common sitemap locations if none found
    if not all_entries:
        for path in ['/sitemap.xml', '/sitemap_index.xml', '/sitemap/']:
            entries = parse_sitemap(f"{base_url}{path}")
            if entries:
                all_entries.extend(entries)
                break
    
    # Step 1.3: Fallback to recursive crawl if no sitemap
    if not all_entries:
        logger.info("  No sitemap found, falling back to recursive crawl")
        all_entries = recursive_crawl(base_url, MAX_CRAWL_DEPTH, MAX_PAGES)
    
    # Step 1.4: URL Filtering
    filtered = filter_urls(all_entries, domain, disallow_paths)
    
    # Deduplicate
    seen = set()
    unique_entries = []
    for entry in filtered:
        normalized = normalize_url(entry["url"])
        if normalized not in seen:
            seen.add(normalized)
            entry["url"] = entry["url"].rstrip('/')  # Keep original case but strip trailing slash
            unique_entries.append(entry)
    
    # Cap at MAX_PAGES
    unique_entries = unique_entries[:MAX_PAGES]
    
    logger.info(f"  Phase 1 complete: {len(unique_entries)} URLs discovered")
    return unique_entries


def recursive_crawl(base_url: str, max_depth: int, max_pages: int) -> List[Dict]:
    """Fallback crawler when no sitemap is available."""
    domain = extract_domain(base_url)
    visited = set()
    entries = []
    queue = [(base_url, 0)]
    
    while queue and len(entries) < max_pages:
        url, depth = queue.pop(0)
        normalized = normalize_url(url)
        
        if normalized in visited or depth > max_depth:
            continue
        visited.add(normalized)
        
        try:
            resp = requests.get(url, timeout=FETCH_TIMEOUT, 
                              headers={"User-Agent": USER_AGENT},
                              allow_redirects=True)
            if resp.status_code != 200 or 'text/html' not in resp.headers.get('content-type', ''):
                continue
            
            entries.append({
                "url": url,
                "priority": max(0.3, 0.9 - (depth * 0.2)),
                "lastmod": None,
                "depth": depth,
                "source": "crawl"
            })
            
            # Extract links for crawling
            if depth < max_depth:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    full_url = urljoin(url, href)
                    parsed = urlparse(full_url)
                    
                    # Only follow same-domain links
                    if parsed.netloc == domain or not parsed.netloc:
                        queue.append((full_url, depth + 1))
            
        except Exception:
            continue
    
    return entries


def filter_urls(entries: List[Dict], domain: str, disallow_paths: List[str]) -> List[Dict]:
    """Filter out URLs that shouldn't be in llms.txt."""
    filtered = []
    
    for entry in entries:
        url = entry["url"]
        parsed = urlparse(url)
        
        # Must be same domain
        if parsed.netloc and parsed.netloc != domain:
            continue
        
        path = parsed.path.lower()
        
        # Check against disallow paths from robots.txt
        disallowed = False
        for disallow in disallow_paths:
            if path.startswith(disallow.lower()):
                disallowed = True
                break
        if disallowed:
            continue
        
        # Check against exclusion patterns
        excluded = False
        for pattern in EXCLUDE_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                excluded = True
                break
        if excluded:
            continue
        
        filtered.append(entry)
    
    return filtered


# ─── Phase 2: Content Extraction ──────────────────────────────────────────────

def extract_page_content(url: str) -> Optional[Dict]:
    """Fetch a page and extract structured content."""
    try:
        resp = requests.get(url, timeout=FETCH_TIMEOUT, 
                          headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
                          allow_redirects=True)
        
        if resp.status_code != 200:
            return None
        
        if 'text/html' not in resp.headers.get('content-type', ''):
            return None
        
        final_url = resp.url
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Extract metadata from <head>
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '')
        
        og_title = ""
        og_title_tag = soup.find('meta', property='og:title')
        if og_title_tag:
            og_title = og_title_tag.get('content', '')
        
        og_desc = ""
        og_desc_tag = soup.find('meta', property='og:description')
        if og_desc_tag:
            og_desc = og_desc_tag.get('content', '')
        
        # Check canonical
        canonical = None
        canonical_tag = soup.find('link', rel='canonical')
        if canonical_tag:
            canonical = canonical_tag.get('href', '')
        
        canonical_match = True
        if canonical:
            canon_norm = normalize_url(canonical)
            url_norm = normalize_url(url)
            if canon_norm != url_norm:
                canonical_match = False
        
        # Check noindex
        noindex = False
        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        if robots_meta and 'noindex' in (robots_meta.get('content', '') or '').lower():
            noindex = True
        
        # Extract structural signals
        h1 = ""
        h1_tag = soup.find('h1')
        if h1_tag:
            h1 = h1_tag.get_text(strip=True)
        
        h2s = []
        for h2_tag in soup.find_all('h2'):
            h2_text = h2_tag.get_text(strip=True)
            if h2_text:
                h2s.append(h2_text[:100])
        h2s = h2s[:10]  # Limit
        
        # Extract main body text
        body_text = ""
        main_content = (soup.find('main') or soup.find('article') or 
                       soup.find(id='content') or soup.find(class_='post-content') or 
                       soup.find('body'))
        
        if main_content:
            # Remove script, style, nav, header, footer
            for tag in main_content.find_all(['script', 'style', 'nav', 'header', 'footer', 'noscript']):
                tag.decompose()
            body_text = main_content.get_text(separator=' ', strip=True)
            body_text = re.sub(r'\s+', ' ', body_text)[:MAX_BODY_TEXT_CHARS]
        
        # Detect page type heuristically
        heuristic_type = detect_page_type(url, h1, body_text, soup)
        
        return {
            "url": url,
            "finalUrl": str(final_url),
            "title": title[:200],
            "ogTitle": og_title[:200],
            "description": description[:300],
            "ogDescription": og_desc[:300],
            "h1": h1[:200],
            "h2s": h2s,
            "bodyText": body_text,
            "heuristicType": heuristic_type,
            "canonicalMatch": canonical_match,
            "noindex": noindex
        }
    
    except Exception as e:
        logger.warning(f"  Error extracting {url}: {e}")
        return None


def detect_page_type(url: str, h1: str, body_text: str, soup: BeautifulSoup) -> str:
    """Heuristic page type detection."""
    path = urlparse(url).path.lower()
    
    type_patterns = [
        (r'/(docs?|documentation|guide)', 'documentation'),
        (r'/(blog|posts?|articles?)', 'blog'),
        (r'/(api|reference)', 'api-reference'),
        (r'/(pricing|plans?)', 'pricing'),
        (r'^/$|/home$', 'homepage'),
        (r'/(about|team|company)', 'about'),
        (r'/(changelog|releases?|whats-new)', 'changelog'),
        (r'/(tutorials?|learn)', 'tutorial'),
        (r'/(integrations?)', 'integrations'),
        (r'/(sdk|libraries?)', 'sdks'),
    ]
    
    for pattern, page_type in type_patterns:
        if re.search(pattern, path):
            return page_type
    
    # Check for article tag with dates (blog indicator)
    if soup.find('article') and soup.find('time'):
        return 'blog'
    
    return 'other'


# ─── Phase 3: Per-Page Analysis with Claude ───────────────────────────────────

PAGE_ANALYSIS_SYSTEM_PROMPT = """You are a technical content analyst specializing in LLM indexing.
For each page provided, output ONLY a JSON array. No explanation.
Each element must have exactly these fields:
{
  "url": "exact URL",
  "title": "clean, concise title (max 60 chars)",
  "description": "1-sentence description optimized for LLM understanding (max 120 chars)",
  "section": one of: ["Documentation", "API Reference", "Blog", "Tutorials", 
                       "Pricing", "About", "Changelog", "Homepage", "Integrations", "Other"],
  "importance": integer 1-10 (10 = most important for LLMs to know about),
  "include": boolean (false if page adds no value for LLMs: privacy policy, 404s, tag archives, etc.)
}

Scoring guidelines:
- Homepage: importance 8-10
- Core product/feature pages: 7-9
- Documentation/API reference: 7-9
- Pricing pages: 6-8
- Blog posts (recent, substantive): 4-6
- About/team pages: 3-5
- Legal/privacy/terms: importance 1-2, include: false
- Thin content pages: importance 1-3"""


LLMS_TXT_GENERATION_SYSTEM_PROMPT = """You are an expert technical writer specializing in the llms.txt standard for Generative Engine Optimization (GEO).

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
- No code fences, no explanation, no preamble"""


def analyze_pages_batch(pages: List[Dict], api_key: str, user_id: str = None) -> List[Dict]:
    """Send a batch of pages to Claude for structured analysis."""
    import anthropic
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Prepare simplified page data for the prompt
    simplified = []
    for p in pages:
        simplified.append({
            "url": p.get("url", ""),
            "title": p.get("title", ""),
            "description": p.get("description", ""),
            "h1": p.get("h1", ""),
            "h2s": p.get("h2s", []),
            "bodyText": p.get("bodyText", "")[:1500],
            "heuristicType": p.get("heuristicType", "other")
        })
    
    try:
        with _build_paid_context(user_id):
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=PAGE_ANALYSIS_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"Analyze these pages and return a JSON array:\n\n{json.dumps(simplified, indent=2)}"
                }]
            )
        
        text = response.content[0].text.strip()
        # Strip accidental code fences
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        return json.loads(text)
    
    except Exception as e:
        logger.error(f"  Claude batch analysis error: {e}")
        # Fallback: return basic metadata from heuristics
        fallback = []
        for p in pages:
            fallback.append({
                "url": p.get("url", ""),
                "title": p.get("title", p.get("h1", ""))[:60],
                "description": p.get("description", "")[:120],
                "section": _heuristic_to_section(p.get("heuristicType", "other")),
                "importance": 5,
                "include": True
            })
        return fallback


def _heuristic_to_section(heuristic_type: str) -> str:
    """Convert heuristic type to section name."""
    mapping = {
        "documentation": "Documentation",
        "api-reference": "API Reference",
        "blog": "Blog",
        "tutorial": "Tutorials",
        "pricing": "Pricing",
        "homepage": "Homepage",
        "about": "About",
        "changelog": "Changelog",
        "integrations": "Integrations",
        "sdks": "Documentation",
    }
    return mapping.get(heuristic_type, "Other")


def generate_llms_txt_content(domain: str, site_overview: Dict, grouped_pages: Dict, api_key: str, user_id: str = None) -> str:
    """Phase 4: Final synthesis — generate the llms.txt file content."""
    import anthropic
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Build section text
    sections_text = ""
    for section_name, pages in grouped_pages.items():
        sections_text += f"\n## {section_name}\n"
        for p in pages:
            sections_text += f"- [{p['title']}]({p['url']}): {p['description']} [importance:{p['importance']}]\n"
    
    # Top 5 most important pages
    all_pages = []
    for pages in grouped_pages.values():
        all_pages.extend(pages)
    top_5 = sorted(all_pages, key=lambda x: x.get('importance', 0), reverse=True)[:5]
    top_5_text = "\n".join([
        f"{i+1}. {p['url']} — {p['title']} (importance: {p['importance']})"
        for i, p in enumerate(top_5)
    ])
    
    prompt = f"""Generate a complete llms.txt file for this website.

Domain: {domain}
Total pages analyzed: {site_overview.get('totalAnalyzed', 0)}
Pages to include: {site_overview.get('totalIncluded', 0)}

Site overview signals:
- Homepage title: "{site_overview.get('homepageTitle', domain)}"
- Homepage description: "{site_overview.get('homepageDescription', '')}"
- Primary sections detected: {', '.join(site_overview.get('sections', []))}

Top 5 most important pages:
{top_5_text}

All pages (grouped by section, sorted by importance):
{sections_text}

Now generate the best possible llms.txt. Follow the llmstxt.org spec exactly."""

    try:
        with _build_paid_context(user_id):
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=LLMS_TXT_GENERATION_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
        
        # Collect all text blocks
        llms_txt = ""
        for block in response.content:
            if hasattr(block, 'text'):
                llms_txt += block.text
        
        return llms_txt.strip()
    
    except Exception as e:
        logger.error(f"  Claude synthesis error: {e}")
        raise


# ─── Main Pipeline ─────────────────────────────────────────────────────────────

def generate_llms_txt(
    input_url: str,
    progress_callback=None,
    user_id: str = None
) -> Dict[str, Any]:
    """
    Main entry point: generate an llms.txt file for a given website URL.
    
    Args:
        input_url: The website URL to generate llms.txt for
        progress_callback: Optional callback fn(progress: int, step: str)
        
    Returns:
        Dict with keys: llms_txt, domain, stats, pages_analyzed
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    
    def update_progress(progress: int, step: str):
        if progress_callback:
            progress_callback(progress, step)
        logger.info(f"  [{progress}%] {step}")
    
    # Normalize input
    if not input_url.startswith('http'):
        input_url = f"https://{input_url}"
    
    parsed = urlparse(input_url)    
    domain = parsed.netloc
    base_url = f"{parsed.scheme}://{domain}"
    
    update_progress(5, "Starting URL discovery...")
    
    # ───────────────────────────────────────────────────
    # PHASE 1: URL Discovery
    # ───────────────────────────────────────────────────
    update_progress(10, "Crawling robots.txt and sitemaps...")
    url_entries = discover_urls(base_url)
    
    if not url_entries:
        # Try without www or with www
        if 'www.' in domain:
            alt_domain = domain.replace('www.', '')
        else:
            alt_domain = f'www.{domain}'
        alt_base = f"{parsed.scheme}://{alt_domain}"
        url_entries = discover_urls(alt_base)
        if url_entries:
            domain = alt_domain
            base_url = alt_base
    
    if not url_entries:
        raise ValueError(f"Could not discover any pages for {domain}. The site may be blocking crawlers.")
    
    update_progress(20, f"Found {len(url_entries)} URLs to analyze")
    
    # ───────────────────────────────────────────────────
    # PHASE 2: Content Extraction
    # ───────────────────────────────────────────────────
    update_progress(25, "Extracting page content...")
    
    page_data = []
    total = len(url_entries)
    
    for i, entry in enumerate(url_entries):
        if i % 10 == 0:
            pct = 25 + int((i / total) * 25)  # 25-50%
            update_progress(pct, f"Extracting content from page {i+1}/{total}...")
        
        extracted = extract_page_content(entry["url"])
        if not extracted:
            continue
        if not extracted["canonicalMatch"]:
            continue
        if extracted["noindex"]:
            continue
        
        # Merge with sitemap data
        extracted["priority"] = entry.get("priority", 0.5)
        extracted["lastmod"] = entry.get("lastmod")
        extracted["depth"] = entry.get("depth", 1)
        extracted["source"] = entry.get("source", "sitemap")
        
        page_data.append(extracted)
    
    if not page_data:
        raise ValueError(f"Could not extract content from any pages on {domain}.")
    
    update_progress(50, f"Extracted content from {len(page_data)} pages")
    
    # ───────────────────────────────────────────────────
    # PHASE 3: Per-Page Analysis with Claude
    # ───────────────────────────────────────────────────
    update_progress(55, "Analyzing pages with AI...")
    
    # Batch pages
    batches = [page_data[i:i+BATCH_SIZE] for i in range(0, len(page_data), BATCH_SIZE)]
    analyzed_pages = []
    
    for batch_idx, batch in enumerate(batches):
        pct = 55 + int((batch_idx / len(batches)) * 20)  # 55-75%
        update_progress(pct, f"AI analyzing batch {batch_idx+1}/{len(batches)}...")
        
        result = analyze_pages_batch(batch, api_key, user_id=user_id)
        analyzed_pages.extend(result)
    
    # Filter and sort
    included_pages = [p for p in analyzed_pages if p.get("include", True) and p.get("importance", 0) > 2]
    
    update_progress(75, f"AI analysis complete: {len(included_pages)} pages included")
    
    # Group by section
    grouped = {}
    for page in included_pages:
        section = page.get("section", "Other")
        if section not in grouped:
            grouped[section] = []
        grouped[section].append(page)
    
    # Sort within sections by importance, cap per section
    for section in grouped:
        grouped[section] = sorted(grouped[section], key=lambda x: x.get("importance", 0), reverse=True)[:MAX_LINKS_PER_SECTION]
    
    # Order sections by priority
    section_order = ["Homepage", "Documentation", "API Reference", "Tutorials", "Integrations", "Changelog", "Blog", "Pricing", "About", "Other"]
    ordered_grouped = {}
    for section in section_order:
        if section in grouped:
            ordered_grouped[section] = grouped[section]
    # Add any sections not in the standard order
    for section in grouped:
        if section not in ordered_grouped:
            ordered_grouped[section] = grouped[section]
    
    # Merge thin sections (< 3 pages)
    final_grouped = {}
    other_pages = ordered_grouped.pop("Other", [])
    
    for section, pages in ordered_grouped.items():
        if len(pages) < 2 and section not in ["Homepage", "Pricing"]:
            other_pages.extend(pages)
        else:
            final_grouped[section] = pages
    
    if other_pages:
        final_grouped["Other"] = other_pages
    
    # ───────────────────────────────────────────────────
    # PHASE 4: Final Synthesis
    # ───────────────────────────────────────────────────
    update_progress(80, "Generating llms.txt file...")
    
    # Find homepage
    homepage_title = domain
    homepage_desc = ""
    for page in analyzed_pages:
        url_path = urlparse(page.get("url", "")).path
        if url_path in ["", "/", "/home"]:
            homepage_title = page.get("title", domain)
            homepage_desc = page.get("description", "")
            break
    
    site_overview = {
        "domain": domain,
        "totalAnalyzed": len(page_data),
        "totalIncluded": len(included_pages),
        "homepageTitle": homepage_title,
        "homepageDescription": homepage_desc,
        "sections": list(final_grouped.keys())
    }
    
    llms_txt_content = generate_llms_txt_content(domain, site_overview, final_grouped, api_key, user_id=user_id)
    
    update_progress(90, "Validating and post-processing...")
    
    # ───────────────────────────────────────────────────
    # Post-Processing & Validation
    # ───────────────────────────────────────────────────
    llms_txt_content = post_process_llms_txt(llms_txt_content)
    
    # Build stats
    section_stats = {}
    for section, pages in final_grouped.items():
        section_stats[section] = len(pages)
    
    update_progress(100, "Generation complete!")
    
    return {
        "llms_txt": llms_txt_content,
        "domain": domain,
        "stats": {
            "total_urls_discovered": len(url_entries),
            "pages_extracted": len(page_data),
            "pages_included": len(included_pages),
            "sections": section_stats
        },
        "pages_analyzed": [{
            "url": p.get("url"),
            "title": p.get("title"),
            "section": p.get("section"),
            "importance": p.get("importance"),
            "include": p.get("include")
        } for p in analyzed_pages]
    }


def post_process_llms_txt(content: str) -> str:
    """Validate and clean up the generated llms.txt content."""
    # Remove code fences if present
    content = re.sub(r'^```(?:markdown)?\s*\n?', '', content)
    content = re.sub(r'\n?```\s*$', '', content)
    
    # Ensure starts with H1
    if not content.startswith('# '):
        lines = content.split('\n')
        # Try to find the H1 line
        h1_idx = next((i for i, line in enumerate(lines) if line.startswith('# ')), -1)
        if h1_idx > 0:
            content = '\n'.join(lines[h1_idx:])
    
    # Normalize line endings
    content = content.replace('\r\n', '\n')
    
    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in content.split('\n')]
    content = '\n'.join(lines)
    
    # Ensure proper spacing between sections
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()
