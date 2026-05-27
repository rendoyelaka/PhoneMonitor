import logging
import threading
import time
import requests
from datetime import datetime
from bot.services.queue_manager import queue_manager
from bot.config import QUEUE_SYNC_INTERVAL

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# SYNC SERVICE CLASS
# ─────────────────────────────────────────
class SyncService:
    def __init__(self):
        self.sync_interval = QUEUE_SYNC_INTERVAL
        self._running = False
        self._thread = None
        self._last_sync = None
        self._sync_count = 0
        self._online = False

    # ─────────────────────────────────────────
    # CHECK INTERNET CONNECTION
    # ─────────────────────────────────────────
    def check_connection(self) -> bool:
        try:
            requests.get("https://api.telegram.org", timeout=5)
            if not self._online:
                self._online = True
                logger.info("Connection restored — starting sync")
                self._on_connection_restored()
            return True
        except Exception:
            if self._online:
                self._online = False
                logger.warning("Connection lost — switching to offline mode")
            return False

    # ─────────────────────────────────────────
    # ON CONNECTION RESTORED
    # ─────────────────────────────────────────
    def _on_connection_restored(self):
        try:
            logger.info("Running immediate sync after reconnection")
            queue_manager.sync_all_queues()
        except Exception as e:
            logger.error(f"On connection restored error: {e}")

    # ─────────────────────────────────────────
    # RUN SYNC CYCLE
    # ─────────────────────────────────────────
    def _run_sync_cycle(self):
        try:
            is_online = self.check_connection()
            if is_online:
                result = queue_manager.sync_all_queues()
                if result.get("success"):
                    self._last_sync = datetime.now()
                    self._sync_count += 1
                    logger.info(f"Sync cycle {self._sync_count} complete")
        except Exception as e:
            logger.error(f"Sync cycle error: {e}")

    # ─────────────────────────────────────────
    # START SYNC SERVICE
    # ─────────────────────────────────────────
    def start(self):
        try:
            if self._running:
                logger.info("Sync service already running")
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._sync_loop,
                daemon=True,
                name="SyncServiceThread"
            )
            self._thread.start()
            logger.info("Sync service started")
        except Exception as e:
            logger.error(f"Start sync service error: {e}")

    # ─────────────────────────────────────────
    # STOP SYNC SERVICE
    # ─────────────────────────────────────────
    def stop(self):
        try:
            self._running = False
            logger.info("Sync service stopped")
        except Exception as e:
            logger.error(f"Stop sync service error: {e}")

    # ─────────────────────────────────────────
    # SYNC LOOP
    # ─────────────────────────────────────────
    def _sync_loop(self):
        while self._running:
            try:
                self._run_sync_cycle()
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
            time.sleep(self.sync_interval)

    # ─────────────────────────────────────────
    # MANUAL SYNC NOW
    # ─────────────────────────────────────────
    def sync_now(self) -> dict:
        try:
            is_online = self.check_connection()
            if not is_online:
                return {
                    "success": False,
                    "reason": "offline",
                    "message": "⚠️ No internet connection"
                }
            result = queue_manager.sync_all_queues()
            if result.get("success"):
                self._last_sync = datetime.now()
                self._sync_count += 1
            return result
        except Exception as e:
            logger.error(f"Sync now error: {e}")
            return {"success": False, "reason": str(e)}

    # ─────────────────────────────────────────
    # GET SYNC STATUS
    # ─────────────────────────────────────────
    def get_sync_status(self) -> dict:
        try:
            return {
                "running": self._running,
                "online": self._online,
                "last_sync": self._last_sync.strftime("%Y-%m-%d %H:%M:%S") if self._last_sync else "Never",
                "sync_count": self._sync_count,
                "sync_interval": self.sync_interval
            }
        except Exception as e:
            logger.error(f"Get sync status error: {e}")
            return {}

    # ─────────────────────────────────────────
    # FORMAT SYNC STATUS MESSAGE
    # ─────────────────────────────────────────
    def format_sync_status_message(self) -> str:
        try:
            status = self.get_sync_status()
            online_status = "🟢 Online" if status.get("online") else "🔴 Offline"
            running_status = "▶️ Running" if status.get("running") else "⏹ Stopped"
            message = (
                f"🔄 Sync Service Status\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📡 Connection: {online_status}\n"
                f"⚙️ Service: {running_status}\n"
                f"🕐 Last Sync: {status.get('last_sync', 'Never')}\n"
                f"🔢 Total Syncs: {status.get('sync_count', 0)}\n"
                f"⏱ Interval: {status.get('sync_interval', 30)}s\n"
            )
            return message
        except Exception as e:
            logger.error(f"Format sync status message error: {e}")
            return "⚠️ Sync status unavailable"


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
sync_service = SyncService()
