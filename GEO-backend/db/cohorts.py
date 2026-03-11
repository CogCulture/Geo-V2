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

def save_cohorts(session_id: str, cohorts: List[Dict]) -> List[int]:
    try:
        session_check = supabase.table('analysis_sessions').select('session_id').eq('session_id', session_id).execute()
        if not session_check.data:
            logger.error(f"❌ Session {session_id} does NOT exist in database. Cannot save cohorts!")
            raise Exception(f"Session {session_id} must be saved to database before creating cohorts")
        
        timestamp = datetime.now().isoformat()
        cohort_ids = []
        
        for idx, cohort in enumerate(cohorts):
            data = {
                'session_id': session_id,
                'cohort_name': cohort['name'],
                'cohort_description': cohort.get('description', ''),
                'prompt_count': cohort.get('prompt_count', 3),
                'cohort_order': idx,
                'timestamp': timestamp
            }
            
            response = supabase.table('cohorts').insert(data).execute()
            if response.data:
                cohort_ids.append(response.data[0]['id'])
        
        logger.info(f"✅ Saved {len(cohorts)} cohorts for session {session_id}")
        return cohort_ids
        
    except Exception as e:
        logger.error(f"Error saving cohorts: {str(e)}")
        logger.error(f"  Session ID: {session_id}")
        logger.error(f"  Cohort count: {len(cohorts) if cohorts else 0}")
        raise


def save_prompts_with_cohorts(session_id: str, cohort_prompts: List[Dict]):
    try:
        timestamp = datetime.now().isoformat()
        
        all_data = []
        prompt_index = 0
        
        for cohort_data in cohort_prompts:
            cohort_id = cohort_data['cohort_id']
            prompts = cohort_data['prompts']
            
            for prompt_text in prompts:
                all_data.append({
                    'session_id': session_id,
                    'cohort_id': cohort_id,
                    'prompt_text': prompt_text,
                    'prompt_index': prompt_index,
                    'selected': False,
                    'timestamp': timestamp
                })
                prompt_index += 1
        
        if all_data:
            supabase.table('prompts_cohort_mapping').insert(all_data).execute()
        
        logger.info(f"✅ Saved {prompt_index} prompts with cohort mappings for session {session_id}")
        
    except Exception as e:
        logger.error(f"Error saving prompts with cohorts: {str(e)}")
        raise

def get_cohorts_for_session(session_id: str) -> List[Dict]:
    try:
        # Get cohorts
        cohorts_response = supabase.table('cohorts').select('*').eq('session_id', session_id).order('cohort_order').execute()
        
        logger.info(f"📊 Retrieved {len(cohorts_response.data)} cohorts for session {session_id}")
        
        if not cohorts_response.data:
            logger.warning(f"⚠️ No cohorts found for session {session_id}")
            return []
        
        # Optimize: Fetch ALL prompts for this session in one go to avoid N+1 requests
        # This prevents "COMPRESSION_ERROR" and connection termination issues
        all_prompts_response = supabase.table('prompts_cohort_mapping').select(
            'cohort_id, prompt_text, prompt_index, selected'
        ).eq('session_id', session_id).order('prompt_index').execute()
        
        all_prompts = all_prompts_response.data or []
        
        # Group prompts by cohort_id
        prompts_by_cohort = {}
        for p in all_prompts:
            cid = p['cohort_id']
            if cid not in prompts_by_cohort:
                prompts_by_cohort[cid] = []
            prompts_by_cohort[cid].append(p)
            
        logger.info(f"✅ Retrieved {len(all_prompts)} total prompts for session")
        
        cohorts = []
        for cohort_row in cohorts_response.data:
            cohort_id = cohort_row['id']
            
            # Get prompts from memory
            prompts = prompts_by_cohort.get(cohort_id, [])
             
            # Ensure prompts are properly formatted for frontend
            formatted_prompts = []
            for prompt in prompts:
                formatted_prompts.append({
                    'prompt_text': prompt.get('prompt_text', ''),
                    'category': None  # Add category if needed
                })
            
            cohorts.append({
                'id': cohort_id,
                'name': cohort_row['cohort_name'],
                'description': cohort_row['cohort_description'],
                'prompt_count': len(formatted_prompts),
                'prompts': formatted_prompts
            })
        
        logger.info(f"✅ Successfully retrieved {len(cohorts)} cohorts with prompts")
        return cohorts
        
    except Exception as e:
        logger.error(f"❌ Error retrieving cohorts: {str(e)}")
        logger.error(f"   Stack trace: {traceback.format_exc()}")
        return []

