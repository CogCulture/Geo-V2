import os
import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Header, Query
from pydantic import BaseModel
from collections import defaultdict
import asyncio
from urllib.parse import unquote

from api.auth import get_current_user
from api.config import PLAN_LIMITS
from services.tracking import send_signal
from db.client import supabase
from db.sessions import update_session_status
from services.database_manager import *
from services.scoring_engine import calculate_scores, aggregate_results
from services.share_of_voice import calculate_share_of_voice
from services.url_keyword_extractor import extract_keywords_from_url
from services.deep_research import conduct_deep_research
from services.multi_llm_executor import execute_prompts_multi_llm_sync
from services.prompt_generator import generate_prompts_by_cohort, generate_prompts
from services.keyword_extractor import extract_keywords

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analysis"])

class CustomExecutionRequest(BaseModel):
    prompts: List[str]
    llms: List[str]

class CompetitorUpdateRequest(BaseModel):
    competitors: List[str]

class AnalysisRequest(BaseModel):
    brand_name: str
    product_name: Optional[str] = None
    industry: Optional[str] = None
    website_url: Optional[str] = None
    selected_llms: List[str] = []
    regenerate_prompts: bool = True
    custom_keywords: Optional[List[str]] = None
    custom_competitors: Optional[List[str]] = None
    project_id: Optional[str] = None
    brand_aliases: Optional[List[str]] = None

class ResearchRequest(BaseModel):
    brand_name: str
    website_url: Optional[str] = None


# In app.py - Update the /api/analysis/run endpoint

@router.post("/api/analysis/research")
async def conduct_research_endpoint(request: ResearchRequest, user_id: str = Depends(get_current_user)):
    """Conduct deep research to find competitors and industry info"""
    try:
        from services.deep_research import conduct_deep_research
        
        if not request.brand_name:
             raise HTTPException(status_code=400, detail="Brand name is required")
        
        logger.info(f"🔍 Starting deep research for {request.brand_name}...")
        
        # Run deep research (synchronously for now as per user request flow)
        results = conduct_deep_research(
            brand_name=request.brand_name,
            website_url=request.website_url
        )
        
        return {
            "status": "success", 
            "data": results
        }
    except Exception as e:
        logger.error(f"Error in deep research endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/analysis/run")
