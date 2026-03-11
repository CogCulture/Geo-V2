import os

app_file = r"c:\Users\Cog\Downloads\GEO-V2\GEO(Server-Test)\GEO-backend\app.py"
analysis_file = r"c:\Users\Cog\Downloads\GEO-V2\GEO(Server-Test)\GEO-backend\api\analysis.py"

with open(app_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Analysis logic spans from line 672 to 2435
analysis_logic = lines[671:2435]

# Find imports needed for analysis
import_lines = [
    "import os\n",
    "import logging\n",
    "import json\n",
    "from typing import List, Optional, Dict, Any\n",
    "from datetime import datetime\n",
    "from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Header, Query\n",
    "from pydantic import BaseModel\n",
    "from collections import defaultdict\n",
    "import asyncio\n",
    "\n",
    "from api.auth import get_current_user\n",
    "from api.config import PLAN_LIMITS\n",
    "from services.tracking import send_signal\n",
    "from services.database_manager import *\n",
    "from services.scoring_engine import calculate_scores, aggregate_results\n",
    "from services.share_of_voice import calculate_share_of_voice\n",
    "from services.url_keyword_extractor import extract_keywords_from_url\n",
    "\n",
    "logger = logging.getLogger(__name__)\n\n",
    "router = APIRouter(prefix=\"/api\", tags=[\"Analysis\"])\n\n",
    "class CustomExecutionRequest(BaseModel):\n",
    "    prompts: List[str]\n",
    "    llms: List[str]\n\n",
    "class CompetitorUpdateRequest(BaseModel):\n",
    "    competitors: List[str]\n\n",
    "class AnalysisRequest(BaseModel):\n",
    "    brand_name: str\n",
    "    product_name: Optional[str] = None\n",
    "    industry: Optional[str] = None\n",
    "    website_url: Optional[str] = None\n",
    "    selected_llms: List[str] = []\n",
    "    regenerate_prompts: bool = True\n",
    "    custom_keywords: Optional[List[str]] = None\n",
    "    custom_competitors: Optional[List[str]] = None\n",
    "    project_id: Optional[str] = None\n",
    "    brand_aliases: Optional[List[str]] = None\n\n",
    "class ResearchRequest(BaseModel):\n",
    "    brand_name: str\n",
    "    website_url: Optional[str] = None\n\n"
]

# We need to replace @app.get, @app.post, ... with @router.get, @router.post, ...
processed_analysis_logic = []
for line in analysis_logic:
    if line.startswith("@app."):
        # Before we had /api in the path, now our router might not have prefix set for all.
        # Actually in app.py it was like @app.post("/api/analysis/run")
        # Since I set prefix="/api", I should either keep prefix="/" or remove "/api" from paths.
        # Let's just use router = APIRouter() without prefix so the paths remain unchanged.
        line = line.replace("@app.", "@router.")
    processed_analysis_logic.append(line)

# Let's adjust prefix and tags
import_lines[19] = "router = APIRouter(tags=[\"Analysis\"])\n\n"

with open(analysis_file, "w", encoding="utf-8") as f:
    f.writelines(import_lines)
    f.writelines(processed_analysis_logic)

print("Created api/analysis.py")
