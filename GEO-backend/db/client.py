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

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- STATUS MANAGEMENT (The Fix for Global Variable Issue) ---


def init_database():
    """
    Initialize Supabase database with schema
    Note: Tables should be created via Supabase SQL Editor using the schema below
    """
    logger.info("Using Supabase database")
    logger.info("Ensure tables are created in Supabase SQL Editor with the following schema:")
    
    schema_sql = """ 
    CREATE TABLE IF NOT EXISTS projects (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        website_url TEXT,
        industry TEXT,
        update_frequency TEXT DEFAULT '24h',
        is_active BOOLEAN DEFAULT TRUE,
        last_sync_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Monitored Prompts for a project
    CREATE TABLE IF NOT EXISTS monitored_prompts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        prompt_text TEXT NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Monitored Competitors for a project
    CREATE TABLE IF NOT EXISTS monitored_competitors (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Daily Metrics for historical tracking (Real-time Dashboard Source)
    CREATE TABLE IF NOT EXISTS daily_brand_metrics (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        llm_name TEXT NOT NULL,
        visibility_score REAL,
        avg_position REAL,
        mention_count INTEGER,
        total_prompts INTEGER,
        citation_count INTEGER,
        date DATE NOT NULL DEFAULT CURRENT_DATE,
        UNIQUE(project_id, llm_name, date)
    );

    -- Main analysis sessions table (Updated to link to project)
    CREATE TABLE IF NOT EXISTS analysis_sessions (
        session_id TEXT PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        project_id UUID REFERENCES projects(id) ON DELETE SET NULL, -- Link to project
        brand_name TEXT NOT NULL,
        product_name TEXT,
        industry TEXT,
        website_url TEXT,
        timestamp TEXT NOT NULL,
        research_data JSONB,
        keywords JSONB,
        status TEXT DEFAULT 'pending',
        current_step TEXT,
        progress INTEGER DEFAULT 0,
        error_message TEXT
    );
    
    -- LLM responses table (Updated to link to project)
    CREATE TABLE IF NOT EXISTS llm_responses (
        id SERIAL PRIMARY KEY,
        prompt_id TEXT NOT NULL,
        session_id TEXT NOT NULL REFERENCES analysis_sessions(session_id),
        project_id UUID REFERENCES projects(id) ON DELETE SET NULL, -- Link to project
        llm_name TEXT NOT NULL,
        prompt_text TEXT NOT NULL,
        response_text TEXT NOT NULL,
        citations JSONB,
        timestamp TEXT NOT NULL
    );
    
    -- Scoring results table (Updated to link to project)
    CREATE TABLE IF NOT EXISTS scoring_results (
        id SERIAL PRIMARY KEY,
        prompt_id TEXT NOT NULL,
        session_id TEXT NOT NULL REFERENCES analysis_sessions(session_id),
        project_id UUID REFERENCES projects(id) ON DELETE SET NULL, -- Link to project
        llm_name TEXT NOT NULL,
        brand_mention_score REAL,
        position_score REAL,
        description_richness_score REAL,
        keyword_strength_score REAL,
        total_score REAL,
        normalized_visibility REAL,
        average_positioning REAL,
        weighted_score REAL,
        brand_position INTEGER,
        total_items INTEGER,
        timestamp TEXT NOT NULL
    );
    
    -- Competitors table
    CREATE TABLE IF NOT EXISTS competitors (
        id SERIAL PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES analysis_sessions(session_id),
        competitor_name TEXT NOT NULL,
        rank INTEGER
    );
    
    -- Share of Voice results table
    CREATE TABLE IF NOT EXISTS share_of_voice (
        id SERIAL PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES analysis_sessions(session_id),
        brand_name TEXT NOT NULL,
        normalized_visibility REAL,
        average_positioning REAL,
        weighted_score REAL,
        rank INTEGER,
        timestamp TEXT NOT NULL
    );
    
    -- Saved prompts table
    CREATE TABLE IF NOT EXISTS saved_prompts (
        id SERIAL PRIMARY KEY,
        brand_name TEXT NOT NULL,
        product_name TEXT,
        prompts_json JSONB NOT NULL,
        timestamp TEXT NOT NULL,
        UNIQUE(brand_name, product_name)
    );
    
    -- Cohorts table
    CREATE TABLE IF NOT EXISTS cohorts (
        id SERIAL PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES analysis_sessions(session_id),
        cohort_name TEXT NOT NULL,
        cohort_description TEXT,
        prompt_count INTEGER,
        cohort_order INTEGER,
        timestamp TEXT NOT NULL
    );
    
    -- Prompts with cohort mapping table
    CREATE TABLE IF NOT EXISTS prompts_cohort_mapping (
        id SERIAL PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES analysis_sessions(session_id),
        cohort_id INTEGER NOT NULL REFERENCES cohorts(id),
        prompt_text TEXT NOT NULL,
        prompt_index INTEGER,
        selected BOOLEAN DEFAULT FALSE,
        timestamp TEXT NOT NULL
    );
    """
    
    logger.info("Copy the above SQL to Supabase SQL Editor to create tables")
    return True


# Initialize database on module import
init_database()

