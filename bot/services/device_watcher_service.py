import logging
import threading
import time
import requests
from datetime import datetime
from bot.database.db_manager import db
from bot.config import BOT_TOKEN, OWNER_ID

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# DEVICE WATCHER SERVICE
# Runs every 60 seconds
# Checks all connected devices
# If any device offline → sends restart signal
# If device goes offline → alerts owner
# Toggle ON/OFF from Telegram bot
# ─────────────────────────────────────────
class DeviceWatcherService:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.owner_id = OWNER_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self._running = False
        self._thread = None
        self.check_interval = 60  # Check every 60 seconds
        self._alerted_offline = set()  # Track which devices already alerted
        self._device_last_seen = None  # Will be injected from webhook

    # ─────────────────────────────────────────
    # INJECT DEVICE REGISTRY FROM WEBHOOK
    # Called from main.py after webhook starts
    # ─────────────────────────────────────────
    def set_device_registry(self, device_last_seen: dict, device_registry: dict, pending_commands: dict):
        self._device_last_seen = device_last_seen
        self._device_registry = device_registry
        self._pending_commands = pending_commands

    # ─────────────────────────────────────────
    # IS AUTO RESTART ENABLED
    # ─────────────────────────────────────────
    def is_auto_restart_enabled(self) -> bool:
        try:
            return db.get_setting("auto_device_restart_enabled", "true") == "true"
        except Exception:
            return True

    # ─────────────────────────────────────────
    # IS OFFLINE ALERT ENABLED
    # ─────────────────────────────────────────
    def is_offline_alert_enabled(self) -> bool:
        try:
            return db.get_setting("device_offline_alert_enabled", "true") == "true"
        except Exception:
            return True

    # ─────────────────────────────────────────
    # GET OFFLINE THRESHOLD
    # ─────────────────────────────────────────
    def get_offline_threshold(self) -> int:
        try:
            return int(db.get_setting("device_offline_threshold_seconds", "60"))
        except Exception:
            return 60

    # ─────────────────────────────────────────
    # SEND TELEGRAM MESSAGE
    # ─────────────────────────────────────────
    def _send_message(self, text: str):
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.owner_id,
                "text": text,
                "parse_mode": "HTML"
            }
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Device watcher send message error: {e}")

    # ─────────────────────────────────────────
    # GET ALL OFFLINE DEVICES
    # ─────────────────────────────────────────
    def get_offline_devices(self) -> list:
        if not self._device_last_seen:
            return []
        now = datetime.now()
        threshold = self.get_offline_threshold()
        offline = []
        for device_id, last_seen in self._device_last_seen.items():
            diff = (now - last_seen).total_seconds()
            if diff > threshold:
                info = self._device_registry.get(device_id, {})
                offline.append({
                    "device_id": device_id,
                    "model": info.get("model", "Unknown Device"),
                    "seconds_offline": int(diff),
                    "last_seen": last_seen.strftime("%H:%M:%S")
                })
        return offline

    # ─────────────────────────────────────────
    # GET ALL ONLINE DEVICES
    # ─────────────────────────────────────────
    def get_online_devices(self) -> list:
        if not self._device_last_seen:
            return []
        now = datetime.now()
        threshold = self.get_offline_threshold()
        online = []
        for device_id, last_seen in self._device_last_seen.items():
            diff = (now - last_seen).total_seconds()
            if diff <= threshold:
                info = self._device_registry.get(device_id, {})
                online.append({
                    "device_id": device_id,
                    "model": info.get("model", "Unknown Device"),
                    "last_seen": last_seen.strftime("%H:%M:%S")
                })
        return online

    # ─────────────────────────────────────────
    # SEND RESTART SIGNAL TO ONE DEVICE
    # ─────────────────────────────────────────
    def send_restart_signal(self, device_id: str):
        try:
            if self._pending_commands is not None:
                self._pending_commands[device_id] = "reconnect"
                logger.info(f"Restart signal sent to: {device_id}")
        except Exception as e:
            logger.error(f"Send restart signal error: {e}")

    # ─────────────────────────────────────────
    # RESTART ALL OFFLINE DEVICES
    # Called manually from Telegram button
    # ─────────────────────────────────────────
    def restart_all_offline(self) -> dict:
        try:
            offline = self.get_offline_devices()
            if not offline:
                return {"success": True, "count": 0, "devices": []}
            for device in offline:
                self.send_restart_signal(device["device_id"])
            logger.info(f"Restart signal sent to {len(offline)} offline devices")
            return {
                "success": True,
                "count": len(offline),
                "devices": [d["model"] for d in offline]
            }
        except Exception as e:
            logger.error(f"Restart all offline error: {e}")
            return {"success": False, "count": 0, "devices": []}

    # ─────────────────────────────────────────
    # CHECK AND ALERT OFFLINE DEVICES
    # Sends alert for newly offline devices
    # ─────────────────────────────────────────
    def _check_and_alert(self):
        try:
            offline = self.get_offline_devices()
            for device in offline:
                device_id = device["device_id"]
                # Only alert once per offline event
                if device_id not in self._alerted_offline:
                    self._alerted_offline.add(device_id)
                    if self.is_offline_alert_enabled():
                        mins_offline = device["seconds_offline"] // 60
                        secs_offline = device["seconds_offline"] % 60
                        self._send_message(
                            f"🔴 <b>Device Offline</b>\n"
                            f"━━━━━━━━━━━━━━━━\n"
                            f"📱 <b>{device['model']}</b>\n"
                            f"🕐 Last seen: {device['last_seen']}\n"
                            f"⏱ Offline for: {mins_offline}m {secs_offline}s\n"
                            f"━━━━━━━━━━━━━━━━\n"
                            f"{'⚡ Auto restart signal sent' if self.is_auto_restart_enabled() else '⚠️ Auto restart is OFF'}"
                        )
                    # Auto restart if enabled
                    if self.is_auto_restart_enabled():
                        self.send_restart_signal(device_id)
                        logger.info(f"Auto restart sent to: {device['model']}")

            # Clear alerted set for devices that came back online
            online_ids = {d["device_id"] for d in self.get_online_devices()}
            came_back = self._alerted_offline & online_ids
            for device_id in came_back:
                self._alerted_offline.discard(device_id)
                info = self._device_registry.get(device_id, {})
                model = info.get("model", "Unknown Device")
                if self.is_offline_alert_enabled():
                    self._send_message(
                        f"🟢 <b>Device Back Online</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📱 <b>{model}</b>\n"
                        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
                    )

        except Exception as e:
            logger.error(f"Check and alert error: {e}")

    # ─────────────────────────────────────────
    # WATCHER LOOP
    # Runs every 60 seconds
    # ─────────────────────────────────────────
    def _watcher_loop(self):
        while self._running:
            try:
                self._check_and_alert()
            except Exception as e:
                logger.error(f"Watcher loop error: {e}")
            time.sleep(self.check_interval)

    # ─────────────────────────────────────────
    # START WATCHER
    # ─────────────────────────────────────────
    def start(self):
        try:
            if self._running:
                logger.info("Device watcher already running")
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._watcher_loop,
                daemon=True,
                name="DeviceWatcherThread"
            )
            self._thread.start()
            logger.info("Device watcher started")
        except Exception as e:
            logger.error(f"Start device watcher error: {e}")

    # ─────────────────────────────────────────
    # STOP WATCHER
    # ─────────────────────────────────────────
    def stop(self):
        try:
            self._running = False
            logger.info("Device watcher stopped")
        except Exception as e:
            logger.error(f"Stop device watcher error: {e}")

    # ─────────────────────────────────────────
    # GET WATCHER STATUS
    # ─────────────────────────────────────────
    def get_status(self) -> dict:
        try:
            offline = self.get_offline_devices()
            online = self.get_online_devices()
            return {
                "running": self._running,
                "auto_restart_enabled": self.is_auto_restart_enabled(),
                "offline_alert_enabled": self.is_offline_alert_enabled(),
                "online_count": len(online),
                "offline_count": len(offline),
                "total_count": len(online) + len(offline),
                "check_interval": self.check_interval
            }
        except Exception as e:
            logger.error(f"Get watcher status error: {e}")
            return {}


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
device_watcher = DeviceWatcherService()
