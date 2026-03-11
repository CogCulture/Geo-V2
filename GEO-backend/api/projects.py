import os
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from api.auth import get_current_user
from services.database_manager import (
    get_subscription_status,
    create_project,
    get_user_projects,
    get_project_by_id,
    update_project,
    delete_project,
    add_monitored_prompts,
    get_monitored_prompts,
    add_monitored_competitors,
    get_monitored_competitors,
    get_project_dashboard_metrics
)
from api.config import PLAN_LIMITS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["Projects"])

class ProjectCreateRequest(BaseModel):
    name: str
    website_url: Optional[str] = None
    industry: Optional[str] = None
    update_frequency: str = "24h"
    initial_prompts: Optional[List[str]] = []
    initial_competitors: Optional[List[str]] = []

class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    website_url: Optional[str] = None
    industry: Optional[str] = None
    update_frequency: Optional[str] = None
    is_active: Optional[bool] = None

@router.post("")
async def create_new_project(request: ProjectCreateRequest, user_id: str = Depends(get_current_user)):
    """Create a new project and initialize its monitored entities"""
    try:
        # ─── 1. Limit Enforcement ───────────────────────────────────────────
        # Get subscription status to find limits
        sub_status = get_subscription_status(user_id)
        plan_name = "free"
        if sub_status and sub_status.get("is_active"):
            raw_plan = sub_status.get("subscription_plan", "free")
            plan_name = raw_plan.lower() if raw_plan else "free"
            
        limits = PLAN_LIMITS.get(plan_name, PLAN_LIMITS["free"])
        
        # Check existing project count
        existing_projects = get_user_projects(user_id)
        if len(existing_projects) >= limits["max_projects"]:
            raise HTTPException(
                status_code=403,
                detail=f"Project limit reached for your {plan_name.capitalize()}. (Max: {limits['max_projects']})"
            )
            
        # Check initial prompts count
        prompts_to_add = request.initial_prompts or []
        if len(prompts_to_add) > limits["max_prompts_per_project"]:
            raise HTTPException(
                status_code=403,
                detail=f"Prompt limit per project exceeded. Your plan allows {limits['max_prompts_per_project']} prompts per project."
            )

        # ─── 2. Creation ───────────────────────────────────────────────────
        # 1. Create the project
        project = create_project(
            user_id=user_id,
            name=request.name,
            website_url=request.website_url,
            industry=request.industry,
            update_frequency=request.update_frequency
        )
        
        if not project:
            raise HTTPException(status_code=500, detail="Failed to create project")
        
        project_id = project['id']
        
        # 2. Add initial monitored prompts if provided
        if prompts_to_add:
            add_monitored_prompts(project_id, prompts_to_add)
            
        # 3. Add initial monitored competitors if provided
        if request.initial_competitors:
            add_monitored_competitors(project_id, request.initial_competitors)
            
        return {
            "status": "success",
            "message": "Project created successfully",
            "project": project
        }
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
async def list_projects(user_id: str = Depends(get_current_user)):
    """List all projects for the user"""
    try:
        projects = get_user_projects(user_id)
        return {"projects": projects}
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}")
async def get_project_details(project_id: str, user_id: str = Depends(get_current_user)):
    """Get detailed project info including monitored entities"""
    try:
        project = get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
            
        if project['user_id'] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
            
        prompts = get_monitored_prompts(project_id)
        competitors = get_monitored_competitors(project_id)
        
        return {
            "project": project,
            "monitored_prompts": prompts,
            "monitored_competitors": competitors
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{project_id}")
async def update_project_settings(project_id: str, request: ProjectUpdateRequest, user_id: str = Depends(get_current_user)):
    """Update project configuration"""
    try:
        project = get_project_by_id(project_id)
        if not project or project['user_id'] != user_id:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
            
        update_data = request.dict(exclude_unset=True)
        if update_project(project_id, update_data):
            return {"status": "success", "message": "Project updated"}
        raise HTTPException(status_code=500, detail="Update failed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{project_id}")
async def delete_user_project(project_id: str, user_id: str = Depends(get_current_user)):
    """Delete a project and all its data"""
    try:
        project = get_project_by_id(project_id)
        if not project or str(project['user_id']) != str(user_id):
            raise HTTPException(status_code=404, detail="Project not found or access denied")
            
        if delete_project(project_id):
            return {"status": "success", "message": "Project deleted successfully"}
        raise HTTPException(status_code=500, detail="Delete failed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/metrics")
async def get_project_metrics(project_id: str, days: int = Query(30), user_id: str = Depends(get_current_user)):
    """Get historical metrics for the project dashboard"""
    try:
        project = get_project_by_id(project_id)
        if not project or project['user_id'] != user_id:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
            
        metrics = get_project_dashboard_metrics(project_id, days)
        return {"metrics": metrics}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
