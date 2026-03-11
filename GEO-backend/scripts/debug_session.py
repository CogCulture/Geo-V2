#!/usr/bin/env python3
"""Debug script to check session and results"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import sys

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL or SUPABASE_KEY not set")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get most recent session
print("\n📋 Fetching most recent session...")
response = supabase.table('analysis_sessions').select('*').order('timestamp', desc=True).limit(1).execute()

if response.data:
    session = response.data[0]
    session_id = session['session_id']
    print(f"✅ Found session: {session_id}")
    print(f"   Brand: {session.get('brand_name')}")
    print(f"   User: {session.get('user_id')}")
    print(f"   Status: {session.get('status')}")
    print(f"   Progress: {session.get('progress')}")
    print(f"   Current Step: {session.get('current_step')}")
    
    # Check for responses
    print(f"\n📝 Checking for LLM responses...")
    responses = supabase.table('llm_responses').select('*').eq('session_id', session_id).execute()
    print(f"   Found {len(responses.data)} LLM responses")
    
    # Check for scores
    print(f"\n📊 Checking for scoring results...")
    scores = supabase.table('scoring_results').select('*').eq('session_id', session_id).execute()
    print(f"   Found {len(scores.data)} scoring results")
    
    # Check for cohorts
    print(f"\n🎯 Checking for cohorts...")
    cohorts = supabase.table('cohorts').select('*').eq('session_id', session_id).execute()
    print(f"   Found {len(cohorts.data)} cohorts")
    
    # Check for prompts
    print(f"\n❓ Checking for prompts...")
    prompts = supabase.table('prompts').select('*').eq('session_id', session_id).execute()
    print(f"   Found {len(prompts.data)} prompts")
    
    # Check for competitors
    print(f"\n🏆 Checking for competitors...")
    competitors = supabase.table('competitors').select('*').eq('session_id', session_id).execute()
    print(f"   Found {len(competitors.data)} competitors")
    
    # Check for share of voice
    print(f"\n📈 Checking for share of voice...")
    sov = supabase.table('share_of_voice').select('*').eq('session_id', session_id).execute()
    print(f"   Found {len(sov.data)} share of voice entries")
    
else:
    print("❌ No sessions found")
