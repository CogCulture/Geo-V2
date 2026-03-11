import os
import requests
import time
import logging
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# ─── BrightData Configuration ───
BRIGHTDATA_API_TOKEN = os.environ.get("BRIGHTDATA_API_TOKEN", "")

# Dataset IDs for each LLM scraper (configurable via .env)
BRIGHTDATA_CHATGPT_DATASET_ID = os.environ.get("BRIGHTDATA_CHATGPT_DATASET_ID", "")
BRIGHTDATA_GEMINI_DATASET_ID = os.environ.get("BRIGHTDATA_GEMINI_DATASET_ID", "")
BRIGHTDATA_PERPLEXITY_DATASET_ID = os.environ.get("BRIGHTDATA_PERPLEXITY_DATASET_ID", "")

# LLM URL and dataset mapping
LLM_SCRAPER_CONFIG = {
    "ChatGPT": {
        "url": "https://chatgpt.com/",
        "dataset_id_env": "BRIGHTDATA_CHATGPT_DATASET_ID",
    },
    "Gemini": {
        "url": "https://gemini.google.com/",
        "dataset_id_env": "BRIGHTDATA_GEMINI_DATASET_ID",
    },
    "Perplexity": {
        "url": "https://www.perplexity.ai/",
        "dataset_id_env": "BRIGHTDATA_PERPLEXITY_DATASET_ID",
    },
}

HEADERS = {
    "Authorization": f"Bearer {BRIGHTDATA_API_TOKEN}",
    "Content-Type": "application/json"
}

# ─── Polling configuration ───
POLL_INTERVAL_SECONDS = 20
MAX_POLL_ATTEMPTS = 90  # 20s * 90 = 30 minutes max wait


def _get_dataset_id(llm_name: str) -> str:
    """Resolve the BrightData dataset ID for a given LLM."""
    config = LLM_SCRAPER_CONFIG.get(llm_name)
    if not config:
        raise ValueError(f"No BrightData scraper config found for LLM: {llm_name}")

    dataset_id = os.environ.get(config["dataset_id_env"], "")
    if not dataset_id:
        raise ValueError(
            f"BrightData dataset ID not configured for {llm_name}. "
            f"Set {config['dataset_id_env']} in .env"
        )
    return dataset_id

def _get_target_url(llm_name: str) -> str:
    """Get the target website URL for a given LLM."""
    config = LLM_SCRAPER_CONFIG.get(llm_name)
    if not config:
        raise ValueError(f"No BrightData scraper config found for LLM: {llm_name}")
    return config["url"]

def _trigger_scrape(llm_name: str, prompts: List[str], country: str = "in") -> str:
    """
    Trigger a BrightData scraping job for the given LLM and prompts.
    Returns the snapshot_id for polling.
    """
    if not BRIGHTDATA_API_TOKEN:
        raise ValueError("BRIGHTDATA_API_TOKEN is not set in .env")

    dataset_id = _get_dataset_id(llm_name)
    target_url = _get_target_url(llm_name)

    payload = [
        {
            "url": target_url,
            "prompt": p,
            "country": country
        }
        for p in prompts
    ]

    endpoint = f"https://api.brightdata.com/datasets/v3/trigger?dataset_id={dataset_id}&format=json"

    logger.info(f"  🌐 Triggering BrightData scrape for {llm_name} ({len(prompts)} prompts)...")

    response = requests.post(endpoint, headers=HEADERS, json=payload, timeout=60)
    response.raise_for_status()

    snapshot_id = response.json().get("snapshot_id")
    if not snapshot_id:
        raise Exception(f"BrightData did not return a snapshot_id for {llm_name}")

    logger.info(f"  ✅ {llm_name} batch triggered! Snapshot ID: {snapshot_id}")
    return snapshot_id

