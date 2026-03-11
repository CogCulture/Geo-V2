import os
import json
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from urllib.parse import urlparse
from collections import Counter
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

from db.client import supabase

def update_session_status(session_id: str, status: str = None, progress: int = None, step: str = None, error: str = None):
    """
    Updates the progress/status of a session in the DB.
    Replaces the global dictionary in app.py.
    """
    try:
        update_data = {}
        if status: update_data['status'] = status
        if progress is not None: update_data['progress'] = progress
        if step: update_data['current_step'] = step
        if error: update_data['error_message'] = error
        
        if update_data:
            # Check if session exists first to avoid errors
            supabase.table('analysis_sessions').update(update_data).eq('session_id', session_id).execute()
    except Exception as e:
        logger.error(f"Failed to update session status: {e}")

def get_session_status(session_id: str) -> Dict[str, Any]:
    """Retrieves status from DB."""
    try:
        response = supabase.table('analysis_sessions').select('status, progress, current_step, error_message').eq('session_id', session_id).execute()
        if response.data:
            return response.data[0]
        return {"status": "not_found", "progress": 0}
    except Exception as e:
        logger.error(f"Failed to get session status: {e}")
        return {"status": "error", "progress": 0}

def get_session_metadata(session_id: str) -> Optional[Dict[str, Any]]:
    """Helper to get just the session metadata for copying/forking."""
    try:
        response = supabase.table('analysis_sessions').select('*').eq('session_id', session_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching session metadata: {e}")
        return None
def create_session_id(brand_name: str, product_name: Optional[str] = None) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if product_name:
        return f"{brand_name.replace(' ', '_')}_{product_name.replace(' ', '_')}_{timestamp}"
    return f"{brand_name.replace(' ', '_')}_{timestamp}"

def create_prompt_id(session_id: str, prompt_index: int) -> str:
    return f"{session_id}_prompt_{prompt_index}"
def save_session(session_id: str, brand_name: str, user_id: str, product_name: Optional[str] = None, 
                 website_url: Optional[str] = None, research_data: Optional[Dict] = None,
                 keywords: Optional[List[str]] = None, industry: Optional[str] = None,
                 project_id: Optional[str] = None, brand_aliases: Optional[List[str]] = None):
    
    try:
        logger.info(f"💾 Saving session {session_id} for brand {brand_name}. Project ID: {project_id}")
        timestamp = datetime.now().isoformat()
        
        data = {
            'session_id': session_id,
            'user_id': user_id,
            'brand_name': brand_name,
            'product_name': product_name,
            'industry': industry,
            'website_url': website_url,
            'timestamp': timestamp,
            'research_data': research_data,
            'keywords': keywords,
            'brand_aliases': brand_aliases,
            # 'project_id': project_id  <-- REMOVED from here
            # Note: We do NOT set 'status' here to avoid overwriting "running" status with "pending"
        }
        
        # Only update project_id if explicitly provided, to avoid overwriting with None
        if project_id is not None:
            data['project_id'] = project_id
        
        # ✅ FIX: Use upsert instead of insert to prevent "duplicate key" errors
        supabase.table('analysis_sessions').upsert(data).execute()
        logger.info(f"✅ Saved/Updated session: {session_id}")
    except Exception as e:
        logger.error(f"Error saving session: {str(e)}")
        raise
def get_user_sessions(user_id: str) -> List[Dict[str, Any]]:
    try:
        response = supabase.table('analysis_sessions').select('*').eq('user_id', user_id).order('timestamp', desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error retrieving user sessions: {str(e)}")
        return []
def duplicate_session_cohorts(parent_session_id: str, new_session_id: str):
 
    try:
        # 1. Get all cohorts from the parent session
        parent_cohorts = supabase.table('cohorts').select('*').eq('session_id', parent_session_id).execute()
        
        if not parent_cohorts.data:
            logger.warning(f"No cohorts found to duplicate for session {parent_session_id}")
            return

        # 2. Iterate and copy each cohort
        for old_cohort in parent_cohorts.data:
            cohort_data = {
                'session_id': new_session_id,
                'cohort_name': old_cohort['cohort_name'],
                'cohort_description': old_cohort.get('cohort_description'),
                'prompt_count': old_cohort.get('prompt_count'),
                'cohort_order': old_cohort.get('cohort_order'),
                'timestamp': datetime.now().isoformat()
            }
            
            # Insert new cohort and get its ID
            new_cohort_res = supabase.table('cohorts').insert(cohort_data).execute()
            
            if new_cohort_res.data:
                new_cohort_id = new_cohort_res.data[0]['id']
                old_cohort_id = old_cohort['id']
                
                # 3. Get all prompts for this cohort
                old_prompts = supabase.table('prompts_cohort_mapping')\
                    .select('*').eq('cohort_id', old_cohort_id).execute()
                
                if old_prompts.data:
                    new_prompts_data = []
                    for prompt in old_prompts.data:
                        new_prompts_data.append({
                            'session_id': new_session_id,
                            'cohort_id': new_cohort_id,
                            'prompt_text': prompt['prompt_text'],
                            'prompt_index': prompt['prompt_index'],
                            'selected': False,
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    # Bulk insert prompts
                    if new_prompts_data:
                        supabase.table('prompts_cohort_mapping').insert(new_prompts_data).execute()
        
        logger.info(f"Successfully duplicated cohorts from {parent_session_id} to {new_session_id}")

    except Exception as e:
        logger.error(f"Error duplicating cohorts: {str(e)}")

def duplicate_session_competitors(parent_session_id: str, new_session_id: str):
    """Copies competitors from one session to another to ensure they are carried forward."""
    try:
        # Get competitors from parent
        response = supabase.table('competitors').select('competitor_name, rank').eq('session_id', parent_session_id).order('rank').execute()
        
        if response.data:
            new_data = [
                {
                    'session_id': new_session_id,
                    'competitor_name': row['competitor_name'],
                    'rank': row['rank']
                }
                for row in response.data
            ]
            supabase.table('competitors').insert(new_data).execute()
            logger.info(f"✅ Duplicated {len(new_data)} competitors from {parent_session_id} to {new_session_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Error duplicating competitors: {str(e)}")
        return False
def get_all_sessions() -> List[Dict[str, Any]]:
    try:
        response = supabase.table('analysis_sessions').select(
            'session_id, brand_name, product_name, timestamp'
        ).order('timestamp', desc=True).execute()
        
        return response.data
    except Exception as e:
        logger.error(f"Error getting all sessions: {str(e)}")
        return []
def get_recent_sessions(limit=10):
    try:
        response = supabase.table('analysis_sessions').select(
            'session_id, brand_name, timestamp, product_name, website_url'
        ).order('timestamp', desc=True).limit(limit).execute()
        
        return response.data
    except Exception as e:
        logger.error(f"Error getting recent sessions: {str(e)}")
        return []
def get_all_unique_brands():
    try:
        response = supabase.table('analysis_sessions').select('brand_name').execute()
        brands = list(set(row['brand_name'] for row in response.data))
        return sorted(brands)
    except Exception as e:
        logger.error(f"Error getting unique brands: {str(e)}")
        return []
def get_recent_sessions_by_brand(brand_name: str, limit: int = 20):
    try:
        response = supabase.table('analysis_sessions').select(
            'session_id, brand_name, product_name, website_url, timestamp'
        ).eq('brand_name', brand_name).order('timestamp', desc=True).limit(limit).execute()
        
        return response.data
    except Exception as e:
        logger.error(f"Error getting recent sessions by brand: {str(e)}")
        return []
def replace_session_competitors(session_id: str, competitors: list):
    """Deletes existing competitors for a session and adds new ones."""
    try:
        supabase.table('competitors').delete().eq('session_id', session_id).execute()
        if competitors:
            data = [{'session_id': session_id, 'competitor_name': c, 'rank': i+1} for i, c in enumerate(competitors)]
            supabase.table('competitors').insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"Error replacing competitors: {str(e)}")
        raise

def clear_session_metrics(session_id: str):
    """Clears scoring results to prepare for re-calculation."""
    try:
        supabase.table('scoring_results').delete().eq('session_id', session_id).execute()
        supabase.table('share_of_voice').delete().eq('session_id', session_id).execute()
    except Exception as e:
        logger.error(f"Error clearing metrics: {str(e)}")
        raise
