import logging
import threading
import time
import requests
from datetime import datetime
from bot.config import BOT_TOKEN, OWNER_ID

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# RECONNECT SERVICE CLASS
# ─────────────────────────────────────────
class ReconnectService:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.owner_id = OWNER_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self._running = False
        self._thread = None
        self._connected = False
        self._reconnect_attempts = 0
        self._last_connected = None
        self._last_disconnected = None
        self.check_interval = 15
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5

    # ─────────────────────────────────────────
    # CHECK BOT CONNECTION
    # ─────────────────────────────────────────
    def _check_connection(self) -> bool:
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    # ─────────────────────────────────────────
    # SEND RECONNECT NOTIFICATION
    # ─────────────────────────────────────────
    def _notify_reconnected(self):
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.owner_id,
                "text": (
                    f"🟢 Bot Reconnected\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"✅ Connection restored\n"
                    f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}\n"
                    f"🔢 Attempt: {self._reconnect_attempts}\n"
                ),
                "parse_mode": "HTML"
            }
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Notify reconnected error: {e}")

    # ─────────────────────────────────────────
    # ATTEMPT RECONNECTION
    # ─────────────────────────────────────────
    def _attempt_reconnect(self) -> bool:
        try:
            self._reconnect_attempts += 1
            logger.info(f"Reconnect attempt {self._reconnect_attempts}")

            for attempt in range(self.max_reconnect_attempts):
                time.sleep(self.reconnect_delay * (attempt + 1))
                if self._check_connection():
                    self._connected = True
                    self._last_connected = datetime.now()
                    self._reconnect_attempts = 0
                    logger.info("Reconnection successful")
                    self._notify_reconnected()
                    return True
                logger.warning(f"Reconnect sub-attempt {attempt + 1} failed")

            logger.error("All reconnect attempts failed")
            return False
        except Exception as e:
            logger.error(f"Attempt reconnect error: {e}")
            return False

    # ─────────────────────────────────────────
    # MONITOR LOOP
    # ─────────────────────────────────────────
    def _monitor_loop(self):
        while self._running:
            try:
                is_connected = self._check_connection()

                if is_connected and not self._connected:
                    self._connected = True
                    self._last_connected = datetime.now()
                    logger.info("Connection established")

                elif not is_connected and self._connected:
                    self._connected = False
                    self._last_disconnected = datetime.now()
                    logger.warning("Connection lost — attempting reconnect")
                    self._attempt_reconnect()

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

            time.sleep(self.check_interval)

    # ─────────────────────────────────────────
    # START RECONNECT SERVICE
    # ─────────────────────────────────────────
    def start(self):
        try:
            if self._running:
                logger.info("Reconnect service already running")
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True,
                name="ReconnectServiceThread"
            )
            self._thread.start()
            logger.info("Reconnect service started")
        except Exception as e:
            logger.error(f"Start reconnect service error: {e}")

    # ─────────────────────────────────────────
    # STOP RECONNECT SERVICE
    # ─────────────────────────────────────────
    def stop(self):
        try:
            self._running = False
            logger.info("Reconnect service stopped")
        except Exception as e:
            logger.error(f"Stop reconnect service error: {e}")

    # ─────────────────────────────────────────
    # GET CONNECTION STATUS
    # ─────────────────────────────────────────
    def get_status(self) -> dict:
        try:
            return {
                "connected": self._connected,
                "running": self._running,
                "reconnect_attempts": self._reconnect_attempts,
                "last_connected": self._last_connected.strftime("%Y-%m-%d %H:%M:%S") if self._last_connected else "Never",
                "last_disconnected": self._last_disconnected.strftime("%Y-%m-%d %H:%M:%S") if self._last_disconnected else "Never"
            }
        except Exception as e:
            logger.error(f"Get connection status error: {e}")
            return {}

    # ─────────────────────────────────────────
    # FORMAT STATUS MESSAGE
    # ─────────────────────────────────────────
    def format_status_message(self) -> str:
        try:
            status = self.get_status()
            conn_status = "🟢 Connected" if status.get("connected") else "🔴 Disconnected"
            message = (
                f"📡 Connection Status\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🔌 Status: {conn_status}\n"
                f"🔢 Reconnect Attempts: {status.get('reconnect_attempts', 0)}\n"
                f"✅ Last Connected: {status.get('last_connected', 'Never')}\n"
                f"❌ Last Disconnected: {status.get('last_disconnected', 'Never')}\n"
            )
            return message
        except Exception as e:
            logger.error(f"Format status message error: {e}")
            return "⚠️ Connection status unavailable"


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
reconnect_service = ReconnectService()
