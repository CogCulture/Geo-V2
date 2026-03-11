import os
import asyncio
from typing import List, Dict, Any, Optional
import json

from dotenv import load_dotenv
load_dotenv()
# LLM imports
from anthropic import Anthropic
from openai import OpenAI
import google.genai as genai
import re
from google.genai import types
import requests
# Import Google AI Overview scraper
from services.google_ai_overview_scraper import extract_ai_overview_links, setup_driver
# Import BrightData scraper for Gemini, ChatGPT, Perplexity
from services.brightdata_scraper import scrape_llm_responses, is_scraper_configured

# API Keys
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize clients
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
       
def detect_available_llms() -> List[str]:
    """Dynamically detect which LLM APIs are available based on API keys or BrightData scrapers"""
    available = []
   
    if ANTHROPIC_API_KEY:
        available.append("Claude")
    if OPENAI_API_KEY or is_scraper_configured("ChatGPT"):
        available.append("ChatGPT")
    if PERPLEXITY_API_KEY or is_scraper_configured("Perplexity"):
        available.append("Perplexity")
    if GEMINI_API_KEY or is_scraper_configured("Gemini"):
        available.append("Gemini")  
    
    # Google AI Overview doesn't need API key - uses Selenium
    # Always available as it doesn't require API credentials
    available.append("Google AI Overview")
    
    return available

def unwrap_url(redirect_url):
    """Follows the Google redirect wrapper to get the clean destination URL."""
    # If it's not a Google redirect, return it as-is
    if "vertexaisearch.cloud.google.com/grounding-api-redirect" not in redirect_url:
        return redirect_url
        
    try:
        # Use a quick HEAD request to follow the redirect without downloading the page
        response = requests.head(redirect_url, allow_redirects=True, timeout=5)
        return response.url
    except Exception:
        # If the request fails (e.g., timeout), fallback to the original URL
        return redirect_url

