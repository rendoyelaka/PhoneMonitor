import logging
import time
from datetime import datetime
from bot.database.db_manager import db
from bot.config import MAX_RETRY_ATTEMPTS, RETRY_DELAY_SECONDS

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# DELIVERY STATUS CONSTANTS
# ─────────────────────────────────────────
STATUS_PENDING = "pending"
STATUS_DELIVERED = "delivered"
STATUS_FAILED = "failed"
STATUS_RETRYING = "retrying"

# ─────────────────────────────────────────
# DELIVERY TRACKER CLASS
# ─────────────────────────────────────────
class DeliveryTracker:
    def __init__(self):
        self.max_retries = MAX_RETRY_ATTEMPTS
        self.retry_delay = RETRY_DELAY_SECONDS

    # ─────────────────────────────────────────
    # TRACK NEW ITEM
    # ─────────────────────────────────────────
    def track(self, item_id: str, item_type: str) -> bool:
        try:
            db.track_delivery(item_id, item_type, STATUS_PENDING, 0)
            return True
        except Exception as e:
            logger.error(f"Track item error: {e}")
            return False

    # ─────────────────────────────────────────
    # MARK DELIVERED
    # ─────────────────────────────────────────
    def mark_delivered(self, item_id: str, item_type: str) -> bool:
        try:
            db.track_delivery(item_id, item_type, STATUS_DELIVERED, 1)
            logger.info(f"Item delivered: {item_id}")
            return True
        except Exception as e:
            logger.error(f"Mark delivered error: {e}")
            return False

    # ─────────────────────────────────────────
    # MARK FAILED
    # ─────────────────────────────────────────
    def mark_failed(self, item_id: str, item_type: str, attempts: int) -> bool:
        try:
            db.track_delivery(item_id, item_type, STATUS_FAILED, attempts)
            logger.warning(f"Item failed: {item_id} after {attempts} attempts")
            return True
        except Exception as e:
            logger.error(f"Mark failed error: {e}")
            return False

    # ─────────────────────────────────────────
    # SEND WITH RETRY
    # ─────────────────────────────────────────
    def send_with_retry(self, item_id: str, item_type: str, send_function, *args) -> bool:
        attempts = 0
        while attempts < self.max_retries:
            try:
                result = send_function(*args)
                if result:
                    self.mark_delivered(item_id, item_type)
                    return True
                else:
                    attempts += 1
                    logger.warning(f"Send attempt {attempts} failed for {item_id}")
                    if attempts < self.max_retries:
                        time.sleep(self.retry_delay)
            except Exception as e:
                attempts += 1
                logger.error(f"Send error attempt {attempts} for {item_id}: {e}")
                if attempts < self.max_retries:
                    time.sleep(self.retry_delay)

        self.mark_failed(item_id, item_type, attempts)
        return False

    # ─────────────────────────────────────────
    # GET DELIVERY STATS
    # ─────────────────────────────────────────
    def get_stats(self) -> dict:
        try:
            return db.get_delivery_stats()
        except Exception as e:
            logger.error(f"Get stats error: {e}")
            return {"total": 0, "delivered": 0, "failed": 0, "pending": 0}

    # ─────────────────────────────────────────
    # FORMAT STATS MESSAGE
    # ─────────────────────────────────────────
    def format_stats_message(self) -> str:
        try:
            stats = self.get_stats()
            queue_status = db.get_full_queue_status()
            message = (
                f"📊 Delivery Status\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"✅ Delivered: {stats['delivered']}\n"
                f"❌ Failed: {stats['failed']}\n"
                f"⏳ Pending: {stats['pending']}\n"
                f"📦 Total: {stats['total']}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📬 Queue Status\n"
                f"📱 SMS Queue: {queue_status['sms_queue']}\n"
                f"👁 Viewer Queue: {queue_status['viewer_queue']}\n"
                f"🔔 Notification Queue: {queue_status['notification_queue']}\n"
                f"📦 Total Queue: {queue_status['total']}\n"
            )
            return message
        except Exception as e:
            logger.error(f"Format stats message error: {e}")
            return "⚠️ Stats unavailable"


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
delivery_tracker = DeliveryTracker()