async def run_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    """Start a new analysis (runs in background)"""
    try:
        # ─── Plan Limit Enforcement ───
        sub_status = get_subscription_status(user_id)
        raw_plan = sub_status.get("subscription_plan", "free") if sub_status else "free"
        plan_name = raw_plan.lower() if raw_plan else "free"
        limits = PLAN_LIMITS.get(plan_name, PLAN_LIMITS["free"])

        # If project_id is missing, this is a new brand/project analysis
        if not request.project_id:
            existing_projects = get_user_projects(user_id)
            # Check if a project with this name already exists (case-insensitive)
            brand_exists = any(p['name'].lower() == request.brand_name.lower() for p in existing_projects)
            
            if not brand_exists and len(existing_projects) >= limits["max_projects"]:
                raise HTTPException(
                    status_code=403,
                    detail=f"Project limit reached for your {plan_name.capitalize()} ({limits['max_projects']} max). Please upgrade or delete an existing project."
                )

        custom_keywords = None
        if request.custom_keywords and len(request.custom_keywords) > 0:
            # Clean and validate keywords
            custom_keywords = [k.strip() for k in request.custom_keywords if k.strip()]
            custom_keywords = list(set(custom_keywords))  # Remove duplicates
            if len(custom_keywords) > 20:
                custom_keywords = custom_keywords[:20]
            
            logger.info(f"✅ Custom keywords provided: {custom_keywords}")
        
        # Validate custom competitors if provided
        custom_competitors = None
        if request.custom_competitors and len(request.custom_competitors) > 0:
            # Clean and validate competitor names
            custom_competitors = [c.strip() for c in request.custom_competitors if c.strip()]
            
            # Remove duplicates
            custom_competitors = list(set(custom_competitors))
            
            # Limit to 10 competitors
            if len(custom_competitors) > 10:
                custom_competitors = custom_competitors[:10]
            
            logger.info(f"✅ Custom competitors provided: {custom_competitors}")
        
        # ✅ NEW: Use selected_llms if provided, otherwise empty list (will be selected in cohort selector)
        normalized_llms = []
        if request.selected_llms and len(request.selected_llms) > 0:
            valid_llms = ["Claude", "Mistral", "Google AI Overview"]
            
            for llm in request.selected_llms:
                if isinstance(llm, str):
                    matched = False
                    for valid_llm in valid_llms:
                        if valid_llm.lower() in llm.lower() or llm.lower() in valid_llm.lower():
                            normalized_llms.append(valid_llm)
                            matched = True
                            break
                    
                    if not matched and llm.lower() not in ["string", ""]:
                        normalized_llms.append(llm)
        
        # Create session ID
        session_id = create_session_id(request.brand_name, request.product_name)
        
        # ✅ FIX: Save initial status to DB instead of memory
        # ✅ FIX: Save initial status to DB instead of memory
        save_session(session_id, request.brand_name, user_id, request.product_name, request.website_url, None, None, request.industry, request.project_id, request.brand_aliases)
        update_session_status(session_id, status="running", progress=0, step="Initializing...")
        
        send_signal("analysis_initialized", session_id, {"brand": request.brand_name})
        
        logger.info(f"🚀 Analysis started for {request.brand_name} (Session: {session_id}) by user {user_id}")
        if normalized_llms:
            logger.info(f"   LLMs: {normalized_llms}")
        else:
            logger.info(f"   LLMs: Will be selected in cohort selector")
        if custom_competitors:
            logger.info(f"   Custom Competitors: {custom_competitors}")
        
        # Add background task
        background_tasks.add_task(
            execute_analysis_workflow,
            session_id,
            request.brand_name,
            request.product_name,
            request.industry,
            request.website_url,
            normalized_llms,  # Can be empty list now
            request.regenerate_prompts,
            custom_keywords,
            custom_competitors,
            user_id,
            request.project_id,
            request.brand_aliases
        )
        
        return {
            "session_id": session_id,
            "status": "started",
            "message": f"Analysis started for {request.brand_name}"
        }
    
    except HTTPException as e:
        logger.error(f"❌ Validation error: {str(e.detail)}")
        raise
    except Exception as e:
        logger.error(f"❌ Error starting analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ✅ NEW ENDPOINT: This solves the metric mix-up issue
@router.post("/api/analysis/fork-session")
async def fork_session(
    request: CustomExecutionRequest, 
    parent_session_id: str = Query(..., description="The ID of the session to copy context from"),
    background_tasks: BackgroundTasks = None,
    user_id: str = Depends(get_current_user)
):
    """
    Creates a NEW session based on an old one, but only executes the specific provided prompts.
    This ensures metrics are calculated ONLY for these prompts.
    """
    try:
        # 1. Get Parent Session Metadata
        parent_metadata = get_session_metadata(parent_session_id)
        if not parent_metadata:
            raise HTTPException(status_code=404, detail="Parent session not found")
        
        brand_name = parent_metadata['brand_name']
        product_name = parent_metadata.get('product_name')
        
        # 2. Create NEW Session ID
        new_session_id = create_session_id(brand_name, product_name)
        
        # 3. Save New Session
        save_session(
            new_session_id,
            brand_name,
            user_id,
            product_name,
            parent_metadata.get('website_url'),
            parent_metadata.get('research_data'),
            parent_metadata.get('keywords'),
            parent_metadata.get('industry'),
            parent_metadata.get('project_id')
        )

        # 4. Initialize Status
        update_session_status(new_session_id, status="running", progress=0, step="Queuing Custom Analysis...")
        
        send_signal("analysis_initialized", new_session_id, {"event": "fork_session", "parent_session_id": parent_session_id})

        # ✅ NEW STEP: Duplicate Cohorts & Prompts for the UI
        # Run this immediately so the UI has data when it loads
        duplicate_session_cohorts(parent_session_id, new_session_id)
        duplicate_session_competitors(parent_session_id, new_session_id)
        
        # 5. Start Execution
        if background_tasks:
            background_tasks.add_task(
                execute_prompts_workflow,
                new_session_id,
                request.prompts,
                request.llms
            )
        
        return {
            "success": True, 
            "new_session_id": new_session_id, 
            "message": "New analysis session started"
        }

    except Exception as e:
        logger.error(f"Error forking session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/analysis/status/{session_id}")
def get_status(session_id: str):
    """Get status from DB (Stateless)"""
    return get_session_status(session_id)

@router.post("/api/analysis/execute-custom-prompts/{session_id}")
async def execute_custom_prompts_endpoint(
    session_id: str, 
    request: CustomExecutionRequest, 
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """
    Executes a specific list of raw prompt strings. 
    Used by the Dashboard Prompt Manager tab for re-analysis or custom prompt execution.
    """
    try:
        if not request.prompts:
            raise HTTPException(status_code=400, detail="No prompts provided")
        
        if not request.llms:
             raise HTTPException(status_code=400, detail="No LLMs selected")
            
        # Update Status to indicate we are starting
        update_session_status(session_id, status="running", progress=0, step="Queuing Custom Analysis...")

        send_signal("analysis_initialized", session_id, {"event": "execute_custom_prompts"})

        logger.info(f"🚀 Custom Execution started for Session {session_id}")
        logger.info(f"   Prompts: {len(request.prompts)}")
        logger.info(f"   LLMs: {request.llms}")

        # Reuse the existing workflow function
        background_tasks.add_task(
            execute_prompts_workflow,
            session_id,
            request.prompts, # Passing raw strings here
            request.llms
        )
        
        return {
            "success": True, 
            "message": "Execution started", 
            "data": {"prompt_count": len(request.prompts)}
        }

    except Exception as e:
        logger.error(f"Error starting custom execution: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/recent-analyses")
def recent_analyses(user_id: str = Depends(get_current_user)):
    try:
        # Get recent sessions for the current user
        recent_sessions = get_user_sessions(user_id)
        # Example format: [{session_id, brand_name, timestamp, product_name, website_url}]
        return {"total": len(recent_sessions), "analyses": recent_sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent analyses: {str(e)}")
    
@router.get("/api/analysis/status/{session_id}")
async def get_session_status_endpoint(session_id: str):
    """Get current analysis progress from database"""
    try:
        from services.database_manager import get_session_status
        
        status = get_session_status(session_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/results/{session_id}")
def get_results(session_id: str, user_id: str = Depends(get_current_user)):
    """Get completed analysis results"""
    try:
        from services.database_manager import get_session_results_aggregated, get_session_metadata
        
        # First check if session exists using lightweight metadata query
        session_metadata = get_session_metadata(session_id)
        if not session_metadata:
            logger.error(f"❌ Session not found in database: {session_id}")
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Verify user owns this session
        stored_user_id = session_metadata.get('user_id')
        
        # Log IDs for debugging (hide first part for security)
        logger.info(f"🔍 Verifying access: User {str(user_id)[-5:]} vs Session Owner {str(stored_user_id)[-5:]}")
        
        if str(stored_user_id) != str(user_id):
            logger.warning(f"🚫 Access denied for user {user_id} to session {session_id} (Owned by {stored_user_id})")
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get aggregated results
        logger.info(f"📊 Fetching aggregated results for {session_id}...")
        results = get_session_results_aggregated(session_id)
        if not results:
            logger.warning(f"⏳ No aggregated results found for session {session_id}.")
            # Return session metadata with empty results instead of 404
            return {
                'session_id': session_id,
                'brand_name': session_metadata.get('brand_name', 'Unknown'),
                'num_prompts': 0,
                'brand_scores': [],
                'share_of_voice': [],
                'llm_responses': [],
                'domain_citations': [],
                'competitors': [],
                'cohorts': [],
                'created_at': session_metadata.get('timestamp', ''),
                'average_visibility_score': 0,
                'average_position': 0,
                'average_mentions': 0,
                'debug_msg': 'AGGREGATOR_RETURNED_NONE',
                'session_metadata': {
                    'user_id': session_metadata.get('user_id'),
                    'product_name': session_metadata.get('product_name'),
                    'website_url': session_metadata.get('website_url'),
                    'keywords': session_metadata.get('keywords')
                },
                'message': 'Session found but results are still being processed'
            }
        
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching results: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/analysis/citations/{session_id}")
def get_citation_analytics(session_id: str, user_id: str = Depends(get_current_user)):
    """Get detailed citation analytics for a session"""
    try:
        from services.database_manager import get_detailed_citation_analytics
        
        results = get_detailed_citation_analytics(session_id)
        return results
    except Exception as e:
        logger.error(f"Error getting citation analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/analysis/citations/brand/{brand_name}")
def get_brand_citation_analytics(brand_name: str, user_id: str = Depends(get_current_user)):
    """Get aggregated citation analytics for all sessions of a brand"""
    try:
        from services.database_manager import get_brand_citation_repository
        
        # Safe decoding of brand name if it's URL encoded
        from urllib.parse import unquote
        decoded_brand_name = unquote(brand_name)
        
        logger.info(f"📊 Fetching brand-wide citation repository for '{decoded_brand_name}'")
        results = get_brand_citation_repository(decoded_brand_name, user_id)
        return results
    except Exception as e:
        logger.error(f"Error getting brand citation analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/results/")
def list_sessions(user_id: str = Depends(get_current_user)):
    """List user's sessions"""
    try:
        from services.database_manager import get_user_sessions
        sessions = get_user_sessions(user_id)
        return {
            "total": len(sessions),
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/analysis/generate-custom-cohort-prompts/{session_id}")
async def generate_custom_cohort_prompts(
    session_id: str,
    request: dict
):
    """
    Generate prompts for a user-created custom cohort.
    User provides cohort name/description, backend generates 5 prompts.
    """
    try:
        # Verify session exists in database
        from services.database_manager import get_session_results
        session_check = get_session_results(session_id)
        if not session_check:
            raise HTTPException(status_code=404, detail="Session not found")
        
        cohort_name = request.get("cohort_name", "").strip()
        cohort_description = request.get("cohort_description", "").strip()
        
        if not cohort_name:
            raise HTTPException(status_code=400, detail="Cohort name is required")
        
        logger.info(f" Generating prompts for custom cohort: {cohort_name}")
        
        # Get session data for context
        from services.database_manager import get_session_results, get_cohorts_for_session, save_custom_cohort, save_prompts_with_cohorts
        
        session_data = get_session_results(session_id)
        if not session_data or 'session' not in session_data:
            raise HTTPException(status_code=404, detail="Session data not found")
        
        session_metadata = session_data['session']
        brand_name = session_metadata.get('brand_name')
        product_name = session_metadata.get('product_name')  #  Correct
        research_data = session_metadata.get('research_data', {})  #  Correct
        keywords = session_metadata.get('keywords', [])  #  Correct
        industry = session_metadata.get('industry')  #  Correct   
        
        # Create cohort dict for prompt generation
        custom_cohort = {
            'name': cohort_name,
            'description': cohort_description or f"Custom cohort focusing on {cohort_name}",
            'prompt_count': 5
        }
        
        # Generate prompts using existing logic
        from services.prompt_generator import generate_prompts_by_cohort
        
        prompts = generate_prompts_by_cohort(
            brand_name=brand_name,
            cohort=custom_cohort,
            research_context=research_data,
            keywords=keywords,
            industry=industry,
            product_name=product_name
        )
        
        # Save custom cohort to database
        existing_cohorts = get_cohorts_for_session(session_id)
        cohort_order = len(existing_cohorts)
        
        cohort_id = save_custom_cohort(
            session_id,
            cohort_name,
            cohort_description or custom_cohort['description'],
            cohort_order
        )
        
        if cohort_id < 0:
            raise HTTPException(status_code=500, detail="Failed to save custom cohort")
        
        # Save generated prompts
        cohort_prompts_data = [{
            'cohort_id': cohort_id,
            'prompts': prompts
        }]
        save_prompts_with_cohorts(session_id, cohort_prompts_data)
        
        logger.info(f" Generated {len(prompts)} prompts for custom cohort '{cohort_name}'")
        
        return {
            "cohort_id": cohort_id,
            "cohort_name": cohort_name,
            "cohort_description": cohort_description,
            "prompts": prompts,
            "message": f"Generated {len(prompts)} prompts for {cohort_name}"
        }
        
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error generating custom cohort prompts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/api/analysis/execute-selected-prompts/{session_id}")
async def execute_selected_prompts(
    session_id: str,
    background_tasks: BackgroundTasks,
    request: dict
):
    """
    Execute analysis with user-selected/custom cohorts and prompts
    """
    try:
        # Check if session exists in database
        from services.database_manager import get_session_results
        session_data = get_session_results(session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # ── 1. Plan-Based Limit Enforcement ────────────────────────────────
        session_user_id = session_data.get('session', {}).get('user_id')
        sub_status = get_subscription_status(session_user_id) if session_user_id else None
        raw_plan = sub_status.get("subscription_plan", "free") if sub_status else "free"
        plan_name = raw_plan.lower() if raw_plan else "free"
        limits = PLAN_LIMITS.get(plan_name, PLAN_LIMITS["free"])
        max_prompts = limits.get("max_prompts_per_project", 5)

        # Extract request data
        selected_cohorts_data = request.get("selected_cohorts", [])
        custom_cohorts_data = request.get("custom_cohorts", [])
        selected_llms = request.get("selected_llms", [])
        
        # Validation
        total_cohorts = len(selected_cohorts_data) + len(custom_cohorts_data)
        
        if total_cohorts == 0:
            raise HTTPException(status_code=400, detail="No cohorts selected")
        
        if total_cohorts > 5:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum 5 cohorts allowed. You selected {total_cohorts}."
            )
            
        # ─── Global Prompt Limit Check ───
        total_selected_prompts = 0
        for c in selected_cohorts_data:
            total_selected_prompts += len(c.get("selected_prompt_indices", []))
            total_selected_prompts += len(c.get("custom_prompts", []))
        
        for cc in custom_cohorts_data:
            total_selected_prompts += len(cc.get("prompts", []))
            
        if total_selected_prompts > max_prompts:
             raise HTTPException(
                status_code=400,
                detail=f"Prompt limit reached. Your {plan_name.capitalize()} allows total {max_prompts} prompts per project. You selected {total_selected_prompts}."
            )

        if not selected_llms:
            raise HTTPException(status_code=400, detail="No LLMs selected")
        
        logger.info(f" Processing {total_cohorts} cohorts ({len(selected_cohorts_data)} selected, {len(custom_cohorts_data)} custom)")
        
        # Get generated cohorts for session
        from services.database_manager import (
            get_cohorts_for_session,
            save_custom_cohort,
            save_custom_prompts,
            get_prompt_count_for_cohort
        )
        
        all_cohorts = get_cohorts_for_session(session_id)
        
        # Build final prompt list
        final_prompts = []
        cohort_details = []
        
        # Process SELECTED cohorts
        for cohort_data in selected_cohorts_data:
            cohort_index = cohort_data.get("cohort_index")
            selected_prompt_indices = cohort_data.get("selected_prompt_indices", [])
            custom_prompts = cohort_data.get("custom_prompts", [])
            
            # We've already checked the global total above
            total_prompts_in_cohort = len(selected_prompt_indices) + len(custom_prompts)
            
            if cohort_index < len(all_cohorts):
                cohort = all_cohorts[cohort_index]
                cohort_name = cohort['name']
                cohort_id = cohort['id']
                
                # Add selected generated prompts
                for prompt_idx in selected_prompt_indices:
                    if prompt_idx < len(cohort['prompts']):
                        prompt_text = cohort['prompts'][prompt_idx]['prompt_text']
                        final_prompts.append(prompt_text)
                
                # Add custom prompts if any
                if custom_prompts:
                    # Save custom prompts to database
                    save_custom_prompts(
                        session_id,
                        cohort_id,
                        custom_prompts,
                        start_index=len(cohort['prompts'])
                    )
                    final_prompts.extend(custom_prompts)
                
                cohort_details.append({
                    'type': 'selected',
                    'name': cohort_name,
                    'prompt_count': total_prompts_in_cohort
                })
                
                logger.info(f"   Selected cohort: {cohort_name} ({total_prompts_in_cohort} prompts)")
        
        # Process CUSTOM cohorts
        for idx, custom_cohort in enumerate(custom_cohorts_data):
            cohort_name = custom_cohort.get("name", f"Custom Topic {idx+1}")
            cohort_description = custom_cohort.get("description", "Custom user-defined cohort")
            custom_prompts = custom_cohort.get("prompts", [])
            
            # Already checked global total
            
            # Save custom cohort
            cohort_order = len(all_cohorts) + idx
            custom_cohort_id = save_custom_cohort(
                session_id,
                cohort_name,
                cohort_description,
                cohort_order
            )
            
            if custom_cohort_id > 0:
                # Save custom prompts
                save_custom_prompts(session_id, custom_cohort_id, custom_prompts)
                final_prompts.extend(custom_prompts)
                
                cohort_details.append({
                    'type': 'custom',
                    'name': cohort_name,
                    'prompt_count': len(custom_prompts)
                })
                
                logger.info(f"   Custom cohort: {cohort_name} ({len(custom_prompts)} prompts)")
        
        if not final_prompts:
            raise HTTPException(status_code=400, detail="No prompts to analyze")
        
        logger.info(f" Total prompts to execute: {len(final_prompts)}")
        logger.info(f"   Cohorts breakdown: {cohort_details}")
        
        # Continue analysis in background
        background_tasks.add_task(
            execute_prompts_workflow,
            session_id,
            final_prompts,
            selected_llms
        )
        
        # Update status in database
        update_session_status(session_id, status="running", progress=65)
        
        return {
            "session_id": session_id,
            "status": "executing",
            "total_prompts": len(final_prompts),
            "total_cohorts": total_cohorts,
            "cohort_details": cohort_details,
            "message": f"Executing {len(final_prompts)} prompts across {total_cohorts} cohorts"
        }
        
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error executing selected prompts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
        
@router.post("/api/analysis/validate-selection/{session_id}")
async def validate_selection(session_id: str, request: dict):
    """
    Validate user's cohort and prompt selection before execution.
    Returns validation errors if any.
    """
    try:
        # ─── Plan-Based Validation ───
        # Get session user to fetch plan limits
        session_response = supabase.table('analysis_sessions').select('user_id').eq('session_id', session_id).execute()
        user_id = session_response.data[0].get('user_id') if session_response.data else None
        
        sub_status = get_subscription_status(user_id) if user_id else None
        raw_plan = sub_status.get("subscription_plan", "free") if sub_status else "free"
        plan_name = raw_plan.lower() if raw_plan else "free"
        limits = PLAN_LIMITS.get(plan_name, PLAN_LIMITS["free"])
        max_prompts = limits.get("max_prompts_per_project", 5)

        selected_cohorts_data = request.get("selected_cohorts", [])
        custom_cohorts_data = request.get("custom_cohorts", [])
        
        errors = []
        
        # Check total cohorts
        total_cohorts = len(selected_cohorts_data) + len(custom_cohorts_data)
        if total_cohorts > 5:
            errors.append(f"Maximum 5 cohorts allowed. You selected {total_cohorts}.")
        
        if total_cohorts == 0:
            errors.append("Please select at least one cohort.")
        
        # ─── Global Prompt Limit Check ───
        total_selected_prompts = 0
        for c in selected_cohorts_data:
            total_selected_prompts += len(c.get("selected_prompt_indices", []))
            total_selected_prompts += len(c.get("custom_prompts", []))
        
        for cc in custom_cohorts_data:
            total_selected_prompts += len(cc.get("prompts", []))
            
        if total_selected_prompts > max_prompts:
             errors.append(f"Prompt limit reached. Your {plan_name.capitalize()} allows total {max_prompts} prompts per project. You selected {total_selected_prompts}.")

        # Check prompts per cohort (just check for 0)
        for idx, cohort_data in enumerate(selected_cohorts_data):
            selected_count = len(cohort_data.get("selected_prompt_indices", []))
            custom_count = len(cohort_data.get("custom_prompts", []))
            total = selected_count + custom_count
            
            if total == 0:
                errors.append(f"Cohort {idx+1} has no prompts selected.")
                                                                                    
        for idx, custom_cohort in enumerate(custom_cohorts_data):
            prompt_count = len(custom_cohort.get("prompts", []))
            
            if prompt_count == 0:
                errors.append(f"Custom cohort '{custom_cohort.get('name', 'Unnamed')}' has no prompts.")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "total_cohorts": total_cohorts,
            "max_cohorts": 5,
            "max_prompts": max_prompts
        }
        
    except Exception as e:
        logger.error(f"Error validating selection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/api/analysis/cohorts/{session_id}")
def get_analysis_cohorts(session_id: str, user_id: str = Depends(get_current_user)):
    """
    Get cohorts and prompts for prompt selection UI
    """
    try:
        from services.database_manager import get_cohorts_for_session
        
        # Verify this session belongs to the current user
        session_response = supabase.table('analysis_sessions').select('user_id').eq('session_id', session_id).execute()
        if not session_response.data or session_response.data[0].get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        cohorts = get_cohorts_for_session(session_id)
        
        # Return empty cohorts list if none found (not a 404, just empty)
        return {
            "session_id": session_id,
            "cohorts": cohorts or [],
            "total_prompts": sum(c['prompt_count'] for c in (cohorts or []))
        }
        
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error retrieving cohorts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# ============= BACKGROUND TASKS =============
async def execute_analysis_workflow(
    session_id: str,
    brand_name: str,
    product_name: Optional[str],
    industry: Optional[str],
    website_url: Optional[str],
    selected_llms: List[str],
    regenerate_prompts: bool = True,
    custom_keywords: Optional[List[str]] = None,
    custom_competitors: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    brand_aliases: Optional[List[str]] = None
):
    """   
    Cohort-based analysis workflow with custom competitor support
    Phase 1: Generate cohorts and prompts, Wait for user selection
    Phase 2: Execute selected prompts (handled by separate function)
    """
    try:
        # Step 1: Deep Research (15%)
        update_progress(session_id, 15, " Conducting market research...")
        logger.info(f"Step 1: Deep Research for {brand_name}")
        
        research_data = conduct_deep_research(
            brand_name, 
            product_name, 
            website_url, 
            industry,
            custom_competitors=custom_competitors
        )
        
        # Step 2: Keywords (25%)
        update_progress(session_id, 25, "🔍 Processing keywords...")
        logger.info("Step 2: Keyword Extraction")

        extracted_content = None

        if custom_keywords and len(custom_keywords) > 0:
            keywords = custom_keywords
            logger.info(f"✅ Using {len(keywords)} custom keywords: {keywords}")
        else:
            # ✅ NEW: Try to extract keywords from URL if provided
            if website_url:
                logger.info(f"🌐 No custom keywords provided, extracting from URL: {website_url}")
                url_keywords, extracted_content = await extract_keywords_from_url(website_url, brand_name, num_keywords=40)
                
                if url_keywords and len(url_keywords) > 0:
                    keywords = url_keywords
                    logger.info(f"✅ Extracted {len(keywords)} keywords from URL: {keywords}")
                else:
                    logger.info(f"⚠️ URL extraction failed, falling back to research-based extraction")
                    keywords = extract_keywords(
                        brand_name=brand_name, 
                        research_data=research_data, 
                        product_name=product_name, 
                        industry=industry,
                        num_keywords=20
                    )
                    logger.info(f"✅ Extracted {len(keywords)} keywords from research")
            else:
                logger.info(f"ℹ️ No URL provided, using research-based keyword extraction")
                keywords = extract_keywords(
                    brand_name=brand_name, 
                    research_data=research_data, 
                    product_name=product_name, 
                    industry=industry,
                    num_keywords=20
                )
                logger.info(f"✅ Extracted {len(keywords)} keywords from research")
            
        
        # Step 3: Generate Cohorts (35%)
        update_progress(session_id, 35, " Generating topic cohorts...")
        logger.info("Step 3: Cohort Generation")
        
        from services.cohort_generator import generate_cohorts
        
        num_cohorts = 5
        cohorts = generate_cohorts(
            brand_name=brand_name,
            research_context=research_data,
            keywords=keywords,
            industry=industry,
            num_cohorts=num_cohorts,
            product_name=product_name,
            extracted_content=extracted_content
        )
        
        if not cohorts:
            logger.warning("Cohort generation failed, using fallback")
            cohorts = [
                {'name': 'Brand Discovery', 'description': 'Finding and comparing brands', 'prompt_count': 3},
                {'name': 'Product Reviews', 'description': 'Reviews and ratings', 'prompt_count': 3},
                {'name': 'Buying Decisions', 'description': 'Purchase considerations', 'prompt_count': 3},
                {'name': 'Problem Solving', 'description': 'How-to and troubleshooting', 'prompt_count': 3},
                {'name': 'Industry Trends', 'description': 'Market trends and innovations', 'prompt_count': 3}
            ]
        save_session(session_id, brand_name, user_id, product_name, website_url, research_data, keywords, industry, project_id, brand_aliases)
        # Save cohorts to database
        from services.database_manager import save_cohorts, save_prompts_with_cohorts
        cohort_ids = save_cohorts(session_id, cohorts)
        
        logger.info(f" Generated {len(cohorts)} cohorts:")
        for cohort in cohorts:
            logger.info(f" {cohort['name']}: {cohort.get('prompt_count', 3)} prompts")
        
        # Step 4: Generate Prompts Per Cohort (50%)
        update_progress(session_id, 50, f" Generating prompts for {len(cohorts)} cohorts...")
        logger.info(f"Step 4: Generating cohort-specific prompts")
        
        from services.prompt_generator import generate_prompts_by_cohort
        
        all_prompts = []
        cohort_prompts_data = []
        
        for idx, (cohort, cohort_id) in enumerate(zip(cohorts, cohort_ids)):
            logger.info(f" Generating prompts for cohort: {cohort['name']}")
            
            try:
                
                cohort_prompts = generate_prompts_by_cohort(
                    brand_name=brand_name,
                    cohort=cohort,
                    research_context=research_data,
                    keywords=keywords,
                    industry=industry,
                    product_name=product_name
                )
                
                if cohort_prompts:
                    all_prompts.extend(cohort_prompts)
                    cohort_prompts_data.append({
                        'cohort_id': cohort_id,
                        'prompts': cohort_prompts
                    })
                    logger.info(f" Generated {len(cohort_prompts)} prompts")
                else:
                    logger.warning(f" No prompts generated for cohort: {cohort['name']}")
                    
            except Exception as e:
                logger.error(f" Error generating prompts for cohort {cohort['name']}: {str(e)}")
        
        if not all_prompts:
            raise Exception("Failed to generate any prompts across all cohorts")
        
        # Save prompts with cohort mapping
        save_prompts_with_cohorts(session_id, cohort_prompts_data)
        
        logger.info(f" Generated total {len(all_prompts)} prompts across {len(cohorts)} cohorts")
        
        # Save session metadata
        
        # Extract competitors
        if custom_competitors and len(custom_competitors) > 0:
            competitors_list = custom_competitors
            logger.info(f" Using {len(competitors_list)} custom competitors: {competitors_list}")
        else:
            competitors_list = research_data.get('competitors', [])
            logger.info(f" Extracted {len(competitors_list)} competitors from research: {competitors_list[:5]}")
        
        # Step 5: PAUSE HERE - Wait for user prompt selection
        update_progress(session_id, 60, " Prompts generated - awaiting your selection...")
        
        # ✅ FIX: Update DB instead of global dict
        update_session_status(
            session_id, 
            status="pending_selection",
            step="Ready for prompt selection"
        )
        
        # Note: We don't need to store cohorts/prompts in memory anymore 
        # because they are already saved to Supabase in Step 3 & 4.
        
        logger.info(f" Analysis paused at prompt selection stage for session {session_id}")
        logger.info(f"    Total prompts available: {len(all_prompts)}")
        logger.info(f"    User must now select prompts to continue analysis")
        
    except Exception as e:
        logger.error(f" Error in analysis workflow: {str(e)}", exc_info=True)
        # ✅ FIX: Update DB with error status
        update_session_status(
            session_id, 
            status="error", 
            error=str(e)
        )

async def execute_prompts_workflow(
    session_id: str,
    selected_prompts: List[str],
    selected_llms: List[str]
):
    """
    Phase 2 - Execute LLM analysis on user-selected prompts
    This runs after user selects prompts in the UI
    """
    try:
        logger.info(f" Starting execution of {len(selected_prompts)} selected prompts")
        logger.info(f"    LLMs: {selected_llms}")
        
        # Get session metadata
        from services.database_manager import get_session_results
        session_data = get_session_results(session_id)
        
        if not session_data or 'session' not in session_data:
            raise Exception(f"Session {session_id} not found in database")
        
        session_metadata = session_data.get('session')
        
        # Extract session details
        brand_name = session_metadata['brand_name']
        research_data = session_metadata.get('research_data', {})
        keywords = session_metadata.get('keywords', [])
        brand_aliases = session_metadata.get('brand_aliases', [])
        
        # ✅ FIX: Prefer competitors from the competitors table over research_data
        db_competitors = [c['competitor_name'] for c in session_data.get('competitors', [])]
        if db_competitors:
            competitors_list = db_competitors
        else:
            competitors_list = research_data.get('competitors', [])
        
        logger.info(f" Session context loaded:")
        logger.info(f" Brand: {brand_name}")
        logger.info(f" Keywords: {len(keywords)}")
        logger.info(f" Competitors: {len(competitors_list)}")
        
        # Step 6: Execute LLMs (70%)
        update_progress(session_id, 70, f" Running {len(selected_llms)} LLMs on {len(selected_prompts)} prompts...")
        logger.info(f"Step 6: Executing LLMs: {selected_llms}")
        
        llm_responses = execute_prompts_multi_llm_sync(
            prompts=selected_prompts,
            llms=selected_llms,
            brand_name=brand_name
        )
        
        if not llm_responses:
            raise Exception("No LLM responses received")
        
        logger.info(f" Received {len(llm_responses)} LLM responses")
        
        # Step 7: Scoring (85%)
        update_progress(session_id, 85, " Calculating visibility scores...")
        logger.info("Step 7: Scoring")
        
        scored_results = calculate_scores(llm_responses, brand_name, keywords, competitors=competitors_list)
        
        # ✅ FIX: Post-process aliases separately to ensure they only affect Brand Mention, not Position
        if brand_aliases and len(brand_aliases) > 0:
            import re
            logger.info(" Checking for brand aliases in responses with no main brand mention...")
            alias_patterns = [re.compile(re.escape(alias.strip()), re.IGNORECASE) for alias in brand_aliases if alias and alias.strip()]
            
            for result in scored_results:
                # Only check if main brand was NOT found (score is 0)
                if result['scores']['mention_score'] == 0:
                    response_text = result['response']
                    
                    found_alias = False
                    for pattern in alias_patterns:
                        if pattern.search(response_text):
                            found_alias = True
                            break
                    
                    if found_alias:
                        # Force update mention score and visibility ONLY
                        # Leave position_score, richness_score, keyword_score as 0 (calculated by main logic)
                        result['scores']['mention_score'] = 1
                        result['scores']['normalized_visibility'] = 100.0
                        result['scores']['brand_mention_score'] = 1
                        result['visibility_score'] = 100.0
                        
                        # Recalculate weighted score with the new mention score
                        # (1 * 0.3) + (0 * 0.4) + (0 * 0.2) + (0 * 0.1) = 0.3
                        # We use the existing function to be safe, or just do manual math since we know others are 0
                        from services.scoring_engine import calculate_weighted_score
                        new_weighted = calculate_weighted_score(
                            1, 
                            result['scores']['position_score'], 
                            result['scores']['richness_score'], 
                            result['scores']['keyword_score']
                        )
                        result['scores']['weighted_score'] = new_weighted
                        result['scores']['total_score'] = min(100, new_weighted)


        logger.info(f" Scored {len(scored_results)} results")
        
        # Save LLM responses WITH CITATIONS to database
        logger.info(" Saving LLM responses and citations to database...")
        saved_count = 0
        
        for result in scored_results:
            try:
                prompt_id = create_prompt_id(session_id, result.get('prompt_index', 0))
                
                # Extract citations and prompt from the original llm_responses
                matching_response = next(
                    (r for r in llm_responses 
                    if r.get('prompt_index') == result.get('prompt_index') 
                    and r.get('llm_name') == result.get('llm_name')),
                    None
                )
                
                citations = matching_response.get('citations', []) if matching_response else []
                prompt_text = matching_response.get('prompt', '') if matching_response else result.get('prompt', '')
                
                # Save LLM response with citations
                save_llm_response(
                    prompt_id, 
                    session_id, 
                    result.get('llm_name'),
                    prompt_text,
                    result.get('response', ''),
                    citations=citations
                )
                
                # Ensure visibility score is in scores dict
                scores_dict = result.get('scores', {})
                if 'normalized_visibility' not in scores_dict and 'visibility_score' in result:
                    scores_dict['normalized_visibility'] = result.get('visibility_score', 0)
                
                # Save scoring results
                save_scoring_result(
                    prompt_id, 
                    session_id, 
                    result.get('llm_name'),
                    scores_dict
                )
                
                saved_count += 1
                
            except Exception as e:
                logger.warning(f" Could not save response: {str(e)}")
        
        logger.info(f" Saved {saved_count}/{len(scored_results)} responses to database")
        
        # Step 8: Share of Voice (95%)
        update_progress(session_id, 95, " Computing share of voice...")
        logger.info("Step 8: Share of Voice")
        
        sov_data = None
        
        # Filter out the main brand from competitors list
        if competitors_list:
            cleaned_competitors = [
                c for c in competitors_list 
                if c.lower().strip() != brand_name.lower().strip()
            ]
            
            if cleaned_competitors:
                try:
                    logger.info(f"Found {len(cleaned_competitors)} competitors (excluding main brand): {cleaned_competitors}")
                    save_competitors(session_id, cleaned_competitors)
                    
                    # Calculate Share of Voice
                    sov_data = calculate_share_of_voice(scored_results, cleaned_competitors, brand_aliases)
                    
                    if sov_data and 'ranked_brands' in sov_data:
                        ranked_brands = sov_data.get('ranked_brands', [])
                        logger.info(f"Saving SOV for {len(ranked_brands)} brands")
                        
                        for rank_index, brand_data in enumerate(ranked_brands, 1):
                            try:
                                brand_name_sov = brand_data.get('brand_name', 'Unknown')
                                sov_scores_dict = {
                                    'normalized_visibility': float(brand_data.get('normalized_visibility', 0)),
                                    'average_positioning': float(brand_data.get('average_positioning', 0)),
                                    'weighted_score': float(brand_data.get('weighted_score', 0)),
                                    'total_mentions': int(brand_data.get('total_mentions', 0))
                                }
                                
                                save_share_of_voice(
                                    session_id,
                                    brand_name_sov,
                                    sov_scores_dict,
                                    rank_index
                                )
                                logger.info(f"  âœ” Saved SOV for {brand_name_sov} (Rank {rank_index})")
                            except Exception as e:
                                logger.warning(f"Could not save SOV for {brand_data.get('brand_name', 'Unknown')}: {str(e)}")
                        
                        logger.info(f" Share of Voice saved: {len(ranked_brands)} brands")
                    else:
                        logger.warning(" ï¸ Share of Voice missing 'ranked_brands' key")
                        
                except Exception as e:
                    logger.error(f" Error calculating Share of Voice: {str(e)}", exc_info=True)
                    sov_data = None
            else:
                logger.info(" ï¸ Competitor list empty after removing main brand.")
                sov_data = None
        else:
            logger.info(" ï¸ No competitors found - skipping Share of Voice")
            sov_data = None
        
        # Aggregate results
        summary = aggregate_results(scored_results)
        save_brand_score_summary(session_id, brand_name, summary)
        
        # Step 9: Complete (100%)
        update_progress(session_id, 100, " Analysis complete!")
        
        send_signal("prompts_executed", session_id, {
            "brand": brand_name,
            "prompts_count": len(selected_prompts),
            "llms_count": len(selected_llms)
        })
        
        # ✅ FIX: Update DB to completed
        update_session_status(
            session_id, 
            status="completed",
            progress=100,
            step="Analysis complete!"
        )
        
        logger.info(f" Analysis completed for {brand_name}")
        logger.info(f"   - Selected Prompts: {len(selected_prompts)}")
        logger.info(f"   - LLM Responses: {len(llm_responses)}")
        logger.info(f"   - Scored Results: {len(scored_results)}")
        logger.info(f"   - Share of Voice: {'Yes' if sov_data else 'No'}")
        
    except Exception as e:
        logger.error(f" Error in prompt execution workflow: {str(e)}", exc_info=True)
        # ✅ FIX: Update DB with error status
        update_session_status(
            session_id, 
            status="error", 
            error=str(e)
        )

def update_progress(session_id: str, progress: int, step: str):
    """
    Update analysis progress in the database (Stateless)
    """
    # ✅ FIX: Use DB function instead of global dict
    update_session_status(
        session_id, 
        progress=progress, 
        step=step,
        status="running" 
    )
    logger.info(f"[{session_id}] {progress}% - {step}")
from services.database_manager import get_brand_visibility_history

@router.get("/api/brand-history/{brand_name}")
async def get_brand_history(brand_name: str, user_id: str = Depends(get_current_user)):
    """
    Get brand visibility history across all analysis dates (scoped to current user)
    """
    try:
        history = get_brand_visibility_history(brand_name, user_id)
        
        if not history:
            raise HTTPException(
                status_code=404,
                detail=f"No analysis history found for brand: {brand_name} (user)")
        
        return {
            "brand_name": brand_name,
            "history": history,
            "total_analyses": len(history)
        }
    except Exception as e:
        logger.error(f"Error fetching brand history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/api/brands")
def get_all_brands(user_id: str = Depends(get_current_user)):
    """Get all unique brands for dropdown selector"""
    try:
        brands = get_all_unique_brands()
        return {"brands": brands}
    except Exception as e:
        logger.error(f"Error fetching brands: {str(e)}")
        return {"brands": [], "error": str(e)}
    
@router.get("/api/recent-analyses-by-brand/{brand_name}")
def get_recent_analyses_by_brand(brand_name: str, user_id: str = Depends(get_current_user), limit: int = 20):
    """Get recent analyses for a specific brand"""
    try:
        sessions = get_recent_sessions_by_brand(brand_name, limit)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Error fetching analyses for brand {brand_name}: {str(e)}")
        return {"sessions": [], "error": str(e)}
@router.get("/api/visibility-history/brand-product/{brand_name}/{product_name}")
def get_brand_product_history(brand_name: str, product_name: str, user_id: str = Depends(get_current_user)):
    """Get visibility history for brand + product combination (scoped to current user)"""
    try:
        history = get_product_specific_visibility_history(brand_name, product_name, user_id)
        return {"history": history}
    except Exception as e:
        logger.error(f"Error fetching product visibility history: {str(e)}")
        return {"history": [], "error": str(e)}
    
def get_llm_names_from_session(session_id: str) -> List[str]:
    """Get LLM names used in a session - using Supabase"""
    try:
        response = supabase.table('llm_responses').select('llm_name').eq('session_id', session_id).execute()
        llm_names = list(set(row['llm_name'] for row in response.data))
        return llm_names
    except Exception as e:
        logger.error(f"Error getting LLM names: {str(e)}")
        return []
    
@router.post("/api/reanalyze-with-same-prompts/{session_id}")
async def reanalyze_with_same_prompts(
    session_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Re-analyze with the same prompts from a previous session"""
    try:
        # Get original session details
        original_session = get_session_results(session_id)
        if not original_session:
            raise HTTPException(status_code=404, detail="Original session not found")
        
        session_metadata = original_session.get('session')
        if not session_metadata:
            raise HTTPException(status_code=404, detail="Original session metadata not found")
        
        # Extract metadata
        brand_name = session_metadata['brand_name']
        product_name = session_metadata.get('product_name')
        website_url = session_metadata.get('website_url')
        research_data = session_metadata.get('research_data', {})
        research_data = session_metadata.get('research_data', {})
        keywords = session_metadata.get('keywords', [])
        brand_aliases = session_metadata.get('brand_aliases', [])
        
        # Get prompts and LLMs
        prompts = get_saved_prompts_for_analysis(session_id)
        llm_names = get_llm_names_from_session(session_id)
        
        if not prompts:
            raise HTTPException(status_code=400, detail="No prompts found for this session")
        if not llm_names:
            logger.warning("No LLM names found in original session, defaulting to Claude")
            llm_names = ['Claude']
        
        # Create new session ID
        new_session_id = create_session_id(brand_name, product_name)
        
        # Save new session (use keyword args to ensure correct mapping)
        save_session(
            new_session_id,
            brand_name,
            user_id=user_id,
            product_name=product_name,
            website_url=website_url,
            research_data=research_data,
            keywords=keywords,
            industry=session_metadata.get('industry'),
            project_id=session_metadata.get('project_id'),
            brand_aliases=brand_aliases
        )
        
        # Initialize progress tracking in database
        update_session_status(new_session_id, status="running", progress=0, step="Initializing Re-analysis...")
        
        # ✅ NEW: Carry forward competitors
        duplicate_session_competitors(session_id, new_session_id)
        
        # Run analysis with saved prompts
        background_tasks.add_task(
            run_analysis_with_saved_prompts,
            new_session_id,
            brand_name,
            prompts,
            llm_names,
            research_data,
            keywords,
            brand_aliases
        )
        
        return {
            "new_session_id": new_session_id,
            "message": "Re-analysis started with same prompts",
            "status": "processing"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in re-analysis: {str(e)}", exc_info=True)
        if 'new_session_id' in locals():
            update_session_status(new_session_id, status="error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
async def run_analysis_with_saved_prompts(
    session_id: str,
    brand_name: str,
    prompts: list,
    llm_names: list,
    research_data: Optional[dict] = None,
    keywords: Optional[list] = None,
    brand_aliases: Optional[list] = None
):
    """Execute analysis using pre-saved prompts"""
    update_progress(session_id, 10, " Re-executing LLMs with saved prompts...")
    try:
        if not research_data:
            research_data = {}
        if not keywords:
            keywords = []
            
        competitors_list = [] # Will check database first
        product_name = research_data.get('product_name')
        
        # If no competitors in research_data, check database
        if not competitors_list:
            logger.warning(" ï¸ No competitors in research_data, checking database...")
            try:
                response = supabase.table('competitors').select('competitor_name').eq('session_id', session_id).order('rank').limit(10).execute()
                
                if response.data:
                    competitors_list = [row['competitor_name'] for row in response.data]
                    logger.info(f" Found {len(competitors_list)} competitors from database: {competitors_list}")
                else:
                    logger.warning(f" ï¸ No competitors found in database for session: {session_id}")
            except Exception as e:
                logger.error(f"Error querying database for competitors: {str(e)}")
        if not competitors_list:
            competitors_list = research_data.get('competitors', [])
            
        logger.info(f" Final data - Competitors: {len(competitors_list)}, Keywords: {len(keywords)}")
        # Step 1: Execute prompts with multiple LLMs
        llm_responses = execute_prompts_multi_llm_sync(
            prompts=prompts,
            llms=llm_names,
            brand_name=brand_name
        )
        if not llm_responses:
            raise Exception("No LLM responses received in re-analysis")
        update_progress(session_id, 60, " Recalculating scores...")
        # Step 2: Calculate scores
        scored_results = calculate_scores(llm_responses, brand_name, keywords, competitors=competitors_list)

        # ✅ FIX: Post-process aliases separately to ensure they only affect Brand Mention, not Position
        if brand_aliases and len(brand_aliases) > 0:
            import re
            logger.info(" Checking for brand aliases in responses with no main brand mention...")
            alias_patterns = [re.compile(re.escape(alias.strip()), re.IGNORECASE) for alias in brand_aliases if alias and alias.strip()]
            
            for result in scored_results:
                # Only check if main brand was NOT found (score is 0)
                if result['scores']['mention_score'] == 0:
                    response_text = result['response']
                    
                    found_alias = False
                    for pattern in alias_patterns:
                        if pattern.search(response_text):
                            found_alias = True
                            break
                    
                    if found_alias:
                        # Force update mention score and visibility ONLY
                        # Leave position_score, richness_score, keyword_score as 0 (calculated by main logic)
                        result['scores']['mention_score'] = 1
                        result['scores']['normalized_visibility'] = 100.0
                        result['scores']['brand_mention_score'] = 1
                        result['visibility_score'] = 100.0
                        
                        # Recalculate weighted score with the new mention score
                        # (1 * 0.3) + (0 * 0.4) + (0 * 0.2) + (0 * 0.1) = 0.3
                        # We use the existing function to be safe, or just do manual math since we know others are 0
                        from services.scoring_engine import calculate_weighted_score
                        new_weighted = calculate_weighted_score(
                            1, 
                            result['scores']['position_score'], 
                            result['scores']['richness_score'], 
                            result['scores']['keyword_score']
                        )
                        result['scores']['weighted_score'] = new_weighted
                        result['scores']['total_score'] = min(100, new_weighted)
        # Step 3: Save LLM responses and scores
        for result in scored_results:
            prompt_index = result.get('prompt_index', 0)
            prompt_id = create_prompt_id(session_id, prompt_index)
            matching_response = next(
                (r for r in llm_responses
                if r.get('prompt_index') == prompt_index
                and r.get('llm_name') == result.get('llm_name')),
                None
            )
            citations = matching_response.get('citations', []) if matching_response else []
            prompt_text = matching_response.get('prompt', '') if matching_response else result.get('prompt', '')
            save_llm_response(
                prompt_id,
                session_id,
                result.get('llm_name'),
                prompt_text,
                result.get('response', ''),
                citations=citations
            )
            save_scoring_result(
                prompt_id,
                session_id,
                result.get('llm_name'),
                result.get('scores', {})
            )
        logger.info(f" Saving {len(prompts)} prompts for re-analysis session {session_id}")
        try:
            from services.database_manager import save_prompts_to_db
            save_prompts_to_db(brand_name, prompts, product_name)
            logger.info(f" Prompts saved successfully for brand: {brand_name}")
        except Exception as e:
            logger.warning(f"Could not save prompts for re-analysis: {str(e)}")
        update_progress(session_id, 80, " Computing Share of Voice...")
        # Step 4: Share of Voice
        if competitors_list:
            try:
                save_competitors(session_id, competitors_list)
                logger.info(f" Saved {len(competitors_list)} competitors for session {session_id}")
                sov_data = calculate_share_of_voice(scored_results, competitors_list, brand_aliases)
                if sov_data and 'ranked_brands' in sov_data:
                    logger.info(f" Saving Share of Voice for {len(sov_data['ranked_brands'])} brands in session {session_id}")
                    for rank_index, brand_data in enumerate(sov_data['ranked_brands'], 1):
                        sov_scores_dict = {
                            'normalized_visibility': float(brand_data.get('normalized_visibility', 0)),
                            'average_positioning': float(brand_data.get('average_positioning', 0)),
                            'weighted_score': float(brand_data.get('weighted_score', 0)),
                        }
                        save_share_of_voice(
                            session_id,
                            brand_data.get('brand_name', 'Unknown'),
                            sov_scores_dict,
                            rank_index
                        )
                    logger.info(f" Share of Voice calculation complete for session {session_id}")
                else:
                    logger.warning(f" ï¸ No SOV data generated for session {session_id}")
            except Exception as e:
                logger.error(f" Error calculating Share of Voice in re-analysis: {str(e)}", exc_info=True)
        else:
            logger.info(f"â„¹ï¸ No competitors provided for session {session_id} - skipping Share of Voice calculation")
        # Step 5: Aggregate results
        update_progress(session_id, 90, " Aggregating results...")
        summary = aggregate_results(scored_results)
        save_brand_score_summary(session_id, brand_name, summary)
        # Step 6: Complete
        update_progress(session_id, 100, " Re-analysis complete!")
        logger.info(f" Re-analysis completed for session {session_id}")
    except Exception as e:
        logger.error(f" Error during re-analysis execution for {session_id}: {str(e)}", exc_info=True)
        # ✅ FIX: Update DB
        update_session_status(session_id, status="error", error=str(e))
        
@router.get("/api/same-prompts-history/{session_id}")
def get_same_prompts_history(session_id: str, user_id: str = Depends(get_current_user)):
    """Get visibility history for when same prompts are analyzed again"""
    try:
        from services.database_manager import get_session_results_aggregated
        
        original_results = get_session_results_aggregated(session_id)
        if not original_results:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Verify this session belongs to the current user
        session_user_id = original_results.get('session_metadata', {}).get('user_id')
        if session_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        brand_name = original_results.get('brand_name')
        product_name = original_results.get('product_name', '')
        
        if not brand_name:
            logger.error(f"No brand_name found in session {session_id}")
            return {"history": [], "error": "Brand name not found"}
        
        logger.info(f" Fetching same prompts history for brand: {brand_name}, session: {session_id}")
        
        # Get saved prompts
        prompts = get_saved_prompts_for_analysis(session_id)
        if not prompts:
            logger.info(f"No prompts found for session {session_id}")
            return {"history": [], "message": "No prompts found"}
        
        logger.info(f"Found {len(prompts)} prompts for matching")
        
        # Get history
        history = get_visibility_history_for_same_prompts(brand_name, product_name, prompts)
        
        logger.info(f" Returning {len(history)} data points for same prompts history")
        return {"history": history}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching same prompts history: {str(e)}", exc_info=True)
        return {"history": [], "error": str(e)}

@router.post("/api/analysis/{session_id}/update-competitors")
async def update_competitors_and_recalculate(
    session_id: str,
    request: CompetitorUpdateRequest,
    user_id: str = Depends(get_current_user)
):
    try:
        # 1. Update Competitors
        new_competitors = list(set([c.strip() for c in request.competitors if c.strip()]))
        replace_session_competitors(session_id, new_competitors)
        
        # 2. Get Session Data
        session_results = get_session_results(session_id)
        if not session_results: raise HTTPException(status_code=404, detail="Session not found")
        
        # 3. Clear Old Metrics & Re-Score
        clear_session_metrics(session_id)
        
        formatted_responses = []
        for row in session_results.get('responses', []):
            formatted_responses.append({
                'prompt': row.get('prompt_text'),
                'response': row.get('response_text'),
                'llm_name': row.get('llm_name'),
                'prompt_index': int(row.get('prompt_id').split('_')[-1]) if '_' in row.get('prompt_id') else 0,
                'citations': row.get('citations', [])
            })

        scored_results = calculate_scores(
            formatted_responses, 
            session_results['session']['brand_name'], 
            session_results['session']['keywords'], 
            competitors=new_competitors
        )

        # 4. Save New Scores
        for result in scored_results:
            prompt_id = create_prompt_id(session_id, result.get('prompt_index', 0))
            save_scoring_result(prompt_id, session_id, result.get('llm_name'), result.get('scores', {}))

        # 5. Recalculate Share of Voice
        if new_competitors:
             sov_data = calculate_share_of_voice(scored_results, new_competitors)
             if sov_data and 'ranked_brands' in sov_data:
                for rank, brand in enumerate(sov_data['ranked_brands'], 1):
                    save_share_of_voice(
                        session_id, brand['brand_name'], 
                        {'normalized_visibility': brand['normalized_visibility'], 
                         'average_positioning': brand['average_positioning'], 
                         'weighted_score': brand['weighted_score']}, 
                        rank
                    )

        # 6. Update Summary
        summary = aggregate_results(scored_results)
        save_brand_score_summary(session_id, session_results['session']['brand_name'], summary)
        
        return {"success": True, "competitor_count": len(new_competitors)}

    except Exception as e:
        logger.error(f"Error in recalculation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
