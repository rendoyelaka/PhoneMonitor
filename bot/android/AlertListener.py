import logging
import threading
import time
import uuid
import requests
from datetime import datetime
from bot.database.db_manager import db
from bot.utils.priority_queue import priority_queue
from bot.config import BOT_TOKEN, OWNER_ID

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# ALERT LISTENER CLASS
# Listens for all incoming notifications
# from all apps on the Android device.
# Forwards them to Telegram in real time.
# Supports offline save + auto sync.
# ─────────────────────────────────────────
class AlertListener:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.owner_id = OWNER_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self._running = False
        self._thread = None
        self.poll_interval = 1  # Check every 1 second for new notifications

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
            logger.error(f"Alert listener send error: {e}")
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
    # GENERATE NOTIFICATION ID
    # ─────────────────────────────────────────
    def _generate_notif_id(self, app_name: str, title: str, timestamp: str) -> str:
        raw = f"{app_name}:{title}:{timestamp}"
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, raw))

    # ─────────────────────────────────────────
    # ON NOTIFICATION RECEIVED
    # Entry point called when Android
    # NotificationListenerService fires
    # ─────────────────────────────────────────
    def on_alert_received(self, app_name: str, title: str, content: str, package_name: str = "") -> bool:
        try:
            if not app_name or not title:
                return False

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            notif_id = self._generate_notif_id(app_name, title, timestamp)

            logger.info(f"Alert received from: {app_name} — {title}")

            if self._is_online():
                # Online — deliver immediately
                message = (
                    f"🔔 Alert\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"📲 App: <b>{app_name}</b>\n"
                    f"📌 Title: {title}\n"
                    f"💬 Content: {content}\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"🕐 Time: {timestamp}\n"
                )
                success = self._send_to_telegram(message)
                if success:
                    db.insert_notification(notif_id, app_name, title, content, timestamp)
                    with db.get_connection() as conn:
                        conn.execute(
                            "UPDATE notifications SET is_delivered = 1 WHERE notif_id = ?",
                            (notif_id,)
                        )
                        conn.commit()
                    logger.info(f"Alert delivered: {notif_id}")
                    return True
                else:
                    # Send failed — save to queue
                    logger.warning(f"Alert send failed — queuing: {notif_id}")
                    priority_queue.add_notification(notif_id, app_name, title, content, timestamp)
                    return False
            else:
                # Offline — save to queue
                logger.info(f"Offline — alert queued: {notif_id}")
                priority_queue.add_notification(notif_id, app_name, title, content, timestamp)
                return True

        except Exception as e:
            logger.error(f"On alert received error: {e}")
            return False

    # ─────────────────────────────────────────
    # SYNC OFFLINE NOTIFICATION QUEUE
    # Called when internet is restored
    # ─────────────────────────────────────────
    def sync_offline_alerts(self) -> dict:
        try:
            if not self._is_online():
                return {"success": False, "reason": "offline", "synced": 0}

            queue = db.get_notification_queue()
            synced = 0
            failed = 0

            for item in queue:
                try:
                    message = (
                        f"🔔 Alert [SYNCED]\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📲 App: <b>{item['app_name']}</b>\n"
                        f"📌 Title: {item['title']}\n"
                        f"💬 Content: {item['content']}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"🕐 Time: {item['timestamp']}\n"
                        f"🔄 Synced: {datetime.now().strftime('%H:%M:%S')}\n"
                    )
                    success = self._send_to_telegram(message)
                    if success:
                        db.remove_from_notification_queue(item["notif_id"])
                        synced += 1
                        logger.info(f"Offline alert synced: {item['notif_id']}")
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Sync alert item error: {e}")
                    failed += 1

            return {"success": True, "synced": synced, "failed": failed}

        except Exception as e:
            logger.error(f"Sync offline alerts error: {e}")
            return {"success": False, "reason": str(e), "synced": 0}

    # ─────────────────────────────────────────
    # START LISTENER LOOP
    # Polls DB for new undelivered notifications
    # ─────────────────────────────────────────
    def start(self):
        try:
            if self._running:
                logger.info("Alert listener already running")
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._listener_loop,
                daemon=True,
                name="AlertListenerThread"
            )
            self._thread.start()
            logger.info("Alert listener started")
        except Exception as e:
            logger.error(f"Start alert listener error: {e}")

    # ─────────────────────────────────────────
    # STOP LISTENER
    # ─────────────────────────────────────────
    def stop(self):
        try:
            self._running = False
            logger.info("Alert listener stopped")
        except Exception as e:
            logger.error(f"Stop alert listener error: {e}")

    # ─────────────────────────────────────────
    # LISTENER LOOP
    # ─────────────────────────────────────────
    def _listener_loop(self):
        while self._running:
            try:
                self._check_and_deliver_alerts()
            except Exception as e:
                logger.error(f"Listener loop error: {e}")
            time.sleep(self.poll_interval)

    # ─────────────────────────────────────────
    # CHECK AND DELIVER UNDELIVERED ALERTS
    # ─────────────────────────────────────────
    def _check_and_deliver_alerts(self):
        try:
            with db.get_connection() as conn:
                rows = conn.execute(
                    """SELECT * FROM notifications
                    WHERE is_delivered = 0
                    ORDER BY created_at ASC
                    LIMIT 10"""
                ).fetchall()

            if not rows:
                return

            if not self._is_online():
                logger.debug("Offline — alert delivery waiting")
                return

            for row in rows:
                item = dict(row)
                try:
                    message = (
                        f"🔔 Alert\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📲 App: <b>{item['app_name']}</b>\n"
                        f"📌 Title: {item['title']}\n"
                        f"💬 Content: {item['content']}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"🕐 Time: {item['timestamp']}\n"
                    )
                    success = self._send_to_telegram(message)
                    if success:
                        with db.get_connection() as conn:
                            conn.execute(
                                "UPDATE notifications SET is_delivered = 1 WHERE notif_id = ?",
                                (item["notif_id"],)
                            )
                            conn.commit()
                        logger.info(f"Alert delivered: {item['notif_id']}")
                except Exception as e:
                    logger.error(f"Deliver alert item error: {e}")

        except Exception as e:
            logger.error(f"Check and deliver alerts error: {e}")

    # ─────────────────────────────────────────
    # GET LISTENER STATUS
    # ─────────────────────────────────────────
    def get_status(self) -> dict:
        try:
            with db.get_connection() as conn:
                total = conn.execute(
                    "SELECT COUNT(*) as count FROM notifications"
                ).fetchone()["count"]
                undelivered = conn.execute(
                    "SELECT COUNT(*) as count FROM notifications WHERE is_delivered = 0"
                ).fetchone()["count"]
                queued = conn.execute(
                    "SELECT COUNT(*) as count FROM notification_queue"
                ).fetchone()["count"]
            return {
                "running": self._running,
                "total_alerts": total,
                "undelivered": undelivered,
                "queued": queued,
                "online": self._is_online()
            }
        except Exception as e:
            logger.error(f"Alert listener status error: {e}")
            return {"running": self._running, "total_alerts": 0, "undelivered": 0}


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
alert_listener = AlertListener()
