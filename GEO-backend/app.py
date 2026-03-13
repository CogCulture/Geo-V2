import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.database_manager import init_database

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= PAID.AI & OPENTELEMETRY =============
PAID_API_KEY = os.environ.get("PAID_API_KEY")

try:
    from paid import Paid
    paid_client = Paid(token=PAID_API_KEY)
    logger.info("✅ Paid.ai client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Paid.ai client: {str(e)}")
    paid_client = None

# Initialize opentelemetry for Paid.ai Traces
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    
    # Import specific instrumentors for your LLMs
    from openinference.instrumentation.anthropic import AnthropicInstrumentor
    from openinference.instrumentation.openai import OpenAIInstrumentor
    from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

    if PAID_API_KEY:
        # MUST use the dedicated collector URL and the x-api-key header
        endpoint = "https://collector.agentpaid.io:4318/v1/traces"
        headers = {
            "x-api-key": PAID_API_KEY,
            "Authorization": f"Bearer {PAID_API_KEY}" # Sent as a fallback
        }

        provider = TracerProvider()
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, headers=headers))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        # Boot the auto-instrumentation
        AnthropicInstrumentor().instrument()
        OpenAIInstrumentor().instrument()
        GoogleGenAIInstrumentor().instrument()
        
        logger.info("✅ Paid.ai OpenTelemetry tracking initialized for LLMs (Claude, ChatGPT, Gemini)")
    else:
        logger.warning("❌ PAID_API_KEY not found, skipping OpenTelemetry configuration.")
except Exception as otel_err:
    logger.error(f"❌ Failed to initialize OpenTelemetry: {otel_err}")

# FastAPI app
app = FastAPI(
    title="Brand Visibility Analyzer API",
    description="Backend API for brand visibility analysis",
    version="1.0.0"
)

# ============= CORS MIDDLEWARE =============
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# Support multiple origins via comma-separated ALLOWED_ORIGINS env var
extra_origins = os.environ.get("ALLOWED_ORIGINS", "")
extra_origins_list = [o.strip() for o in extra_origins.split(",") if o.strip()]

origins = list(set([
    "http://localhost:3000",
    FRONTEND_URL,
    *extra_origins_list
]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= ROUTERS =============
from api.auth import router as auth_router
from api.payments import router as payments_router
from api.projects import router as projects_router
from api.analysis import router as analysis_router
from api.llms_txt import router as llms_txt_router

app.include_router(auth_router)
app.include_router(payments_router)
app.include_router(projects_router)
app.include_router(analysis_router)
app.include_router(llms_txt_router)

# ============= ROOT ENDPOINTS =============
@app.get("/health")
def health_check():
    """Check if API is running"""
    return {
        "status": "online",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

# ============= RUN SERVER =============
if __name__ == "__main__":
    import uvicorn
    
    # Dynamic configuration with production defaults
    host = os.environ.get("BACKEND_HOST", "0.0.0.0")
    port = int(os.environ.get("BACKEND_PORT", 8000))
    is_development = os.environ.get("ENVIRONMENT", "production").lower() != "production"
    is_reload = os.environ.get("RELOAD", "false").lower() == "true"
    
    # Only initialize SQLite if not using Supabase, though we assume Supabase is configured
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    if not SUPABASE_URL:
        init_database()

    print("\n" + "="*60)
    print(f" BRAND VISIBILITY ANALYZER - BACKEND ({host}:{port})")
    print("="*60)
    
    uvicorn.run(
        "app:app",
        host=host, 
        port=port,
        reload=is_reload,
        log_level="info"
    )
