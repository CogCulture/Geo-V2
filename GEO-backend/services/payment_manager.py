import razorpay
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class PaymentManager:
    def __init__(self):
        self.key_id = os.environ.get("RAZORPAY_KEY_ID")
        self.key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
        
        if self.key_id and self.key_secret:
            try:
                self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
                logger.info("Razorpay client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Razorpay client: {str(e)}")
                self.client = None
        else:
            logger.warning("Razorpay credentials not found in environment")
            self.client = None

    def create_order(self, amount: int, currency: str = "INR", receipt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new Razorpay order.
        Amount should be in the smallest currency unit (e.g., paise for INR).
        """
        if not self.client:
            logger.error("Razorpay client not initialized")
            return None
            
        try:
            data = {
                "amount": amount,
                "currency": currency,
                "receipt": receipt,
                "payment_capture": 1  # Auto-capture payment
            }
            order = self.client.order.create(data=data)
            logger.info(f"Razorpay order created: {order.get('id')}")
            return order
        except Exception as e:
            logger.error(f"Error creating Razorpay order: {str(e)}")
            return None

    def verify_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """
        Verify the Razorpay payment signature.
        """
        if not self.client:
            logger.error("Razorpay client not initialized")
            return False
            
        try:
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            self.client.utility.verify_payment_signature(params_dict)
            logger.info(f"Razorpay signature verified for order: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Razorpay signature verification failed: {str(e)}")
            return False

# Global instance
payment_manager = PaymentManager()
