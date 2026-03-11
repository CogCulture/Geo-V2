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

def save_llm_response(prompt_id: str, session_id: str, llm_name: str, 
                     prompt_text: str, response_text: str, citations: Optional[List[str]] = None):
    try:
        timestamp = datetime.now().isoformat()
        
        data = {
            'prompt_id': prompt_id,
            'session_id': session_id,
            'llm_name': llm_name,
            'prompt_text': prompt_text,
            'response_text': response_text,
            'citations': citations,
            'timestamp': timestamp
        }
        
        supabase.table('llm_responses').insert(data).execute()
    except Exception as e:
        logger.error(f"Error saving LLM response: {str(e)}")
        raise

def save_scoring_result(prompt_id: str, session_id: str, llm_name: str, scores: Dict[str, Any]):
    try:
        timestamp = datetime.now().isoformat()
        
        data = {
            'prompt_id': prompt_id,
            'session_id': session_id,
            'llm_name': llm_name,
            'brand_mention_score': scores.get('brand_mention_score', 0),
            'position_score': scores.get('position_score', 0),
            'description_richness_score': scores.get('description_richness_score', 0),
            'keyword_strength_score': scores.get('keyword_strength_score', 0),
            'total_score': scores.get('total_score', 0),
            'normalized_visibility': scores.get('normalized_visibility', 0),
            'average_positioning': scores.get('average_positioning', 0),
            'weighted_score': scores.get('weighted_score', 0),
            'brand_position': scores.get('brand_position', 0),
            'total_items': scores.get('total_items', 0),
            'timestamp': timestamp
        }
        
        supabase.table('scoring_results').insert(data).execute()
    except Exception as e:
        logger.error(f"Error saving scoring result: {str(e)}")
        raise
def save_competitors(session_id: str, competitors: list):
    try:
        data = [
            {
                'session_id': session_id,
                'competitor_name': competitor,
                'rank': rank
            }
            for rank, competitor in enumerate(competitors, 1)
        ]
        
        supabase.table('competitors').insert(data).execute()
        logger.info(f"✓ Saved {len(competitors)} competitors for session {session_id}")
    except Exception as e:
        logger.error(f"Error saving competitors: {str(e)}")
        raise
def save_share_of_voice(session_id: str, brand_name: str, sov_scores: Dict[str, Any], rank: int):
    try:
        timestamp = datetime.now().isoformat()
        
        data = {
            'session_id': session_id,
            'brand_name': brand_name,
            'normalized_visibility': sov_scores.get('normalized_visibility', 0),
            'average_positioning': sov_scores.get('average_positioning', 0),
            'weighted_score': sov_scores.get('weighted_score', 0),
            'rank': rank,
            'timestamp': timestamp
        }
        
        supabase.table('share_of_voice').insert(data).execute()
    except Exception as e:
        logger.error(f"Error saving share of voice: {str(e)}")
        raise
def save_brand_score_summary(session_id: str, brand_name: str, summary: Dict[str, Any]):
    try:
        timestamp = datetime.now().isoformat()
        summary_prompt_id = f"{session_id}_summary"
        
        total_prompts = summary.get('total_prompts', 0)
        total_mentions = summary.get('total_mentions', 0)
        mention_rate = summary.get('mention_rate', 0)
        
        mention_based_visibility = mention_rate
        
        data = {
            'prompt_id': summary_prompt_id,
            'session_id': session_id,
            'llm_name': 'SUMMARY',
            'brand_mention_score': total_mentions,
            'position_score': summary.get('avg_position', 0),
            'description_richness_score': 0,
            'keyword_strength_score': 0,
            'total_score': mention_based_visibility,
            'normalized_visibility': mention_based_visibility,
            'average_positioning': summary.get('avg_position', 0),
            'weighted_score': mention_based_visibility,
            'brand_position': 0,
            'total_items': total_prompts,
            'timestamp': timestamp
        }
        
        supabase.table('scoring_results').insert(data).execute()
        logger.info(f"✅ Saved brand score summary for session {session_id}: {mention_based_visibility:.2f}% visibility ({total_mentions}/{total_prompts})")
    except Exception as e:
        logger.error(f"Error saving brand score summary: {str(e)}")
        raise
