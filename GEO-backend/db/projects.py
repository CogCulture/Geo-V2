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



# --- PROJECT MANAGEMENT ---

def create_project(user_id: str, name: str, website_url: Optional[str] = None, 
                   industry: Optional[str] = None, update_frequency: str = '24h') -> Optional[Dict[str, Any]]:
   
    try:
        data = {
            'user_id': user_id,
            'name': name,
            'website_url': website_url,
            'industry': industry,
            'update_frequency': update_frequency,
            'is_active': True,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        response = supabase.table('projects').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        return None

def get_user_projects(user_id: str) -> List[Dict[str, Any]]:
    
    try:
        response = supabase.table('projects').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error retrieving user projects: {str(e)}")
        return []

def get_project_by_id(project_id: str) -> Optional[Dict[str, Any]]:
   
    try:
        response = supabase.table('projects').select('*').eq('id', project_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error retrieving project {project_id}: {str(e)}")
        return None

def update_project(project_id: str, update_data: Dict[str, Any]) -> bool:
    
    try:
        update_data['updated_at'] = datetime.now().isoformat()
        supabase.table('projects').update(update_data).eq('id', project_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {str(e)}")
        return False

def delete_project(project_id: str) -> bool:
    
    try:
        logger.info(f"🗑️ Attempting to delete project {project_id} and all its data")
        
        # 1. Get all session IDs associated with this project
        sessions_res = supabase.table('analysis_sessions').select('session_id').eq('project_id', project_id).execute()
        session_ids = [s['session_id'] for s in (sessions_res.data or [])]
        
        if session_ids:
            logger.info(f"  Found {len(session_ids)} sessions to delete")
            
            # 2. Delete all related data for these sessions
            # We must be thorough because foreign keys might not cascade if not set up that way
            try:
                supabase.table('llm_responses').delete().in_('session_id', session_ids).execute()
                supabase.table('scoring_results').delete().in_('session_id', session_ids).execute()
                supabase.table('competitors').delete().in_('session_id', session_ids).execute()
                supabase.table('share_of_voice').delete().in_('session_id', session_ids).execute()
                supabase.table('prompts_cohort_mapping').delete().in_('session_id', session_ids).execute()
                supabase.table('cohorts').delete().in_('session_id', session_ids).execute()
                # saved_prompts are not linked to session_id, but prompt mappings are.
            except Exception as e:
                logger.warning(f"  Partial failure clearing session children (might be handled by cascade): {e}")

            # 3. Delete the sessions themselves
            supabase.table('analysis_sessions').delete().in_('session_id', session_ids).execute()
            logger.info("  Sessions deleted")
            
        # 4. Delete the project
        # This should cascade to monitored_prompts, monitored_competitors, daily_brand_metrics
        supabase.table('projects').delete().eq('id', project_id).execute()
        
        logger.info(f"✅ Project {project_id} deleted successfully")
        return True
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {str(e)}")
        return False

# --- MONITORED ENTITIES MANAGEMENT ---

def add_monitored_prompts(project_id: str, prompts: List[str]) -> bool:
    
    try:
        data = [
            {'project_id': project_id, 'prompt_text': prompt, 'is_active': True}
            for prompt in prompts
        ]
        supabase.table('monitored_prompts').insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"Error adding monitored prompts: {str(e)}")
        return False

def get_monitored_prompts(project_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
   
    try:
        query = supabase.table('monitored_prompts').select('*').eq('project_id', project_id)
        if active_only:
            query = query.eq('is_active', True)
        response = query.order('created_at', desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error retrieving monitored prompts: {str(e)}")
        return []

def add_monitored_competitors(project_id: str, competitor_names: List[str]) -> bool:
    
    try:
        data = [
            {'project_id': project_id, 'name': name}
            for name in competitor_names
        ]
        supabase.table('monitored_competitors').insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"Error adding monitored competitors: {str(e)}")
        return False

def get_monitored_competitors(project_id: str) -> List[Dict[str, Any]]:
    
    try:
        response = supabase.table('monitored_competitors').select('*').eq('project_id', project_id).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error retrieving monitored competitors: {str(e)}")
        return []

# --- HISTORICAL AGGREGATED METRICS ---

def get_project_dashboard_metrics(project_id: str, days: int = 30) -> List[Dict[str, Any]]:
    try:
        start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
        response = supabase.table('daily_brand_metrics')\
            .select('*')\
            .eq('project_id', project_id)\
            .gte('date', start_date)\
            .order('date')\
            .execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {str(e)}")
        return []

