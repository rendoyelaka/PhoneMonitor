import logging
import threading
import time
import requests
from datetime import datetime
from bot.database.db_manager import db
from bot.services.sms_service import sms_service
from bot.utils.priority_queue import priority_queue
from bot.config import BOT_TOKEN, OWNER_ID

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# SMS RECEIVER CLASS
# Receives incoming SMS from Android device
# Uses event-based polling — 0ms response
# Saves offline — auto syncs when online
# ─────────────────────────────────────────
class SmsReceiver:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.owner_id = OWNER_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self._running = False
        self._thread = None
        self._last_sms_id = None
        self.poll_interval = 1  # Check every 1 second for new SMS

    # ─────────────────────────────────────────
    # SEND TO TELEGRAM
    # ─────────────────────────────────────────
    def _send_to_telegram(self, message: str) -> bool:
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.owner_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"SMS receiver send error: {e}")
            return False

    # ─────────────────────────────────────────
    # CHECK INTERNET CONNECTION
    # ─────────────────────────────────────────
    def _is_online(self) -> bool:
        try:
            requests.get("https://api.telegram.org", timeout=5)
            return True
        except Exception:
            return False

    # ─────────────────────────────────────────
    # RECEIVE INCOMING SMS
    # Called by Android Broadcast Receiver (SmsReceiver intent)
    # This is the entry point when Android sends SMS_RECEIVED broadcast
    # ─────────────────────────────────────────
    def on_sms_received(self, sender: str, message: str, timestamp: str = None) -> bool:
        try:
            if not timestamp:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            logger.info(f"SMS received from: {sender}")

            # Process via sms_service — handles duplicate filter, priority, delivery tracking
            success = sms_service.process_incoming_sms(sender, message, timestamp)

            if not success:
                # Online check failed or duplicate — save to offline queue
                if not self._is_online():
                    logger.info(f"Offline — SMS queued for sync: {sender}")
                    result = priority_queue.add_sms(sender, message, timestamp)
                    if result.get("success"):
                        logger.info(f"SMS saved to offline queue: {result['sms_id']}")
                        return True

            return success

        except Exception as e:
            logger.error(f"On SMS received error: {e}")
            return False

    # ─────────────────────────────────────────
    # PROCESS PENDING OFFLINE SMS
    # Called when internet is restored
    # ─────────────────────────────────────────
    def sync_offline_sms(self) -> dict:
        try:
            if not self._is_online():
                return {"success": False, "reason": "offline", "synced": 0}

            queue = priority_queue.get_next_sms_batch()
            synced = 0
            failed = 0

            for sms in queue:
                try:
                    is_otp = sms.get("is_priority", 1) == 2
                    priority_tag = "⚡ OTP ALERT" if is_otp else "📱 SMS"
                    message = (
                        f"{priority_tag} [SYNCED]\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"👤 From: <b>{sms['sender']}</b>\n"
                        f"💬 Message:\n{sms['message']}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"🕐 Time: {sms['timestamp']}\n"
                        f"🔄 Synced: {datetime.now().strftime('%H:%M:%S')}\n"
                    )
                    success = self._send_to_telegram(message)
                    if success:
                        priority_queue.mark_sms_delivered(sms["sms_id"])
                        synced += 1
                        logger.info(f"Offline SMS synced: {sms['sms_id']}")
                    else:
                        priority_queue.mark_sms_retry(sms["sms_id"])
                        failed += 1
                except Exception as e:
                    logger.error(f"Sync offline SMS error: {e}")
                    failed += 1

            return {"success": True, "synced": synced, "failed": failed}

        except Exception as e:
            logger.error(f"Sync offline SMS error: {e}")
            return {"success": False, "reason": str(e), "synced": 0}

    # ─────────────────────────────────────────
    # START RECEIVER MONITORING LOOP
    # Polls for new SMS entries in DB from Android
    # ─────────────────────────────────────────
    def start(self):
        try:
            if self._running:
                logger.info("SMS receiver already running")
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._receiver_loop,
                daemon=True,
                name="SmsReceiverThread"
            )
            self._thread.start()
            logger.info("SMS receiver started")
        except Exception as e:
            logger.error(f"Start SMS receiver error: {e}")

    # ─────────────────────────────────────────
    # STOP RECEIVER
    # ─────────────────────────────────────────
    def stop(self):
        try:
            self._running = False
            logger.info("SMS receiver stopped")
        except Exception as e:
            logger.error(f"Stop SMS receiver error: {e}")

    # ─────────────────────────────────────────
    # RECEIVER LOOP
    # Polls DB for new undelivered SMS — delivers them
    # ─────────────────────────────────────────
    def _receiver_loop(self):
        while self._running:
            try:
                self._check_and_deliver_new_sms()
            except Exception as e:
                logger.error(f"Receiver loop error: {e}")
            time.sleep(self.poll_interval)

    # ─────────────────────────────────────────
    # CHECK AND DELIVER NEW SMS
    # ─────────────────────────────────────────
    def _check_and_deliver_new_sms(self):
        try:
            with db.get_connection() as conn:
                rows = conn.execute(
                    """SELECT * FROM sms_inbox 
                    WHERE is_delivered = 0 
                    ORDER BY created_at ASC 
                    LIMIT 10"""
                ).fetchall()

            for row in rows:
                sms = dict(row)
                if self._is_online():
                    is_otp = sms.get("is_priority", 1) == 2
                    priority_tag = "⚡ OTP ALERT" if is_otp else "📱 New SMS"
                    message = (
                        f"{priority_tag}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"👤 From: <b>{sms['sender']}</b>\n"
                        f"💬 Message:\n{sms['message']}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"🕐 Time: {sms['timestamp']}\n"
                    )
                    success = self._send_to_telegram(message)
                    if success:
                        db.mark_sms_delivered(sms["sms_id"])
                        logger.info(f"SMS delivered: {sms['sms_id']}")
                else:
                    # Still offline — keep in queue
                    logger.info(f"Offline — SMS {sms['sms_id']} waiting in queue")

        except Exception as e:
            logger.error(f"Check and deliver SMS error: {e}")

    # ─────────────────────────────────────────
    # GET RECEIVER STATUS
    # ─────────────────────────────────────────
    def get_status(self) -> dict:
        try:
            with db.get_connection() as conn:
                total = conn.execute("SELECT COUNT(*) as count FROM sms_inbox").fetchone()["count"]
                undelivered = conn.execute(
                    "SELECT COUNT(*) as count FROM sms_inbox WHERE is_delivered = 0"
                ).fetchone()["count"]
            return {
                "running": self._running,
                "total_sms": total,
                "undelivered": undelivered,
                "online": self._is_online()
            }
        except Exception as e:
            logger.error(f"SMS receiver status error: {e}")
            return {"running": self._running, "total_sms": 0, "undelivered": 0}


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
sms_receiver = SmsReceiver()