def get_session_results(session_id: str) -> Dict[str, Any]:
    try:
        # Get session metadata
        session_response = supabase.table('analysis_sessions').select('*').eq('session_id', session_id).execute()
        session = session_response.data[0] if session_response.data else None
        
        if not session:
            logger.warning(f"Session {session_id} not found in database")
            return None
        
        logger.info(f"Found session {session_id}, fetching related data")
        
        # Get LLM responses
        responses_response = supabase.table('llm_responses').select('*').eq('session_id', session_id).execute()
        responses = responses_response.data
        
        # Get scoring results
        scores_response = supabase.table('scoring_results').select('*').eq('session_id', session_id).execute()
        scores = scores_response.data
        
        # Get competitors
        competitors_response = supabase.table('competitors').select('*').eq('session_id', session_id).order('rank').execute()
        competitors = competitors_response.data
        
        # Get Share of Voice
        sov_response = supabase.table('share_of_voice').select('*').eq('session_id', session_id).order('rank').execute()
        sov = sov_response.data
        
        logger.info(f"Session {session_id}: {len(responses or [])} responses, {len(scores or [])} scores, {len(competitors or [])} competitors")
        
        return {
            'session': session,
            'responses': responses,
            'scores': scores,
            'competitors': competitors,
            'share_of_voice': sov
        }
    except Exception as e:
        logger.error(f"Error getting session results: {str(e)}", exc_info=True)
        return None
