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

def get_detailed_citation_analytics(session_id: str) -> Dict[str, Any]:
    try:
        # Get LLM responses - Optimizing columns to avoid PROTOCOL_ERROR
        llm_response = supabase.table('llm_responses').select(
            'llm_name, prompt_text, timestamp, citations'
        ).eq('session_id', session_id).execute()
        llm_rows = llm_response.data
        
        if not llm_rows:
            return {'citations': []}
            
        domain_stats = {}
        total_session_citations = 0
        
        for row in llm_rows:
            llm_name = row.get('llm_name', 'Unknown')
            prompt_text = row.get('prompt_text', '')
            timestamp = row.get('timestamp', '')
            citations = row.get('citations', []) or []
            
            for url in citations:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc or parsed.path
                    domain = domain.replace('www.', '')
                    
                    if not domain:
                        continue
                        
                    if domain not in domain_stats:
                        domain_stats[domain] = {
                            'domain': domain,
                            'total_citations': 0,
                            'urls': [], # List of distinct URL objects
                            'llms': set(),
                            'competitors': [], # Placeholder for now
                            'first_seen': timestamp
                        }
                    
                    stats = domain_stats[domain]
                    stats['total_citations'] += 1
                    total_session_citations += 1
                    stats['llms'].add(llm_name)
                    
                    # Add URL details if unique
                    existing_url = next((u for u in stats['urls'] if u['url'] == url), None)
                    if not existing_url:
                        stats['urls'].append({
                            'url': url,
                            'prompt': prompt_text,
                            'llm': llm_name,
                            'date': timestamp
                        })
                    else:
                        # If existing but from different prompt/llm, maybe just track it? 
                        # For now, unique URLs are key.
                        pass
                        
                except Exception as e:
                    continue
        
        # Format for frontend
        results = []
        for domain, stats in domain_stats.items():
            percentage = (stats['total_citations'] / total_session_citations * 100) if total_session_citations > 0 else 0
            results.append({
                'domain': domain,
                'count': stats['total_citations'],
                'percentage': round(percentage, 1),
                'urls': stats['urls'],
                'llms': list(stats['llms']),
                'competitors': [], 
                'type': 'Other',
                'date': stats['first_seen'] # Rough approx
            })
            
        # Sort by count desc
        results.sort(key=lambda x: x['count'], reverse=True)
        
        return {'citations': results, 'total_citations': total_session_citations}

    except Exception as e:
        logger.error(f"Error getting citation analytics:{e}")
        return {'citations': [], 'total_citations': 0}

def get_brand_citation_repository(brand_name: str, user_id: str) -> Dict[str, Any]:
    """
    Aggregates citations from all analysis sessions for a specific brand and user.
    Creates a 'repository' view with frequency tracking.
    """
    try:
        # 1. Get all session IDs for this brand and user
        sessions_response = supabase.table('analysis_sessions').select('session_id').eq('brand_name', brand_name).eq('user_id', user_id).execute()
        session_ids = [s['session_id'] for s in (sessions_response.data or [])]
        
        if not session_ids:
            return {'citations': [], 'total_citations': 0}
            
        # 2. Fetch LLM responses for all these sessions in batch - Optimizing columns
        llm_response = supabase.table('llm_responses').select(
            'llm_name, prompt_text, timestamp, citations'
        ).in_('session_id', session_ids).execute()
        llm_rows = llm_response.data
        
        if not llm_rows:
            return {'citations': []}
            
        domain_stats = {}
        total_brand_citations = 0
        
        for row in llm_rows:
            llm_name = row.get('llm_name', 'Unknown')
            prompt_text = row.get('prompt_text', '')
            timestamp = row.get('timestamp', '')
            citations = row.get('citations', []) or []
            
            for url in citations:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc or parsed.path
                    domain = domain.replace('www.', '')
                    
                    if not domain:
                        continue
                        
                    if domain not in domain_stats:
                        domain_stats[domain] = {
                            'domain': domain,
                            'total_citations': 0,
                            'urls': [], # List of distinct URL objects
                            'llms': set(),
                            'competitors': set(),
                            'first_seen': timestamp
                        }
                    
                    stats = domain_stats[domain]
                    stats['total_citations'] += 1
                    total_brand_citations += 1
                    stats['llms'].add(llm_name)
                    
                    # Add URL details if unique
                    existing_url = next((u for u in stats['urls'] if u['url'] == url), None)
                    if not existing_url:
                        stats['urls'].append({
                            'url': url,
                            'prompt': prompt_text,
                            'llm': llm_name,
                            'date': timestamp
                        })
                    else:
                        # If existing, we could potentially update metadata or count frequency per URL
                        # For now, we follow the session-specific logic but across all sessions
                        pass
                        
                except Exception as e:
                    continue
        
        # Format for frontend
        results = []
        for domain, stats in domain_stats.items():
            percentage = (stats['total_citations'] / total_brand_citations * 100) if total_brand_citations > 0 else 0
            results.append({
                'domain': domain,
                'count': stats['total_citations'],
                'percentage': round(percentage, 1),
                'urls': stats['urls'],
                'llms': list(stats['llms']),
                'competitors': list(stats['competitors']), 
                'type': 'Other', # Could be refined by domain lookups if needed
                'date': stats['first_seen']
            })
            
        # Sort by count desc
        results.sort(key=lambda x: x['count'], reverse=True)
        
        logger.info(f"✅ Aggregated {total_brand_citations} citations for brand '{brand_name}' spanning {len(session_ids)} sessions")
        return {'citations': results, 'total_citations': total_brand_citations}

    except Exception as e:
        logger.error(f"Error getting brand citation repository for {brand_name}: {e}")
        return {'citations': [], 'total_citations': 0}

def get_previous_sov_data(brand_name: str, user_id: str, current_session_id: str) -> List[Dict[str, Any]]:
    """
    Finds the most recent session before current_session_id and returns its SOV data.
    """
    try:
        # 1. Get current session timestamp
        current_session = supabase.table('analysis_sessions').select('timestamp').eq('session_id', current_session_id).execute()
        if not current_session.data:
            return []
        
        current_timestamp = current_session.data[0]['timestamp']

        # 2. Find the session immediately preceding this one for the same brand/user
        prev_session_query = supabase.table('analysis_sessions').select('session_id').eq('brand_name', brand_name).eq('user_id', user_id).lt('timestamp', current_timestamp).order('timestamp', desc=True).limit(1).execute()
        
        if not prev_session_query.data:
            return []
        
        prev_session_id = prev_session_query.data[0]['session_id']
        logger.info(f"Found previous session {prev_session_id} for comparison with {current_session_id}")

        # 3. Get SOV data for that previous session
        sov_response = supabase.table('share_of_voice').select('*').eq('session_id', prev_session_id).execute()
        return sov_response.data or []

    except Exception as e:
        logger.error(f"Error getting previous SOV data: {e}")
        return []