def _poll_and_download(snapshot_id: str, llm_name: str) -> List[Dict]:
    """
    Poll BrightData for scraping job completion and download results.
    Returns the raw JSON results list.
    """
    progress_url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
    snapshot_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json"

    for attempt in range(MAX_POLL_ATTEMPTS):
        try:
            status_res = requests.get(progress_url, headers=HEADERS, timeout=30).json()
            status = status_res.get("status")
            logger.info(f"  🕒 {llm_name} scraping status: {status} (poll {attempt + 1})...")

            if status == "ready":
                data_res = requests.get(snapshot_url, headers=HEADERS, timeout=120)
                data_res.raise_for_status()
                results = data_res.json()
                logger.info(f"  ✅ {llm_name} scraping complete! Got {len(results)} results.")
                return results

            elif status == "failed":
                raise Exception(f"{llm_name} BrightData scraping job failed (snapshot: {snapshot_id})")

        except requests.exceptions.RequestException as e:
            logger.warning(f"  ⚠️ Network error while polling {llm_name}: {str(e)}")

        time.sleep(POLL_INTERVAL_SECONDS)

    raise Exception(f"{llm_name} BrightData scraping timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s")

def _extract_citations_from_record(record: Dict, llm_name: str) -> List[str]:
    """
    Extract citation URLs from a BrightData scraper result record.
    Handles different response formats across LLMs.
    """
    citations = []

    # ChatGPT uses 'citations' key with list of dicts containing 'url'
    # Perplexity/Gemini may use 'sources' or 'citations', and items can be dicts or strings
    raw_citations = record.get('citations') or record.get('sources') or []

    for item in raw_citations:
        if isinstance(item, dict):
            url = item.get('url', '')
            if url:
                citations.append(url)
        elif isinstance(item, str) and item.strip():
            citations.append(item.strip())

    return citations

def scrape_llm_responses(
    llm_name: str,
    prompts: List[str],
    country: str = "in"
) -> List[Dict[str, Any]]:
    """
    Main entry point: Scrape responses from an LLM via BrightData.

    Returns a list of dicts in the SAME FORMAT as the existing API-based logic:
    [
        {
            "prompt_index": int,
            "prompt": str,
            "llm_name": str,
            "response": str,
            "citations": List[str]
        },
        ...
    ]
    """
    if llm_name not in LLM_SCRAPER_CONFIG:
        raise ValueError(f"Unsupported LLM for scraping: {llm_name}")

    # Step 1: Trigger the batch scrape
    snapshot_id = _trigger_scrape(llm_name, prompts, country)

    # Step 2: Poll and download results
    raw_results = _poll_and_download(snapshot_id, llm_name)

    # Step 3: Map results back to prompts and format consistently
    formatted_responses = []

    # BrightData returns results in the same order as the input prompts
    for idx, record in enumerate(raw_results):
        answer_text = record.get('answer_text', '') or record.get('content', '') or ''
        citations = _extract_citations_from_record(record, llm_name)

        # Use the prompt from the record if available, fallback to input prompt
        prompt_text = record.get('prompt', prompts[idx] if idx < len(prompts) else '')

        # Find the matching prompt_index from input prompts
        prompt_index = idx  # Default to position-based index
        if prompt_text and prompt_text in prompts:
            prompt_index = prompts.index(prompt_text)

        formatted_responses.append({
            "prompt_index": prompt_index,
            "prompt": prompt_text,
            "llm_name": llm_name,
            "response": answer_text if answer_text else "[No response from scraper]",
            "citations": citations,
        })

    logger.info(f"  ✅ {llm_name} scraping complete: {len(formatted_responses)} responses formatted")
    return formatted_responses

def is_scraper_configured(llm_name: str) -> bool:
    """Check if BrightData scraping is configured for a given LLM."""
    if not BRIGHTDATA_API_TOKEN:
        return False
    if llm_name not in LLM_SCRAPER_CONFIG:
        return False
    try:
        _get_dataset_id(llm_name)
        return True
    except ValueError:
        return False
