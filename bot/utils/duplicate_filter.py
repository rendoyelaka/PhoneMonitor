import hashlib
import logging
from datetime import datetime
from bot.database.db_manager import db

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# DUPLICATE FILTER CLASS
# ─────────────────────────────────────────
class DuplicateFilter:
    def __init__(self):
        self._memory_cache = set()

    # ─────────────────────────────────────────
    # GENERATE UNIQUE SMS ID
    # ─────────────────────────────────────────
    def generate_sms_id(self, sender: str, message: str, timestamp: str) -> str:
        try:
            raw = f"{sender}_{message}_{timestamp}"
            return hashlib.sha256(raw.encode()).hexdigest()[:16]
        except Exception as e:
            logger.error(f"Generate SMS ID error: {e}")
            return hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:16]

    # ─────────────────────────────────────────
    # GENERATE UNIQUE NOTIFICATION ID
    # ─────────────────────────────────────────
    def generate_notif_id(self, app_name: str, title: str, content: str, timestamp: str) -> str:
        try:
            raw = f"{app_name}_{title}_{content}_{timestamp}"
            return hashlib.sha256(raw.encode()).hexdigest()[:16]
        except Exception as e:
            logger.error(f"Generate notification ID error: {e}")
            return hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:16]

    # ─────────────────────────────────────────
    # GENERATE UNIQUE VIEWER ID
    # ─────────────────────────────────────────
    def generate_viewer_id(self, app_name: str, input_text: str, timestamp: str) -> str:
        try:
            raw = f"{app_name}_{input_text}_{timestamp}"
            return hashlib.sha256(raw.encode()).hexdigest()[:16]
        except Exception as e:
            logger.error(f"Generate viewer ID error: {e}")
            return hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:16]

    # ─────────────────────────────────────────
    # CHECK IF SMS IS DUPLICATE
    # ─────────────────────────────────────────
    def is_duplicate_sms(self, sms_id: str) -> bool:
        try:
            if sms_id in self._memory_cache:
                return True
            exists = db.sms_exists(sms_id)
            if exists:
                self._memory_cache.add(sms_id)
            return exists
        except Exception as e:
            logger.error(f"Duplicate SMS check error: {e}")
            return False

    # ─────────────────────────────────────────
    # MARK SMS AS SEEN
    # ─────────────────────────────────────────
    def mark_sms_seen(self, sms_id: str):
        try:
            self._memory_cache.add(sms_id)
        except Exception as e:
            logger.error(f"Mark SMS seen error: {e}")

    # ─────────────────────────────────────────
    # IS OTP MESSAGE
    # ─────────────────────────────────────────
    def is_otp_message(self, message: str) -> bool:
        try:
            otp_keywords = [
                "otp", "one time", "verification", "verify",
                "code", "pin", "password", "passcode",
                "authenticate", "auth", "token", "secure"
            ]
            message_lower = message.lower()
            return any(keyword in message_lower for keyword in otp_keywords)
        except Exception as e:
            logger.error(f"OTP check error: {e}")
            return False

    # ─────────────────────────────────────────
    # CLEAR MEMORY CACHE
    # ─────────────────────────────────────────
    def clear_cache(self):
        try:
            self._memory_cache.clear()
            logger.info("Duplicate filter cache cleared")
        except Exception as e:
            logger.error(f"Clear cache error: {e}")


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
duplicate_filter = DuplicateFilter()
