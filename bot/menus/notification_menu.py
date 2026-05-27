import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# NOTIFICATION MAIN MENU
# ─────────────────────────────────────────
def notification_menu(monitor_active: bool = False):
    markup = InlineKeyboardMarkup()
    toggle_label = "⏹ Stop Monitor" if monitor_active else "▶️ Start Monitor"
    toggle_cb = "notif_stop" if monitor_active else "notif_start"
    markup.row(
        InlineKeyboardButton(toggle_label, callback_data=toggle_cb)
    )
    markup.row(
        InlineKeyboardButton("📋 Recent Notifications", callback_data="notif_recent"),
        InlineKeyboardButton("🔄 Refresh", callback_data="menu_notifications")
    )
    markup.row(
        InlineKeyboardButton("🗑 Clear Notifications", callback_data="notif_clear_confirm"),
        InlineKeyboardButton("🔄 Sync Now", callback_data="action_sync_now")
    )
    markup.row(
        InlineKeyboardButton("📊 Queue Status", callback_data="notif_queue_status"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_main")
    )
    return markup

# ─────────────────────────────────────────
# NOTIFICATION MENU TEXT
# ─────────────────────────────────────────
def notification_menu_text(monitor_active: bool = False):
    status = "🟢 Monitoring" if monitor_active else "🔴 Stopped"
    return (
        f"🔔 <b>Notifications</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Status: {status}\n"
        f"Monitor all incoming notifications:"
    )

# ─────────────────────────────────────────
# NOTIFICATION RECENT LIST MENU
# ─────────────────────────────────────────
def notification_recent_menu(page: int = 1, total_pages: int = 1):
    markup = InlineKeyboardMarkup()
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"notif_page_{page - 1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="notif_page_info"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"notif_page_{page + 1}"))
    if nav_buttons:
        markup.row(*nav_buttons)
    markup.row(
        InlineKeyboardButton("🔄 Refresh", callback_data="notif_recent"),
        InlineKeyboardButton("🗑 Clear All", callback_data="notif_clear_confirm")
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_notifications")
    )
    return markup

# ─────────────────────────────────────────
# NOTIFICATION CONFIRM CLEAR
# ─────────────────────────────────────────
def notification_confirm_clear():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Yes, Clear All", callback_data="notif_clear"),
        InlineKeyboardButton("❌ Cancel", callback_data="menu_notifications")
    )
    return markup

# ─────────────────────────────────────────
# NOTIFICATION QUEUE STATUS MENU
# ─────────────────────────────────────────
def notification_queue_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔄 Sync Now", callback_data="action_sync_now"),
        InlineKeyboardButton("🗑 Clear Queue", callback_data="notif_clear_queue_confirm")
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_notifications")
    )
    return markup

# ─────────────────────────────────────────
# NOTIFICATION CONFIRM CLEAR QUEUE
# ─────────────────────────────────────────
def notification_confirm_clear_queue():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Yes, Clear Queue", callback_data="notif_clear_queue"),
        InlineKeyboardButton("❌ Cancel", callback_data="menu_notifications")
    )
    return markup