def update_prompt_selection(session_id: str, prompt_indices: List[int], selected: bool = True):
    try:
        supabase.table('prompts_cohort_mapping').update({
            'selected': selected
        }).eq('session_id', session_id).in_('prompt_index', prompt_indices).execute()
        
        logger.info(f"✅ Updated selection for {len(prompt_indices)} prompts")
        
    except Exception as e:
        logger.error(f"Error updating prompt selection: {str(e)}")
        raise

def save_custom_cohort(session_id: str, cohort_name: str, cohort_description: str, cohort_order: int) -> int:
    try:
        timestamp = datetime.now().isoformat()
        
        data = {
            'session_id': session_id,
            'cohort_name': cohort_name,
            'cohort_description': cohort_description,
            'prompt_count': 5,
            'cohort_order': cohort_order,
            'timestamp': timestamp
        }
        
        response = supabase.table('cohorts').insert(data).execute()
        
        if response.data:
            cohort_id = response.data[0]['id']
            logger.info(f"✅ Saved custom cohort: {cohort_name} (ID: {cohort_id})")
            return cohort_id
        return -1
        
    except Exception as e:
        logger.error(f"Error saving custom cohort: {str(e)}")
        return -1

def save_custom_prompts(session_id: str, cohort_id: int, prompts: List[str], start_index: int = 0):
    try:
        timestamp = datetime.now().isoformat()
        
        data = [
            {
                'session_id': session_id,
                'cohort_id': cohort_id,
                'prompt_text': prompt_text,
                'prompt_index': start_index + idx,
                'selected': True,
                'timestamp': timestamp
            }
            for idx, prompt_text in enumerate(prompts)
        ]
        
        supabase.table('prompts_cohort_mapping').insert(data).execute()
        logger.info(f"✅ Saved {len(prompts)} custom prompts for cohort {cohort_id}")
        
    except Exception as e:
        logger.error(f"Error saving custom prompts: {str(e)}")
        raise

def get_prompt_count_for_cohort(session_id: str, cohort_id: int) -> int:
    try:
        response = supabase.table('prompts_cohort_mapping').select(
            'id', count='exact'
        ).eq('session_id', session_id).eq('cohort_id', cohort_id).eq('selected', True).execute()
        
        return response.count if response.count else 0
        
    except Exception as e:
        logger.error(f"Error getting prompt count: {str(e)}")
        return 0

def update_cohort_selection(session_id: str, cohort_id: int, selected: bool):
    try:
        if not selected:
            supabase.table('prompts_cohort_mapping').update({
                'selected': False
            }).eq('session_id', session_id).eq('cohort_id', cohort_id).execute()
        
        logger.info(f"Updated cohort {cohort_id} selection: {selected}")
        
    except Exception as e:
        logger.error(f"Error updating cohort selection: {str(e)}")
        raise

def get_selected_cohort_count(session_id: str) -> int:
    try:
        response = supabase.table('prompts_cohort_mapping').select(
            'cohort_id'
        ).eq('session_id', session_id).eq('selected', True).execute()
        
        unique_cohorts = set(row['cohort_id'] for row in response.data)
        return len(unique_cohorts)
        
    except Exception as e:
        logger.error(f"Error getting selected cohort count: {str(e)}")
        return 0

def get_selected_prompts(session_id: str) -> List[str]:
    try:
        response = supabase.table('prompts_cohort_mapping').select(
            'prompt_text'
        ).eq('session_id', session_id).eq('selected', True).order('prompt_index').execute()
        
        return [row['prompt_text'] for row in response.data]
        
    except Exception as e:
        logger.error(f"Error retrieving selected prompts: {str(e)}")
        return []
