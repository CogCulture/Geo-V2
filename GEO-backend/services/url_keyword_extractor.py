import os
import logging
from bs4 import BeautifulSoup
import json
import requests
from typing import List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")

async def extract_keywords_from_url(url: str, brand_name: str, num_keywords: int = 40) -> Tuple[List[str], dict]:
    """
    Extract organic keywords from a URL using web scraping and Mistral LLM.
    
    Args:
        url (str): Website URL to extract content from
        brand_name (str): Brand name to exclude from keywords
        num_keywords (int): Number of keywords to generate (default: 20)
    
    Returns:
        Tuple[List[str], dict]: A tuple containing a list of organic keywords extracted from the webpage, and the raw extracted data (meta tags, descriptions).
    """
    try:
        logger.info(f"🔍 Extracting keywords from URL: {url}")
        
        # Step 1: Extract meta content from URL
        extracted_data = await extract_meta_and_schema(url)
        
        if not extracted_data or not any([
            extracted_data.get('meta_description'),
            extracted_data.get('meta_tags')
        ]):
            logger.warning(f"⚠️ No content extracted from URL: {url}")
            return [], {}
        
        # Step 2: Generate organic keywords using Mistral
        keywords = generate_organic_keywords_from_content(
            extracted_data,
            brand_name,
            num_keywords
        )
        
        if keywords:
            logger.info(f"✅ Extracted {len(keywords)} keywords from URL")
            return keywords, extracted_data
        else:
            logger.warning("⚠️ No keywords generated from URL content")
            return [], extracted_data
    
    except Exception as e:
        logger.error(f"❌ Error extracting keywords from URL: {str(e)}")
        return [], {}


def _extract_data_from_html(html_content: str) -> dict:
    """
    Parse HTML content and extract meta tags, description, and organization schema.
    
    Args:
        html_content (str): Raw HTML string
    
    Returns:
        dict: Extracted content including meta tags, description, and schema
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    extracted_data = {
        'meta_tags': {},
        'meta_description': '',
        'organization_schema': []
    }
    
    # Extract META TAGS
    meta_tags = soup.find_all('meta')
    if meta_tags:
        for meta in meta_tags:
            name = meta.get('name') or meta.get('property') or meta.get('http-equiv')
            content = meta.get('content')
            if name and content:
                extracted_data['meta_tags'][name] = content
    
    # Extract META DESCRIPTION
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if not meta_desc:
        meta_desc = soup.find('meta', attrs={'property': 'og:description'})
    if meta_desc and meta_desc.get('content'):
        extracted_data['meta_description'] = meta_desc.get('content')
    
    # Extract ORGANIZATIONAL SCHEMA
    schema_scripts = soup.find_all('script', type='application/ld+json')
    if schema_scripts:
        for script in schema_scripts:
            try:
                schema_data = json.loads(script.string)
                if isinstance(schema_data, dict):
                    schema_type = schema_data.get('@type', '')
                    if 'Organization' in schema_type or schema_type == 'Organization':
                        extracted_data['organization_schema'].append(schema_data)
                elif isinstance(schema_data, list):
                    for item in schema_data:
                        if isinstance(item, dict):
                            schema_type = item.get('@type', '')
                            if 'Organization' in schema_type or schema_type == 'Organization':
                                extracted_data['organization_schema'].append(item)
            except json.JSONDecodeError:
                continue
    
    return extracted_data


def _fetch_with_requests(url: str) -> Optional[dict]:
    """
    Fetch webpage content using requests (lightweight, no browser needed).
    Works reliably on all Python versions including 3.14.
    
    Args:
        url (str): The URL to fetch
    
    Returns:
        dict or None: Extracted data, or None on failure
    """
    try:
        logger.info(f"📄 Fetching webpage content via HTTP request from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        html_content = response.text
        extracted_data = _extract_data_from_html(html_content)
        
        logger.info(
            f"✅ Extracted meta content (HTTP): {len(extracted_data['meta_tags'])} meta tags, "
            f"description: {bool(extracted_data['meta_description'])}"
        )
        
        return extracted_data
    
    except Exception as e:
        logger.warning(f"⚠️ HTTP request fetch failed: {str(e)}")
        return None


def _fetch_with_playwright_sync(url: str) -> Optional[dict]:
    """
    Fetch webpage content using Playwright SYNCHRONOUSLY in a separate thread.
    This avoids the Python 3.14 Windows asyncio subprocess issue by running
    Playwright's sync API, which manages its own event loop internally.
    
    Args:
        url (str): The URL to fetch
    
    Returns:
        dict or None: Extracted data, or None on failure
    """
    try:
        from playwright.sync_api import sync_playwright
        
        logger.info(f"🌐 Fetching webpage content via Playwright (sync) from: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                java_script_enabled=True
            )
            
            page = context.new_page()
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=50000)
                    page.wait_for_timeout(5000)
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Retry {attempt + 1}/{max_retries} due to: {str(e)[:100]}")
                    page.wait_for_timeout(4000)
            
            html_content = page.content()
            browser.close()
            
            extracted_data = _extract_data_from_html(html_content)
            
            logger.info(
                f"✅ Extracted meta content (Playwright): {len(extracted_data['meta_tags'])} meta tags, "
                f"description: {bool(extracted_data['meta_description'])}"
            )
            
            return extracted_data
    
    except Exception as e:
        logger.error(f"❌ Playwright fetch failed: {str(e)}")
        return None


async def extract_meta_and_schema(url: str) -> dict:
    """
    Extract meta tags, meta description, and organizational schema from URL.
    Uses requests as primary method (fast, reliable), falls back to Playwright
    if requests yields no useful content (e.g. JS-rendered pages).
    
    Args:
        url (str): The URL of the webpage to scrape
    
    Returns:
        dict: Extracted content including meta tags, description, and schema
    """
    try:
        logger.info(f"📄 Fetching webpage content from: {url}")
        
        # Primary method: use requests (fast, no subprocess issues on Python 3.14)
        extracted_data = _fetch_with_requests(url)
        
        # Check if we got meaningful content
        if extracted_data and any([
            extracted_data.get('meta_description'),
            extracted_data.get('meta_tags')
        ]):
            return extracted_data
        
        # Fallback: use Playwright sync API in a separate thread
        # This avoids the Python 3.14 Windows asyncio subprocess_exec issue
        # by not using async_playwright (which requires subprocess_exec on the running loop)
        logger.info("🔄 Requests didn't yield enough content, trying Playwright fallback...")
        import asyncio
        playwright_data = await asyncio.to_thread(_fetch_with_playwright_sync, url)
        
        if playwright_data:
            return playwright_data
        
        # If both methods failed, return whatever we got from requests (may be empty)
        return extracted_data or {}
    
    except Exception as e:
        logger.error(f"❌ Error extracting meta content: {str(e)}")
        return {}

def generate_organic_keywords_from_content(
    content_data: dict,
    brand_name: str,
    num_keywords: int = 40
) -> List[str]:
    """
    Use Mistral LLM to generate organic keywords from extracted content.
    
    Args:
        content_data (dict): Extracted content from webpage
        brand_name (str): Brand name to exclude from keywords
        num_keywords (int): Number of keywords to generate
    
    Returns:
        List[str]: Generated organic keywords
    """
    if not MISTRAL_API_KEY:
        logger.error("❌ MISTRAL_API_KEY not found in environment variables")
        return []
    
    try:
        logger.info(f"🤖 Generating organic keywords using Mistral AI...")
        
        # Prepare content summary
        content_summary = f"""
