import logging
from datetime import datetime
from typing import Dict
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from api.auth import get_current_user
from services.llms_txt_generator import generate_llms_txt
from services.tracking import send_signal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llms-txt", tags=["LLMs Txt"])

class LlmsTxtRequest(BaseModel):
    url: str

# In-memory store for llms.txt generation tasks
llms_txt_tasks: Dict = {}

@router.post("/generate")
async def generate_llms_txt_endpoint(request: LlmsTxtRequest, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    """Start llms.txt generation for a website URL"""
    try:
        if not request.url or not request.url.strip():
            raise HTTPException(status_code=400, detail="URL is required")
        
        # Create a unique task ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # Initialize task state
        llms_txt_tasks[task_id] = {
            "status": "running",
            "progress": 0,
            "step": "Initializing...",
            "url": request.url,
            "result": None,
            "error": None,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat()
        }
        
        def progress_callback(progress: int, step: str):
            if task_id in llms_txt_tasks:
                llms_txt_tasks[task_id]["progress"] = progress
                llms_txt_tasks[task_id]["step"] = step
        
        def run_generation(tid: str, url: str, uid: str):
            try:
                result = generate_llms_txt(url, progress_callback=progress_callback, user_id=uid)
                if tid in llms_txt_tasks:
                    llms_txt_tasks[tid]["status"] = "completed"
                    llms_txt_tasks[tid]["progress"] = 100
                    llms_txt_tasks[tid]["step"] = "Generation complete!"
                    llms_txt_tasks[tid]["result"] = result
                # Signal success to Paid.ai
                send_signal("llms_txt_generated", tid, {
                    "url": url,
                    "domain": result.get("domain", ""),
                    "pages_included": result.get("stats", {}).get("pages_included", 0),
                })
            except Exception as e:
                logger.error(f"llms.txt generation error: {str(e)}")
                if tid in llms_txt_tasks:
                    llms_txt_tasks[tid]["status"] = "error"
                    llms_txt_tasks[tid]["error"] = str(e)
                    llms_txt_tasks[tid]["step"] = f"Error: {str(e)}"
                send_signal("llms_txt_error", tid, {"url": url, "error": str(e)})
        
        background_tasks.add_task(run_generation, task_id, request.url.strip(), user_id)
        
        send_signal("llms_txt_started", task_id, {"url": request.url, "user_id": user_id})
        logger.info(f"🚀 llms.txt generation started for {request.url} (Task: {task_id}) by user {user_id}")
        
        return {
            "status": "success",
            "task_id": task_id,
            "message": "llms.txt generation started"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting llms.txt generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_llms_txt_status(task_id: str, user_id: str = Depends(get_current_user)):
    """Get the status of an llms.txt generation task"""
    task = llms_txt_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify ownership
    if task.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    response = {
        "status": task["status"],
        "progress": task["progress"],
        "step": task["step"],
        "url": task["url"],
    }
    
    if task["status"] == "completed" and task["result"]:
        response["result"] = task["result"]
    elif task["status"] == "error":
        response["error"] = task["error"]
    
    return response