def execute_prompts_multi_llm_sync(prompts: List[str], llms: Optional[List[str]] = None, brand_name: str = None, user_id: str = None) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper - FIXED VERSION with Gemini Rate Limit Handling
    """
    print(f"\n🚀 Executing {len(prompts)} prompts with {llms}")
    
    all_responses = []
    
    # ✅ NORMALIZE LLM NAMES: Handle "Gemini" as "Google AI"
    normalized_llms = []
    for llm in llms:
        llm_lower = llm.lower()
        if llm_lower in ["gemini"]:
            normalized_llms.append("Gemini")
        elif llm_lower == "google ai overview":
            normalized_llms.append("Google AI Overview")
        elif llm_lower == "claude":
            normalized_llms.append("Claude")
        elif llm_lower == "mistral":
            normalized_llms.append("Mistral")
        elif llm_lower == "chatgpt":
            normalized_llms.append("ChatGPT")
        elif llm_lower == "perplexity":
            normalized_llms.append("Perplexity")
        else:
            normalized_llms.append(llm)
    
    # Remove duplicates while preserving order
    normalized_llms = list(dict.fromkeys(normalized_llms))
    print(f"📋 Normalized LLMs: {normalized_llms}")
    
    # Check if Google AI Overview is in the list
    has_google_ai_overview = "Google AI Overview" in normalized_llms
    
    # Handle Google AI Overview separately (Selenium-based)
    if has_google_ai_overview:
        print("\n📊 Processing Google AI Overview (Selenium scraping)...")
        try:
            driver = setup_driver()
            print("  ✅ Chrome driver initialized")
            
            for prompt_index, prompt in enumerate(prompts):
                try:
                    print(f"\n  [{prompt_index + 1}/{len(prompts)}] Scraping: {prompt[:60]}...")
                    
                    # Extract AI Overview data
                    extraction_result = extract_ai_overview_links(driver, prompt, max_links=10)
                    
                    # Format response similar to other LLMs
                    answer_text = extraction_result.get('answer_text', '')
                    links = extraction_result.get('links', [])
                    
                    # Build response text with citations
                    response_text = answer_text
                    if links:
                        response_text += "\n\nSources:\n"
                        for link in links[:5]:  # Top 5 citations
                            response_text += f"- {link['title']}: {link['url']}\n"
                    
                    all_responses.append({
                        "prompt_index": prompt_index,
                        "prompt": prompt,
                        "llm_name": "Google AI Overview",
                        "response": response_text or "[No AI Overview found]",
                        "citations": [link['url'] for link in links]
                    })
                    
                    print(f"  ✅ Google AI Overview extracted ({len(answer_text)} chars, {len(links)} links)")
                    
                    # Delay between requests
                    if prompt_index < len(prompts) - 1:
                        import time
                        import random
                        delay = random.uniform(3, 5)
                        print(f"  ⏳ Waiting {delay:.1f}s...")
                        time.sleep(delay)
                        
                except Exception as e:
                    print(f"  ❌ Error with Google AI Overview: {str(e)}")
                    all_responses.append({
                        "prompt_index": prompt_index,
                        "prompt": prompt,
                        "llm_name": "Google AI Overview",
                        "response": f"[Error] {str(e)}",
                        "error": True
                    })
            
            driver.quit()
            print("\n  ✓ Browser closed")
            
        except Exception as e:
            print(f"\n  ❌ Failed to initialize Google AI Overview: {str(e)}")
    
    # Separate LLMs into scraper-based and API-based
    other_llms = [llm for llm in normalized_llms if llm != "Google AI Overview"]
    
    # ✅ SCRAPER-BASED LLMs: Batch process via BrightData (Gemini, ChatGPT, Perplexity)
    scraper_llms = [llm for llm in other_llms if llm in ("Gemini", "ChatGPT", "Perplexity") and is_scraper_configured(llm)]
    # API-based LLMs: Process per-prompt (Claude, Mistral, and any unconfigured scraper LLMs)
    api_llms = [llm for llm in other_llms if llm not in scraper_llms]
    
    if scraper_llms:
        print(f"\n🌐 Scraper-based LLMs (BrightData): {scraper_llms}")
    if api_llms:
        print(f"📡 API-based LLMs: {api_llms}")
    
    # ── Step 1: Handle scraper-based LLMs (batch all prompts at once) ──
    for llm_name in scraper_llms:
        try:
            print(f"\n📊 Scraping {llm_name} for {len(prompts)} prompts via BrightData...")
            scraper_results = scrape_llm_responses(
                llm_name=llm_name,
                prompts=prompts
            )
            all_responses.extend(scraper_results)
            print(f"  ✅ {llm_name} scraping complete: {len(scraper_results)} responses")
        except Exception as e:
            print(f"  ❌ Error scraping {llm_name}: {str(e)}")
            # Add error entries for each prompt so downstream logic doesn't break
            for prompt_index, prompt in enumerate(prompts):
                all_responses.append({
                    "prompt_index": prompt_index,
                    "prompt": prompt,
                    "llm_name": llm_name,
                    "response": f"[Scraper Error] {str(e)}",
                    "citations": [],
                    "error": True
                })
    
    # ── Step 2: Handle API-based LLMs (per-prompt, same as before) ──
    if api_llms:
        # Try importing context manager for Paid.ai trace grouping
        try:
            from openinference.instrumentation import using_attributes
            attributes = {}
            if user_id:
                attributes["user.id"] = user_id
                attributes["session.user.id"] = user_id
                attributes["externalCustomerId"] = user_id
                attributes["externalProductId"] = "brand_visibility_analyzer"
                
        except ImportError:
            using_attributes = None

        import contextlib
        @contextlib.contextmanager
        def dynamic_context():
            if using_attributes and user_id:
                with using_attributes(**attributes):
                    yield
            else:
                yield

        with dynamic_context():
            for prompt_index, prompt in enumerate(prompts):
                for llm_name in api_llms:
                    try:
                        if llm_name == "Claude":
                            response = anthropic_client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=1000,
                                tools=[
                                    {
                                        "type": "web_search_20250305",
                                        "name": "web_search"
                                    }
                                ],
                                messages=[{"role": "user", "content": prompt}]
                            )

                            parts = []
                            citations_data = []

                            for block in response.content:
                                block_type = getattr(block, "type", None)

                                if block_type == "text":
                                    text = getattr(block, "text", None) or (block.get("text", "") if isinstance(block, dict) else "")
                                    parts.append(text)
                                    for citation in getattr(block, "citations", []) or []:
                                        url = getattr(citation, "url", "")
                                        if url:
                                            citations_data.append(url)

                                elif block_type == "tool_result":
                                    for item in getattr(block, "content", []) or []:
                                        if getattr(item, "type", None) == "web_search_result":
                                            url = getattr(item, "url", "")
                                            if url:
                                                citations_data.append(url)

                            response_text = "\n".join(parts).strip()

                            all_responses.append({
                                "prompt_index": prompt_index,
                                "prompt": prompt,
                                "llm_name": "Claude",
                                "response": response_text,
                                "citations": citations_data,  
                            })
                            print(f"  ✅ Claude executed")
                        
                        elif llm_name == "Mistral":
                            import time
                            from mistralai import Mistral
                        
                            api_key = os.environ.get("MISTRAL_API_KEY")
                            if not api_key:
                                raise ValueError("MISTRAL_API_KEY is missing")

                            mistral_client = Mistral(api_key=api_key)
                        
                            # ✅ ADDED: Retry logic for network stability
                            max_retries = 3
                            response_text = ""
                            
                            for attempt in range(max_retries):
                                try:
                                    message = mistral_client.chat.complete(
                                        model="mistral-small-latest",
                                        messages=[{"role": "user", "content": prompt}],
                                        max_tokens=1000
                                    )
                                    response_text = message.choices[0].message.content
                                    print(f"  ✅ Mistral executed")
                                    break # Success! Exit retry loop
                                
                                except Exception as e:
                                    if ("getaddrinfo" in str(e) or "11001" in str(e)) and attempt < max_retries - 1:
                                        wait_time = 2 * (attempt + 1)
                                        print(f"    ⚠️ Network glitch (attempt {attempt+1}/{max_retries}). Retrying in {wait_time}s...")
                                        time.sleep(wait_time)
                                    else:
                                        raise e 

                            all_responses.append({
                                "prompt_index": prompt_index,
                                "prompt": prompt,
                                "llm_name": "Mistral",
                                "response": response_text,
                            })
                        
                        else:
                            print(f"  ⚠️ Unknown LLM: {llm_name}")
                        
                    except Exception as e:
                        print(f"  ❌ Error with {llm_name}: {str(e)}")
                        all_responses.append({
                            "prompt_index": prompt_index,
                            "prompt": prompt,
                            "llm_name": llm_name,
                            "response": f"[Error] {str(e)}",
                            "error": True
                        })
    
    print(f"\n✅ Done! {len(all_responses)} responses\n")
    return all_responses