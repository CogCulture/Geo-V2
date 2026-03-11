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

def activate_user_subscription(user_id: str, plan_name: str, billing_cycle: str, razorpay_payment_id: str) -> bool:
    """
    Updates the users table with subscription details.
    Calculates subscription_end based on billing_cycle (monthly = +30 days, yearly = +365 days).
    """
    try:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        days = 365 if billing_cycle.lower() == "yearly" else 30
        subscription_end = (now + timedelta(days=days)).isoformat()

        supabase.table('users').update({
            'subscription_plan': plan_name,
            'subscription_status': 'active',
            'subscription_start': now.isoformat(),
            'subscription_end': subscription_end,
            'billing_cycle': billing_cycle,
            'razorpay_payment_id': razorpay_payment_id,
            'updated_at': now.isoformat()
        }).eq('id', user_id).execute()

        logger.info(f"✅ Subscription activated for user {user_id}: {plan_name} ({billing_cycle}) until {subscription_end}")
        return True
    except Exception as e:
        logger.error(f"❌ Error activating subscription for user {user_id}: {str(e)}")
        return False


def save_payment_transaction(
    user_id: str,
    user_email: str,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    plan_name: str,
    billing_cycle: str,
    subscription_end: str
) -> bool:
    """
    Saves an immutable audit record to the payment_transactions table.
    This provides idempotency: if razorpay_payment_id already exists (UNIQUE), the insert will fail.
    """
    try:
        supabase.table('payment_transactions').insert({
            'user_id': user_id,
            'user_email': user_email,
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
            'plan_name': plan_name,
            'billing_cycle': billing_cycle,
            'status': 'verified',
            'subscription_end': subscription_end,
        }).execute()
        logger.info(f"✅ Payment transaction saved for user {user_id}, payment {razorpay_payment_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving payment transaction: {str(e)}")
        # If the error is a unique-constraint violation the payment was already processed
        raise


def get_subscription_status(user_id: str) -> Dict[str, Any]:
    """
    Returns the subscription status for a user.
    `is_active` is True only when subscription_status == 'active' AND subscription_end is in the future.
    """
    try:
        from datetime import timezone
        response = supabase.table('users').select(
            'subscription_plan, subscription_status, subscription_start, subscription_end, billing_cycle'
        ).eq('id', user_id).execute()

        if not response.data:
            return {"is_active": False, "subscription_plan": None, "subscription_end": None}

        user = response.data[0]
        status = user.get('subscription_status', 'inactive')
        sub_end_str = user.get('subscription_end')

        is_active = False
        if status == 'active' and sub_end_str:
            try:
                # Handle both offset-aware and naive ISO strings
                sub_end = datetime.fromisoformat(sub_end_str.replace('Z', '+00:00'))
                if sub_end.tzinfo is None:
                    sub_end = sub_end.replace(tzinfo=timezone.utc)
                is_active = sub_end > datetime.now(timezone.utc)
            except Exception:
                is_active = False

        return {
            "is_active": is_active,
            "subscription_plan": user.get('subscription_plan'),
            "subscription_status": status,
            "subscription_start": user.get('subscription_start'),
            "subscription_end": sub_end_str,
            "billing_cycle": user.get('billing_cycle'),
        }
    except Exception as e:
        logger.error(f"Error getting subscription status for user {user_id}: {str(e)}")
        return {"is_active": False, "subscription_plan": None, "subscription_end": None}
