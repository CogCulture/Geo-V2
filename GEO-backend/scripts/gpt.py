import requests
import time
import json

# 1. Configuration
API_TOKEN = "ab1ed412-b0a5-4ada-a0fc-0b31c1af2154" # Found in Account Settings -> API Keys
DATASET_ID = "gd_m7aof0k82r803d5bjm" # The ID for the ChatGPT Search Scraper
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def trigger_geo_audit(prompts):
    """Sends a set of prompts to the ChatGPT scraper."""
    # Build the payload for each prompt
    payload = [
        {
            "url": "https://chatgpt.com/", 
            "prompt": p, 
            "country": "in" # Ensure results are US-localized for your audit
        } for p in prompts
    ]
    
    endpoint = f"https://api.brightdata.com/datasets/v3/trigger?dataset_id={DATASET_ID}&format=json"
    
    response = requests.post(endpoint, headers=HEADERS, json=payload)
    response.raise_for_status()
    
    snapshot_id = response.json().get("snapshot_id")
    print(f"✅ Batch Triggered! Snapshot ID: {snapshot_id}")
    return snapshot_id

def download_results(snapshot_id):
    """Polls the status and downloads results once ready."""
    progress_url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
    snapshot_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json"

    while True:
        status_res = requests.get(progress_url, headers=HEADERS).json()
        status = status_res.get("status")
        print(f"🕒 Current Status: {status}...")

        if status == "ready":
            # Download final data
            data_res = requests.get(snapshot_url, headers=HEADERS)
            return data_res.json()
        elif status == "failed":
            raise Exception("Scraping job failed.")
            
        time.sleep(20) # Wait 20 seconds between checks

# --- RUNNING THE AUDIT ---
my_prompts = [
    "Top integrated marketing agencies in Delhi NCR 2026"
]

try:
    s_id = trigger_geo_audit(my_prompts)
    results = download_results(s_id)

    
    
    # Process results for GEO insights
    for record in results:
        print(f"\nPrompt: {record['prompt']}")


        # Using .get() ensures your script won't crash if a field is missing
        answer = record.get('answer_text', 'No text answer found.')
        print(f"\nAI RESPONSE:\n{answer}\n")

        print(f"Citations Found: {len(record.get('citations', []))}")
        for cite in record.get('citations', []):
            print(f" - {cite['url']}")
            
except Exception as e:
    print(f"Error: {e}")