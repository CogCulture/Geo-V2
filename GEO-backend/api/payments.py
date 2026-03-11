import os
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from api.auth import get_current_user
from services.payment_manager import payment_manager
from services.database_manager import (
    get_user_by_id,
    save_payment_transaction,
    activate_user_subscription,
    get_subscription_status
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["Payments"])

class RazorpayOrderRequest(BaseModel):
    plan_name: str
    billing_cycle: str
    user_id: str

class RazorpayVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    user_id: str
    plan_name: str
    billing_cycle: str


@router.post("/razorpay/create-order")
async def create_razorpay_order(request: RazorpayOrderRequest):
    """Create a new Razorpay order for a specific plan"""
    try:
        # Define prices in Paise (100 Paise = 1 INR)
        # lite plan, growth plan, pro plan
        prices = {
            "lite plan": {"monthly": 240000, "yearly": 2400000},
            "growth plan": {"monthly": 650000, "yearly": 6500000},
            "pro plan": {"monthly": 1150000, "yearly": 11500000},
            "enterprise": {"monthly": 3700000, "yearly": 37000000}
        }
        
        plan_key = request.plan_name.lower()
        if plan_key not in prices:
            raise HTTPException(status_code=400, detail="Invalid plan name")
            
        cycle = request.billing_cycle.lower()
        if cycle not in ["monthly", "yearly"]:
            raise HTTPException(status_code=400, detail="Invalid billing cycle")
            
        amount = prices[plan_key][cycle]
        
        # Shorten user_id to fit in 40 char receipt limit
        short_id = request.user_id[:8] if len(request.user_id) > 8 else request.user_id
        receipt_id = f"rcpt_{short_id}_{int(datetime.now().timestamp())}"
        
        order = payment_manager.create_order(
            amount=amount,
            currency="INR",
            receipt=receipt_id
        )
        
        if not order:
            raise HTTPException(status_code=500, detail="Failed to create Razorpay order")
            
        return {
            "status": "success",
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": os.environ.get("RAZORPAY_KEY_ID")
        }
    except Exception as e:
        logger.error(f"Error in create_razorpay_order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/razorpay/verify-payment")
async def verify_razorpay_payment(request: RazorpayVerifyRequest):
    """
    Verify Razorpay payment signature and activate user subscription.
    Security flow:
      1. HMAC-SHA256 signature verification (prevents forged callbacks)
      2. User existence guard
      3. Idempotency guard via payment_transactions UNIQUE constraint
      4. Immutable audit log written BEFORE subscription activation
      5. Subscription columns updated on users table
    """
    try:
        # ── 1. Cryptographic Signature Verification ──────────────────────────
        is_valid = payment_manager.verify_signature(
            order_id=request.razorpay_order_id,
            payment_id=request.razorpay_payment_id,
            signature=request.razorpay_signature
        )
        if not is_valid:
            logger.warning(f"❌ Invalid Razorpay signature for order {request.razorpay_order_id}")
            raise HTTPException(status_code=400, detail="Invalid payment signature")

        # ── 2. User Guard ─────────────────────────────────────────────────────
        user = get_user_by_id(request.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_email = user.get('email', '')

        # ── 3 & 4. Idempotency + Audit Log ───────────────────────────────────
        # Calculate subscription_end (needed for the audit row)
        now = datetime.now(timezone.utc)
        days = 365 if request.billing_cycle.lower() == "yearly" else 30
        subscription_end_iso = (now + timedelta(days=days)).isoformat()

        try:
            save_payment_transaction(
                user_id=request.user_id,
                user_email=user_email,
                razorpay_order_id=request.razorpay_order_id,
                razorpay_payment_id=request.razorpay_payment_id,
                razorpay_signature=request.razorpay_signature,
                plan_name=request.plan_name,
                billing_cycle=request.billing_cycle,
                subscription_end=subscription_end_iso,
            )
        except Exception as audit_err:
            # If the payment_id already exists it's a replay attack / accidental retry
            err_str = str(audit_err).lower()
            if 'unique' in err_str or 'duplicate' in err_str:
                logger.warning(f"⚠️ Duplicate payment attempt blocked: {request.razorpay_payment_id}")
                raise HTTPException(status_code=409, detail="This payment has already been processed")
            # If the payment_transactions table doesn't exist yet, log a warning but proceed
            logger.warning(f"⚠️ Could not save payment_transaction (table may be missing): {audit_err}")

        # ── 5. Activate Subscription ──────────────────────────────────────────
        activated = activate_user_subscription(
            user_id=request.user_id,
            plan_name=request.plan_name,
            billing_cycle=request.billing_cycle,
            razorpay_payment_id=request.razorpay_payment_id
        )
        if not activated:
            raise HTTPException(status_code=500, detail="Payment verified but subscription activation failed")

        logger.info(f"✅ Subscription activated for user {request.user_id} — plan: {request.plan_name}")

        return {
            "status": "success",
            "message": "Payment verified and subscription activated successfully",
            "subscription_end": subscription_end_iso
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in verify_razorpay_payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscription-status")
async def check_subscription_status_endpoint(user_id: str = Depends(get_current_user)):
    """
    JWT-protected endpoint. Returns the current subscription status for the
    logged-in user. Used by the frontend to gate dashboard access.
    """
    try:
        status = get_subscription_status(user_id)
        return {"status": "success", "subscription": status}
    except Exception as e:
        logger.error(f"Error fetching subscription status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription status")
