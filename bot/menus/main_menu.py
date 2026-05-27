import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# MAIN MENU
# ─────────────────────────────────────────
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📱 SMS", callback_data="menu_sms"),
        InlineKeyboardButton("👥 Contacts", callback_data="menu_contacts")
    )
    markup.row(
        InlineKeyboardButton("👁 Input Viewer", callback_data="menu_viewer"),
        InlineKeyboardButton("🔔 Notifications", callback_data="menu_notifications")
    )
    markup.row(
        InlineKeyboardButton("📊 Queue Status", callback_data="menu_queue_status"),
        InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")
    )
    markup.row(
        InlineKeyboardButton("📡 Connection", callback_data="menu_connection"),
        InlineKeyboardButton("🔄 Sync Now", callback_data="action_sync_now")
    )
    markup.row(
        InlineKeyboardButton("📱 Devices", callback_data="menu_devices")
    )
    return markup

# ─────────────────────────────────────────
# MAIN MENU MESSAGE TEXT
# ─────────────────────────────────────────
def main_menu_text():
    return (
        "🏠 <b>Main Menu</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        "Select an option below:"
    )

# ─────────────────────────────────────────
# SETTINGS MENU
# ─────────────────────────────────────────
def settings_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📴 Offline Mode: ON", callback_data="toggle_offline_mode"),
    )
    markup.row(
        InlineKeyboardButton("🔄 Auto Sync: ON", callback_data="toggle_auto_sync"),
    )
    markup.row(
        InlineKeyboardButton("🗑 Clear All Queues", callback_data="action_clear_queues"),
    )
    markup.row(
        InlineKeyboardButton("📊 Delivery Stats", callback_data="action_delivery_stats"),
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_main")
    )
    return markup

# ─────────────────────────────────────────
# SETTINGS MENU TEXT
# ─────────────────────────────────────────
def settings_menu_text():
    return (
        "⚙️ <b>Settings</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        "Manage bot settings:"
    )

# ─────────────────────────────────────────
# QUEUE STATUS MENU
# ─────────────────────────────────────────
def queue_status_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔄 Refresh", callback_data="menu_queue_status"),
        InlineKeyboardButton("🗑 Clear Queue", callback_data="action_clear_queues")
    )
    markup.row(
        InlineKeyboardButton("📊 Delivery Stats", callback_data="action_delivery_stats")
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_main")
    )
    return markup

# ─────────────────────────────────────────
# CONNECTION MENU
# ─────────────────────────────────────────
def connection_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔄 Refresh Status", callback_data="menu_connection"),
        InlineKeyboardButton("🔌 Reconnect", callback_data="action_reconnect")
    )
    markup.row(
        InlineKeyboardButton("📡 Sync Status", callback_data="action_sync_status")
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_main")
    )
    return markup

# ─────────────────────────────────────────
# CONFIRM ACTION MENU
# ─────────────────────────────────────────
def confirm_menu(action: str, label: str):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Yes", callback_data=f"confirm_{action}"),
        InlineKeyboardButton("❌ No", callback_data="menu_main")
    )
    return markup

# ─────────────────────────────────────────
# BACK TO MAIN MENU BUTTON
# ─────────────────────────────────────────
def back_to_main():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")
    )
    return markup


# ─────────────────────────────────────────
# CONNECTED DEVICES MENU
# Shows all devices — Restart All Offline button
# Toggle auto restart ON/OFF
# ─────────────────────────────────────────
def connected_devices_menu(devices: list, auto_restart_enabled: bool = True):
    markup = InlineKeyboardMarkup()
    offline_count = sum(1 for d in devices if not d["online"])
    # Restart All Offline button — only when there are offline devices
    if offline_count > 0:
        markup.row(InlineKeyboardButton(
            f"🔄 Restart All Offline ({offline_count})",
            callback_data="device_restart_all_offline"
        ))
    # Auto restart toggle
    auto_label = f"⚡ Auto Restart: {'🟢 ON' if auto_restart_enabled else '🔴 OFF'}"
    markup.row(InlineKeyboardButton(auto_label, callback_data="toggle_auto_device_restart"))
    markup.row(InlineKeyboardButton("🔙 Back", callback_data="menu_main"))
    return markup
