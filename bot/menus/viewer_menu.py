import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# INPUT VIEWER MAIN MENU
# ─────────────────────────────────────────
def viewer_menu(viewer_active: bool = False):
    markup = InlineKeyboardMarkup()
    toggle_label = "⏹ Stop Viewer" if viewer_active else "▶️ Start Viewer"
    toggle_cb = "viewer_stop" if viewer_active else "viewer_start"
    markup.row(
        InlineKeyboardButton(toggle_label, callback_data=toggle_cb)
    )
    markup.row(
        InlineKeyboardButton("➕ Add App", callback_data="viewer_add_app"),
        InlineKeyboardButton("➖ Remove App", callback_data="viewer_remove_app")
    )
    markup.row(
        InlineKeyboardButton("📋 Focused Apps", callback_data="viewer_list_apps"),
        InlineKeyboardButton("📜 View Logs", callback_data="viewer_view_logs")
    )
    markup.row(
        InlineKeyboardButton("🗑 Clear Logs", callback_data="viewer_clear_logs_confirm"),
        InlineKeyboardButton("🔄 Sync Now", callback_data="action_sync_now")
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_main")
    )
    return markup

# ─────────────────────────────────────────
# VIEWER MENU TEXT
# ─────────────────────────────────────────
def viewer_menu_text(viewer_active: bool = False):
    status = "🟢 Active" if viewer_active else "🔴 Inactive"
    return (
        f"👁 <b>Input Viewer</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Status: {status}\n"
        f"View what you type on your phone via Telegram:"
    )

# ─────────────────────────────────────────
# VIEWER FOCUSED APPS LIST MENU
# ─────────────────────────────────────────
def viewer_apps_menu(apps: list):
    markup = InlineKeyboardMarkup()
    if apps:
        for app in apps:
            markup.row(
                InlineKeyboardButton(
                    f"📲 {app['app_name']}",
                    callback_data=f"viewer_app_info_{app['app_name']}"
                ),
                InlineKeyboardButton(
                    "➖ Remove",
                    callback_data=f"viewer_remove_specific_{app['app_name']}"
                )
            )
    markup.row(
        InlineKeyboardButton("➕ Add New App", callback_data="viewer_add_app")
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_viewer")
    )
    return markup

# ─────────────────────────────────────────
# VIEWER LOGS MENU
# ─────────────────────────────────────────
def viewer_logs_menu(page: int = 1, total_pages: int = 1):
    markup = InlineKeyboardMarkup()
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"viewer_logs_page_{page - 1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="viewer_logs_page_info"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"viewer_logs_page_{page + 1}"))
    if nav_buttons:
        markup.row(*nav_buttons)
    markup.row(
        InlineKeyboardButton("🔄 Refresh", callback_data="viewer_view_logs"),
        InlineKeyboardButton("🗑 Clear Logs", callback_data="viewer_clear_logs_confirm")
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_viewer")
    )
    return markup

# ─────────────────────────────────────────
# VIEWER CONFIRM CLEAR LOGS
# ─────────────────────────────────────────
def viewer_confirm_clear_logs():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Yes, Clear", callback_data="viewer_clear_logs"),
        InlineKeyboardButton("❌ Cancel", callback_data="menu_viewer")
    )
    return markup

# ─────────────────────────────────────────
# VIEWER OFFLINE QUEUE MENU
# ─────────────────────────────────────────
def viewer_queue_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔄 Sync Now", callback_data="action_sync_now"),
        InlineKeyboardButton("🗑 Clear Queue", callback_data="viewer_clear_queue_confirm")
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_viewer")
    )
    return markup