def get_brand_visibility_history(brand_name: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
   
   
    try:
        # Build query for sessions for this brand (and optionally user)
        query = supabase.table('analysis_sessions').select(
            'session_id, brand_name, timestamp'
        ).eq('brand_name', brand_name)

        if user_id:
            query = query.eq('user_id', user_id)

        sessions_response = query.order('timestamp').execute()
        
        sessions = sessions_response.data
        
        if not sessions:
            logger.warning(f"No sessions found for brand: {brand_name} (user_id={user_id})")
            return []
        
        # Optimization: Fetch all scores in one query instead of N+1
        session_ids = [s['session_id'] for s in sessions]
        
        if not session_ids:
             return []
             
        # Batch fetch scores for all sessions in this history
        scores_response = supabase.table('scoring_results').select(
            'session_id, brand_mention_score, average_positioning'
        ).in_('session_id', session_ids).neq('llm_name', 'SUMMARY').execute()
        
        all_scoring_results = scores_response.data or []
        
        # Group scores by session_id for O(1) access
        scores_by_session = {}
        for score in all_scoring_results:
            sid = score['session_id']
            if sid not in scores_by_session:
                scores_by_session[sid] = []
            scores_by_session[sid].append(score)
        
        result = []
        
        # Process each session in memory using the batched data
        for session in sessions:
            session_id = session['session_id']
            
            # Get pre-fetched scores from our dictionary
            scoring_results = scores_by_session.get(session_id, [])
            
            total_prompts = len(scoring_results)
            mentions = sum(1 for s in scoring_results if s.get('brand_mention_score', 0) > 0)
            
            visibility = (mentions / total_prompts * 100) if total_prompts > 0 else 0
            
            # Calculate Avg Position (only for prompts where brand was found/ranked)
            positions = [s.get('average_positioning', 0) for s in scoring_results if s.get('average_positioning', 0) > 0]
            avg_position = sum(positions) / len(positions) if positions else 0

            timestamp = session['timestamp']
            date = timestamp.split('T')[0] if 'T' in timestamp else timestamp.split(' ')[0]
            
            result.append({
                'date': date,
                'timestamp': timestamp,
                'visibility': round(float(visibility), 2),
                'average_position': round(float(avg_position), 2),
                'session_id': session_id,
                'brand_name': brand_name
            })
        
        logger.info(f"✅ Retrieved {len(result)} historical sessions for brand: {brand_name} (user_id={user_id})")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error getting brand visibility history for {brand_name}: {str(e)}")
        return []
def get_llm_aggregate_scores(session_id: str, llm_name: str) -> Dict[str, float]:

    try:
        response = supabase.table('scoring_results').select(
            'normalized_visibility, average_positioning, weighted_score'
        ).eq('session_id', session_id).eq('llm_name', llm_name).execute()
        
        results = response.data
        
        if not results:
            return {
                'avg_visibility': 0,
                'avg_positioning': 0,
                'avg_weighted_score': 0,
                'total_prompts': 0
            }
        
        total_prompts = len(results)
        avg_visibility = sum(r['normalized_visibility'] for r in results) / total_prompts
        
        positioning_scores = [r['average_positioning'] for r in results if r['average_positioning'] > 0]
        avg_positioning = sum(positioning_scores) / len(positioning_scores) if positioning_scores else 0
        
        avg_weighted = sum(r['weighted_score'] for r in results) / total_prompts
        
        return {
            'avg_visibility': round(avg_visibility, 2),
            'avg_positioning': round(avg_positioning, 2),
            'avg_weighted_score': round(avg_weighted, 2),
            'total_prompts': total_prompts
        }
    except Exception as e:
        logger.error(f"Error getting LLM aggregate scores: {str(e)}")
        return {'avg_visibility': 0, 'avg_positioning': 0, 'avg_weighted_score': 0, 'total_prompts': 0}
def get_saved_prompts(brand_name: str, product_name: Optional[str] = None) -> Optional[List[str]]:

    try:
        query = supabase.table('saved_prompts').select('prompts_json').eq('brand_name', brand_name)
        
        if product_name:
            query = query.eq('product_name', product_name)
        else:
            query = query.is_('product_name', 'null')
        
        response = query.execute()
        
        if response.data:
            return response.data[0]['prompts_json']
        return None
    except Exception as e:
        logger.error(f"Error retrieving saved prompts: {str(e)}")
        return None

def save_prompts_to_db(brand_name: str, prompts: List[str], product_name: Optional[str] = None):

    try:
        timestamp = datetime.now().isoformat()
        
        data = {
            'brand_name': brand_name,
            'product_name': product_name,
            'prompts_json': prompts,
            'timestamp': timestamp
        }
        
        # Upsert (insert or update if exists)
        supabase.table('saved_prompts').upsert(data).execute()
    except Exception as e:
        logger.error(f"Error saving prompts: {str(e)}")
        raise
def get_session_results_aggregated(session_id: str):

    try:
        logger.info(f"Fetching aggregated results for session: {session_id}")
        
        # Get session metadata
        session_response = supabase.table('analysis_sessions').select('*').eq('session_id', session_id).execute()
        
        if not session_response.data:
            logger.warning(f"Session {session_id} not found in database")
            return None
        
        session_dict = session_response.data[0]
        brand_name = session_dict.get('brand_name', 'Unknown')
        logger.info(f"Found session {session_id} for brand {brand_name}")

        # Get LLM responses - Optimizing columns to avoid PROTOCOL_ERROR
        llm_response = supabase.table('llm_responses').select(
            'id, prompt_id, llm_name, prompt_text, response_text, citations'
        ).eq('session_id', session_id).order('id').execute()
        llm_rows = llm_response.data
        
        # Get scoring results
        scoring_response = supabase.table('scoring_results').select('*').eq('session_id', session_id).execute()
        scoring_results = scoring_response.data
        
        # Optimize: Group scores by (prompt_id, llm_name) for O(1) lookup
        scores_by_key = {
            (s.get('prompt_id'), s.get('llm_name')): s 
            for s in (scoring_results or [])
        }
        
        # NEW: Fetch Cohorts for this session
        from db.cohorts import get_cohorts_for_session
        cohorts = get_cohorts_for_session(session_id) 
        
        llm_responses = []
        all_citations = []

        for row in (llm_rows or []):
            response_text = row.get('response_text', '')
            prompt_text = row.get('prompt_text', '').strip() or 'Source Unknown'
            llm_name = row.get('llm_name', 'Unknown')
            prompt_id = row.get('prompt_id')

            citations = row.get('citations', []) or []

            visibility_score = 0
            matching_score = scores_by_key.get((prompt_id, llm_name))
            
            if matching_score:
                visibility_score = float(matching_score.get('normalized_visibility', 0))

            llm_responses.append({
                'prompt': prompt_text,
                'response': response_text,
                'llm_name': llm_name,
                'citations': citations,
                'visibility_score': visibility_score
            })
            all_citations.extend(citations)

        # Domain citations
        domain_citations = []
        if all_citations:
            domains = []
            for citation_url in all_citations:
                try:
                    parsed = urlparse(citation_url)
                    domain = parsed.netloc or parsed.path
                    if domain:
                        domains.append(domain.replace('www.', ''))
                except:
                    continue
            
            if domains:
                domain_counts = Counter(domains)
                total_citations = len(domains)
                domain_citations = [
                    {'domain': d, 'citations': c, 'percentage': round((c/total_citations*100), 1)}
                    for d, c in domain_counts.most_common(10)
                ]
        
        # Calculate mention-based visibility metrics
        non_summary_scores = [s for s in scoring_results if s.get('llm_name') != 'SUMMARY']
        
        total_prompts_analyzed = len(non_summary_scores)
        total_mentions = sum(1 for s in non_summary_scores if s.get('brand_mention_score', 0) > 0)
        
        positioned_scores = [s for s in non_summary_scores if s.get('average_positioning', 0) > 0]
        avg_position = sum(s['average_positioning'] for s in positioned_scores) / len(positioned_scores) if positioned_scores else 0
        
        mention_based_visibility = (total_mentions / total_prompts_analyzed * 100) if total_prompts_analyzed > 0 else 0
        
        # Share of Voice
        sov_response = supabase.table('share_of_voice').select('*').eq('session_id', session_id).order('rank').execute()
        sov_rows = sov_response.data or []
        
        brand_scores = []
        share_of_voice = []

        total_sov_mass = 0
        temp_sov_data = []

        if sov_rows:
            for row in sov_rows:
                mass = float(row.get('normalized_visibility', 0))
                total_sov_mass += mass
                temp_sov_data.append(row)
        else:
            total_sov_mass = mention_based_visibility
            temp_sov_data.append({
                'brand_name': brand_name,
                'normalized_visibility': mention_based_visibility,
                'average_positioning': avg_position,
                'total_mentions': total_mentions
            })

        for r in temp_sov_data:
            brand = r.get('brand_name', 'Unknown')
            sov_visibility = float(r.get('normalized_visibility', 0))
            
            if total_sov_mass > 0:
                pie_slice_percentage = (sov_visibility / total_sov_mass) * 100
            else:
                pie_slice_percentage = 0

            if brand == brand_name:
                display_visibility = mention_based_visibility
            else:
                display_visibility = sov_visibility
            
            # Get previous average position for delta calculation
            user_id = session_dict.get('user_id')
            from db.citations import get_previous_sov_data
            prev_sov = get_previous_sov_data(brand_name, user_id, session_id)
            prev_data = next((p for p in prev_sov if p.get('brand_name') == brand), None)
            prev_avg_pos = float(prev_data.get('average_positioning', 0)) if prev_data else 0

            brand_scores.append({
                'brand': brand,
                'mention_count': total_mentions if brand == brand_name else r.get('rank', 0),
                'average_position': float(r.get('average_positioning', 0)),
                'prev_average_position': prev_avg_pos,
                'visibility_score': display_visibility,
                'mention_rate': display_visibility / 100,
                'rank': r.get('rank', 0)
            })
            
            share_of_voice.append({
                'brand': brand,
                'percentage': round(pie_slice_percentage, 1),
                'mention_count': r.get('total_mentions', 0)
            })

        # Competitors
        competitors_response = supabase.table('competitors').select('competitor_name').eq('session_id', session_id).order('rank').execute()
        competitors = [row['competitor_name'] for row in (competitors_response.data or [])]
        
        return {
            'session_id': session_id,
            'brand_name': brand_name,
            'num_prompts': total_prompts_analyzed,
            'brand_scores': brand_scores,
            'share_of_voice': share_of_voice,
            'llm_responses': llm_responses,
            'domain_citations': domain_citations,
            'competitors': competitors,
            'cohorts': cohorts, # ✅ Added cohorts here
            'created_at': session_dict.get('timestamp', ''),
            'average_visibility_score': mention_based_visibility,
            'average_position': avg_position,
            'average_mentions': total_mentions,
            'session_metadata': {
                'user_id': session_dict.get('user_id'),
                'product_name': session_dict.get('product_name'),
                'website_url': session_dict.get('website_url'),
                'keywords': session_dict.get('keywords')
            }
        }
    except Exception as e:
        logger.error(f"Error getting aggregated results: {e}", exc_info=True)
        return None
def get_saved_prompts_for_analysis(session_id: str):
    try:
        response = supabase.table('llm_responses').select('prompt_text').eq('session_id', session_id).order('timestamp').execute()
        
        # Get unique prompts
        prompts = list(set(row['prompt_text'] for row in response.data))
        return prompts
    except Exception as e:
        logger.error(f"Error getting saved prompts for analysis: {str(e)}")
        return []
def get_visibility_history_for_same_prompts(brand_name: str, product_name: str, prompts: list):
    try:
        if not prompts or not brand_name:
            logger.warning("No prompts or brand_name provided for same prompts history")
            return []
        
        # Get all sessions for this brand
        sessions_response = supabase.table('analysis_sessions').select(
            'session_id, timestamp'
        ).eq('brand_name', brand_name).order('timestamp').execute()
        
        sessions = sessions_response.data
        
        if not sessions:
            return []
            
        session_ids = [s['session_id'] for s in sessions]
        
        # Batch fetch LLM responses to find prompt_ids for these specific prompts across all sessions
        responses_res = supabase.table('llm_responses').select(
            'session_id, prompt_id, prompt_text'
        ).in_('session_id', session_ids).in_('prompt_text', prompts).execute()
        
        # Group prompt_ids by session_id
        prompt_ids_by_session = {}
        for r in (responses_res.data or []):
            sid = r['session_id']
            pid = r['prompt_id']
            if sid not in prompt_ids_by_session:
                prompt_ids_by_session[sid] = []
            prompt_ids_by_session[sid].append(pid)
            
        # Collect all relevant prompt_ids for batch fetching scores
        all_relevant_pids = []
        for pids in prompt_ids_by_session.values():
            all_relevant_pids.extend(pids)
            
        if not all_relevant_pids:
            return []
            
        # Batch fetch scoring results for these sessions and prompts
        # We filter by session_ids AND the specific prompt_ids we care about
        scores_res = supabase.table('scoring_results').select(
            'session_id, prompt_id, brand_mention_score'
        ).in_('session_id', session_ids).in_('prompt_id', all_relevant_pids).neq('llm_name', 'SUMMARY').execute()
        
        # Group scores by session_id
        scores_by_session = {}
        for s in (scores_res.data or []):
            sid = s['session_id']
            pid = s['prompt_id']
            # Only include if it matches a prompt_id for THIS session
            if pid in prompt_ids_by_session.get(sid, []):
                if sid not in scores_by_session:
                    scores_by_session[sid] = []
                scores_by_session[sid].append(s)
            
        chart_data = []
        
        for session in sessions:
            session_id = session['session_id']
            
            # Get pre-fetched scores for this session's relevant prompts
            scoring_results = scores_by_session.get(session_id, [])
            
            if not scoring_results:
                continue
                
            total_prompts = len(scoring_results)
            mentions = sum(1 for s in scoring_results if s.get('brand_mention_score', 0) > 0)
            
            visibility = (mentions / total_prompts * 100) if total_prompts > 0 else 0
            
            timestamp = session['timestamp']
            if 'T' in timestamp:
                date_display = timestamp.split('T')[0]
                time_display = timestamp.split('T')[1][:5]
            else:
                date_display = timestamp.split(' ')[0]
                time_display = timestamp.split(' ')[1][:5] if ' ' in timestamp else '00:00'
            
            chart_data.append({
                'date': f"{date_display} {time_display}",
                'visibility': round(visibility, 2),
                'timestamp': timestamp,
                'session_id': session_id
            })
        
        logger.info(f"✅ Found {len(chart_data)} session points for same prompts history (brand: {brand_name})")
        return chart_data
        
    except Exception as e:
        logger.error(f"Error in get_visibility_history_for_same_prompts: {str(e)}", exc_info=True)
        return []
def get_product_specific_visibility_history(brand_name: str, product_name: str, user_id: Optional[str] = None):
    try:
        # Build query for sessions for brand+product (optionally scoped to user)
        query = supabase.table('analysis_sessions').select(
            'session_id, timestamp'
        ).eq('brand_name', brand_name).eq('product_name', product_name)

        if user_id:
            query = query.eq('user_id', user_id)

        sessions_response = query.order('timestamp').execute()
        
        sessions = sessions_response.data
        
        if not sessions:
            return []
            
        # Optimization: Fetch all scores in one query instead of N+1
        session_ids = [s['session_id'] for s in sessions]
        
        # Batch fetch all normalized visibility scores for these sessions
        scores_response = supabase.table('scoring_results').select(
            'session_id, normalized_visibility'
        ).in_('session_id', session_ids).execute()
        
        all_scores = scores_response.data or []
        
        # Group by session_id
        scores_by_session = {}
        for score in all_scores:
            sid = score['session_id']
            if sid not in scores_by_session:
                scores_by_session[sid] = []
            scores_by_session[sid].append(score)
        
        history = {}
        
        # Process each session using the batched data
        for session in sessions:
            session_id = session['session_id']
            
            # Get pre-fetched scores
            scoring_results = scores_by_session.get(session_id, [])
            
            if scoring_results:
                avg_visibility = sum(s['normalized_visibility'] for s in scoring_results) / len(scoring_results)
                
                timestamp = session['timestamp']
                date = timestamp.split('T')[0] if 'T' in timestamp else timestamp.split(' ')[0]
                
                if date not in history:
                    history[date] = []
                history[date].append(avg_visibility)
        
        chart_data = [
            {
                'date': date,
                'visibility': round(sum(scores) / len(scores), 2),
                'timestamp': date
            }
            for date, scores in sorted(history.items())
        ]
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Error getting product visibility history: {str(e)}")
        return []