Meta Description: {content_data.get('meta_description', '')}

Meta Tags:
{json.dumps(content_data.get('meta_tags', {}), indent=2)}

Organization Schema:
{json.dumps(content_data.get('organization_schema', []), indent=2)}
"""
        
        # Prepare prompt for Mistral
        prompt = f"""Based on the following "content data : ({content_summary})" content, extract keywords and make a list of exactly {num_keywords} ORGANIC SEO keywords and key phrases.
IMPORTANT RULES:
- DO NOT include the brand name "{brand_name}" or any variations of it
- Strictly do not repeat any keyword more than twice.
- Keywords should be extracted only from the content data, Do not create anything new from your side. 

Please provide a JSON array of EXACTLY {num_keywords} organic keywords.

Format: ["keyword1", "keyword2", "keyword3", ...]

Return ONLY the JSON array, no explanation or markdown."""
        
        # Call Mistral API
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "mistral-small-latest",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Extract keywords from response
        keywords_text = result['choices'][0]['message']['content']
        
        # Try to parse as JSON
        try:
            # Remove markdown code blocks if present
            keywords_text = keywords_text.strip()
            if keywords_text.startswith("```json"):
                keywords_text = keywords_text[7:]
            if keywords_text.startswith("```"):
                keywords_text = keywords_text[3:]
            if keywords_text.endswith("```"):
                keywords_text = keywords_text[:-3]
            keywords_text = keywords_text.strip()
            
            keywords = json.loads(keywords_text)
            
            # Validate keywords
            if isinstance(keywords, list):
                # Filter out any keywords containing brand name
                keywords = [
                    k for k in keywords
                    if isinstance(k, str) and brand_name.lower() not in k.lower()
                ]
                
                # Limit to requested number
                keywords = keywords[:num_keywords]
                
                logger.info(f"✅ Generated {len(keywords)} organic keywords")
                return keywords
            else:
                logger.warning("⚠️ Mistral response is not a list")
                return []
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse Mistral response as JSON: {str(e)}")
            logger.debug(f"Response text: {keywords_text[:200]}")
            return []
    
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error calling Mistral API: {str(e)}")
        return []
    
    except Exception as e:
        logger.error(f"❌ Error generating keywords: {str(e)}")
        return []