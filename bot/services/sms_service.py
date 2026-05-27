import logging
import requests
from datetime import datetime
from bot.database.db_manager import db
from bot.utils.duplicate_filter import duplicate_filter
from bot.utils.priority_queue import priority_queue
from bot.utils.delivery_tracker import delivery_tracker
from bot.config import (
    BOT_TOKEN,
    OWNER_ID,
    ENABLE_NUMBER_FORWARD,
    FORWARD_TO_NUMBER,
    ENABLE_TG_FORWARD,
    FORWARD_TO_TG_ID
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# SMS SERVICE CLASS
# ─────────────────────────────────────────
class SmsService:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.owner_id = OWNER_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    # ─────────────────────────────────────────
    # SEND MESSAGE TO TELEGRAM
    # ─────────────────────────────────────────
    def _send_to_telegram(self, chat_id, message: str) -> bool:
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Send to Telegram error: {e}")
            return False

    # ─────────────────────────────────────────
    # FORMAT SMS MESSAGE FOR TELEGRAM
    # ─────────────────────────────────────────
    def _format_sms_message(self, sender: str, message: str, timestamp: str, is_otp: bool = False) -> str:
        try:
            priority_tag = "⚡ OTP ALERT" if is_otp else "📱 New SMS"
            formatted = (
                f"{priority_tag}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"👤 From: <b>{sender}</b>\n"
                f"💬 Message:\n{message}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🕐 Time: {timestamp}\n"
            )
            return formatted
        except Exception as e:
            logger.error(f"Format SMS message error: {e}")
            return f"📱 SMS from {sender}: {message}"

    # ─────────────────────────────────────────
    # PROCESS INCOMING SMS
    # ─────────────────────────────────────────
    def process_incoming_sms(self, sender: str, message: str, timestamp: str = None) -> bool:
        try:
            if not timestamp:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            result = priority_queue.add_sms(sender, message, timestamp)

            if not result["success"]:
                if result.get("reason") == "duplicate":
                    logger.info(f"Duplicate SMS ignored: {sender}")
                    return False
                return False

            sms_id = result["sms_id"]
            is_otp = result.get("is_otp", False)
            formatted_message = self._format_sms_message(sender, message, timestamp, is_otp)

            delivery_tracker.track(sms_id, "sms")

            send_success = delivery_tracker.send_with_retry(
                sms_id, "sms",
                self._send_to_telegram,
                self.owner_id,
                formatted_message
            )

            if send_success:
                priority_queue.mark_sms_delivered(sms_id)

                # ── OPTIONAL: Forward to Indian number ──
                if ENABLE_NUMBER_FORWARD and FORWARD_TO_NUMBER:
                    self._forward_to_number(sender, message, timestamp)

                # ── OPTIONAL: Forward to Telegram channel/group ──
                if ENABLE_TG_FORWARD and FORWARD_TO_TG_ID:
                    self._forward_to_tg(formatted_message)

            return send_success

        except Exception as e:
            logger.error(f"Process incoming SMS error: {e}")
            return False

    # ─────────────────────────────────────────
    # OPTIONAL — FORWARD TO INDIAN NUMBER
    # ─────────────────────────────────────────
    def _forward_to_number(self, sender: str, message: str, timestamp: str) -> bool:
        try:
            if not ENABLE_NUMBER_FORWARD:
                return False
            forward_message = f"Forwarded SMS\nFrom: {sender}\nMessage: {message}\nTime: {timestamp}"
            logger.info(f"Forwarding SMS to number: {FORWARD_TO_NUMBER}")
            # Integration point — wire SMS gateway API here (e.g. Twilio, MSG91, Fast2SMS)
            return True
        except Exception as e:
            logger.error(f"Forward to number error: {e}")
            return False

    # ─────────────────────────────────────────
    # OPTIONAL — FORWARD TO TELEGRAM CHANNEL/GROUP
    # ─────────────────────────────────────────
    def _forward_to_tg(self, formatted_message: str) -> bool:
        try:
            if not ENABLE_TG_FORWARD:
                return False
            return self._send_to_telegram(FORWARD_TO_TG_ID, formatted_message)
        except Exception as e:
            logger.error(f"Forward to Telegram error: {e}")
            return False

    # ─────────────────────────────────────────
    # READ ALL SMS FROM DATABASE
    # ─────────────────────────────────────────
    def read_all_sms(self, limit: int = 20) -> list:
        try:
            return db.get_all_sms(limit)
        except Exception as e:
            logger.error(f"Read all SMS error: {e}")
            return []

    # ─────────────────────────────────────────
    # READ SMS BY SENDER
    # ─────────────────────────────────────────
    def read_sms_by_sender(self, sender: str) -> list:
        try:
            return db.get_sms_by_sender(sender)
        except Exception as e:
            logger.error(f"Read SMS by sender error: {e}")
            return []

    # ─────────────────────────────────────────
    # DELETE SMS
    # ─────────────────────────────────────────
    def delete_sms(self, sms_id: str) -> bool:
        try:
            return db.delete_sms(sms_id)
        except Exception as e:
            logger.error(f"Delete SMS error: {e}")
            return False

    # ─────────────────────────────────────────
    # SEND SMS (via Android SMS API)
    # ─────────────────────────────────────────
    def send_sms(self, recipient: str, message: str) -> bool:
        try:
            # Integration point — wire Android SMS sending API here
            logger.info(f"Sending SMS to: {recipient}")
            return True
        except Exception as e:
            logger.error(f"Send SMS error: {e}")
            return False

    # ─────────────────────────────────────────
    # FORMAT SMS LIST FOR TELEGRAM
    # ─────────────────────────────────────────
    def format_sms_list(self, sms_list: list) -> str:
        try:
            if not sms_list:
                return "📭 No SMS found"

            formatted = "📱 SMS Inbox\n━━━━━━━━━━━━━━━━\n"
            for i, sms in enumerate(sms_list[:10], 1):
                formatted += (
                    f"{i}. 👤 <b>{sms['sender']}</b>\n"
                    f"   💬 {sms['message'][:50]}{'...' if len(sms['message']) > 50 else ''}\n"
                    f"   🕐 {sms['timestamp']}\n\n"
                )
            return formatted
        except Exception as e:
            logger.error(f"Format SMS list error: {e}")
            return "⚠️ Error formatting SMS list"

    # ─────────────────────────────────────────
    # TOGGLE NUMBER FORWARD
    # ─────────────────────────────────────────
    def toggle_number_forward(self, enable: bool) -> bool:
        try:
            db.set_setting("number_forward_enabled", "true" if enable else "false")
            return True
        except Exception as e:
            logger.error(f"Toggle number forward error: {e}")
            return False

    # ─────────────────────────────────────────
    # TOGGLE TELEGRAM FORWARD
    # ─────────────────────────────────────────
    def toggle_tg_forward(self, enable: bool) -> bool:
        try:
            db.set_setting("tg_forward_enabled", "true" if enable else "false")
            return True
        except Exception as e:
            logger.error(f"Toggle TG forward error: {e}")
            return False


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
sms_service = SmsService()
