import os
import logging
from typing import Optional, Callable, Any, Dict
from functools import wraps
from datetime import datetime

try:
    from paid import Paid
except ImportError:
    Paid = None

logger = logging.getLogger(__name__)

# Initialize Paid client globally
PAID_TOKEN = "ffca655e-5dc3-4f7b-82a6-3a7842b04cbe"

if Paid is None:
    logger.warning("⚠️ 'paid' package not installed. Install with: pip install paid")
    paid_client = None
else:
    paid_client = Paid(token=PAID_TOKEN) if PAID_TOKEN else None


def initialize_paid_tracing():
    """Initialize Paid.ai tracing once at startup"""
    if paid_client:
        try:
            paid_client.initialize_tracing()
            logger.info("✅ Paid.ai cost tracking initialized")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Paid.ai initialization failed: {str(e)}")
            return False
    else:
        logger.warning("⚠️ PAID_TOKEN not set or 'paid' not installed - cost tracking disabled")
        return False


def trace_api_call(
    external_customer_id: str,
    external_agent_id: str,
    operation_name: str
):
    """
    Decorator for tracing API calls to Paid.ai
    
    Usage:
        @trace_api_call(
            external_customer_id="user-123",
            external_agent_id="keyword-extractor",
            operation_name="mistral_keywords"
        )
        def extract_keywords(query):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not paid_client:
                # If Paid not configured, just run the function
                return func(*args, **kwargs)
            
            try:
                result = paid_client.trace(
                    external_customer_id=external_customer_id,
                    external_agent_id=external_agent_id,
                    fn=lambda: func(*args, **kwargs)
                )
                logger.debug(f"✅ {operation_name} traced to Paid.ai")
                return result
            except Exception as e:
                logger.warning(f"⚠️ Paid.ai tracing failed for {operation_name}: {str(e)}")
                # Fallback: still run the function without tracking
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def manual_trace(
    operation_fn: Callable,
    external_customer_id: str,
    external_agent_id: str,
    metadata: Optional[Dict] = None
) -> Any:
    """
    Manually trace a function call to Paid.ai
    
    Usage:
        result = manual_trace(
            operation_fn=lambda: anthropic_client.messages.create(...),
            external_customer_id="user-123",
            external_agent_id="claude-agent",
            metadata={"model": "claude-3-sonnet", "brand": "Nike"}
        )
    """
    if not paid_client:
        # If Paid not configured, just run the operation
        return operation_fn()
    
    try:
        trace_kwargs = {
            "external_customer_id": external_customer_id,
            "external_agent_id": external_agent_id,
            "fn": operation_fn
        }
        
        # Add metadata if provided
        if metadata:
            trace_kwargs["metadata"] = metadata
        
        result = paid_client.trace(**trace_kwargs)
        return result
    except Exception as e:
        logger.warning(f"⚠️ Paid.ai manual trace failed: {str(e)}")
        # Fallback: still run the operation
        return operation_fn()


async def manual_trace_async(
    operation_fn: Callable,
    external_customer_id: str,
    external_agent_id: str,
    metadata: Optional[Dict] = None
) -> Any:
    """
    Async wrapper for tracing API calls
    
    Usage:
        import asyncio
        result = await asyncio.to_thread(
            manual_trace_async,
            operation_fn=async_operation,
            external_customer_id="user-123",
            external_agent_id="async-agent"
        )
    """
    if not paid_client:
        if callable(operation_fn) and hasattr(operation_fn, '__await__'):
            return await operation_fn()
        return operation_fn()
    
    try:
        if callable(operation_fn) and hasattr(operation_fn, '__await__'):
            # If it's an async function, we need to handle it differently
            # For now, wrap it in a sync lambda that the paid client can handle
            result = paid_client.trace(
                external_customer_id=external_customer_id,
                external_agent_id=external_agent_id,
                fn=operation_fn
            )
            return result
        else:
            return paid_client.trace(
                external_customer_id=external_customer_id,
                external_agent_id=external_agent_id,
                fn=operation_fn
            )
    except Exception as e:
        logger.warning(f"⚠️ Paid.ai async trace failed: {str(e)}")
        if callable(operation_fn) and hasattr(operation_fn, '__await__'):
            return await operation_fn()
        return operation_fn()


def get_cost_tracking_metadata(session_id: str, user_id: str) -> Dict:
    """
    Returns metadata structure for tracking costs per session
    
    Usage:
        cost_meta = get_cost_tracking_metadata("session-123", "user-456")
        # Returns:
        # {
        #     "session_id": "session-123",
        #     "user_id": "user-456",
        #     "timestamp": "2025-01-08T16:04:00.000000",
        #     "costs": {...}
        # }
    """
    return {
        "session_id": session_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat(),
        "costs": {
            "anthropic": 0.0,
            "openai": 0.0,
            "mistral": 0.0,
            "google_ai": 0.0,
            "perplexity": 0.0,
            "tavily": 0.0,
            "total": 0.0
        }
    }


def create_trace_metadata(
    brand_name: str,
    model: str,
    api_type: str,
    additional_info: Optional[Dict] = None
) -> Dict:
    """
    Create detailed metadata for a trace call
    
    Usage:
        metadata = create_trace_metadata(
            brand_name="Nike",
            model="claude-3-sonnet",
            api_type="llm",
            additional_info={"tokens": 1500, "industry": "sports"}
        )
    """
    meta = {
        "brand": brand_name,
        "model": model,
        "api_type": api_type,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if additional_info:
        meta.update(additional_info)
    
    return meta


# Common agent IDs (use these for consistency)
AGENT_IDS = {
    "keyword_extraction": "keyword-extractor-mistral",
    "prompt_generation": "prompt-generator-claude",
    "cohort_generation": "cohort-generator-agent",
    "deep_research": "deep-research-tavily",
    "claude_executor": "claude-executor",
    "chatgpt_executor": "chatgpt-executor",
    "perplexity_executor": "perplexity-executor",
    "gemini_executor": "gemini-executor",
    "google_ai_overview": "google-ai-overview",
    "url_keyword_extractor": "url-keyword-extractor"
}

# Common customer ID patterns (format: {service}-{brand}-{session})
def make_customer_id(service: str, brand: str = "general", session: str = None) -> str:
    """Create a standardized customer ID"""
    if session:
        return f"{service}-{brand}-{session}".lower().replace(" ", "-")
    return f"{service}-{brand}".lower().replace(" ", "-")
