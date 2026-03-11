import os
import logging

logger = logging.getLogger(__name__)

PAID_API_KEY = os.environ.get("PAID_API_KEY")

try:
    from paid import Paid
    paid_client = Paid(token=PAID_API_KEY)
except Exception as e:
    logger.error(f"❌ Failed to initialize Paid.ai client: {str(e)}")
    paid_client = None

def init_tracking():
    pass

def send_signal(event_name: str, session_id: str, data: dict = None):
    """
    Sends business signals to Paid.ai. 
    session_id maps to external_customer_id to auto-create customers.
    """
    if not paid_client:
        return

    try:
        signal = {
            "event_name": event_name,
            "customer": {"external_customer_id": session_id},
            "attribution": {"external_product_id": "brand_visibility_analyzer"} 
        }
        
        if data:
            signal["data"] = data

        paid_client.signals.create_signals(signals=[signal])
        logger.info(f"✅ Sent signal to Paid: {event_name}")
    except Exception as e:
        logger.error(f"❌ Error sending signal: {str(e)}")
