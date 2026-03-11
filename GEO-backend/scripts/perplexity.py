import requests
import time
import json

# 1. Configuration
API_TOKEN = "ab1ed412-b0a5-4ada-a0fc-0b31c1af2154" 
DATASET_ID = "gd_m7dhdot1vw9a7gc1n" # UPDATE THIS with your Perplexity Dataset ID
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def trigger_perplexity_audit(prompts):
    """Sends a set of prompts to the Perplexity scraper."""
    payload = [
        {
            "url": "https://www.perplexity.ai/", 
            "prompt": p, 
            "country": "in" # Localized for India
        } for p in prompts
    ]
    
    endpoint = f"https://api.brightdata.com/datasets/v3/trigger?dataset_id={DATASET_ID}&format=json"
    
    response = requests.post(endpoint, headers=HEADERS, json=payload)
    response.raise_for_status()
    
    snapshot_id = response.json().get("snapshot_id")
    print(f"✅ Perplexity Batch Triggered! Snapshot ID: {snapshot_id}")
    return snapshot_id

def download_results(snapshot_id):
    """Polls the status and downloads results."""
    progress_url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
    snapshot_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json"

    while True:
        status_res = requests.get(progress_url, headers=HEADERS).json()
        status = status_res.get("status")
        print(f"🕒 Perplexity Status: {status}...")

        if status == "ready":
            data_res = requests.get(snapshot_url, headers=HEADERS)
            return data_res.json()
        elif status == "failed":
            raise Exception("Perplexity scraping job failed.")
            
        time.sleep(20)

# --- RUNNING THE PERPLEXITY AUDIT ---
my_prompts = ["Top integrated marketing agencies in Delhi NCR 2026"]

try:
    s_id = trigger_perplexity_audit(my_prompts)
    results = download_results(s_id)

    for record in results:
        print(f"\nPrompt: {record.get('prompt')}")
        
        # Perplexity specific fields: answer_text and sources
        answer = record.get('answer_text', 'No answer found.')
        print(f"\nAI RESPONSE:\n{answer}\n")
        
        # Perplexity often uses the key 'sources' instead of 'citations'
        sources = record.get('sources') or record.get('citations') or []
        print(f"Sources Found: {len(sources)}")
        for src in sources:
            # Sources can be strings or dictionaries depending on the dataset version
            url = src.get('url') if isinstance(src, dict) else src
            print(f" - {url}")
            
except Exception as e:
    print(f"Error: {e}")