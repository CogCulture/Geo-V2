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



# ============= AUTHENTICATION FUNCTIONS =============

def signup_user(email: str, password_hash: str) -> Optional[str]:
    try:
        data = {
            'email': email,
            'password_hash': password_hash,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        response = supabase.table('users').insert(data).execute()
        user_id = response.data[0]['id'] if response.data else None
        
        if user_id:
            logger.info(f"✅ User registered: {email}")
        
        return user_id
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        raise


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    try:
        response = supabase.table('users').select('*').eq('email', email).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}")
        return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    try:
        response = supabase.table('users').select(
            'id, email, created_at, subscription_plan, subscription_status, subscription_start, subscription_end, billing_cycle'
        ).eq('id', user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}")
        return None
