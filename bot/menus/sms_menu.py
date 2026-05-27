import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# SMS MAIN MENU
# ─────────────────────────────────────────
def sms_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📨 Read SMS", callback_data="sms_read"),
        InlineKeyboardButton("🗑 Delete SMS", callback_data="sms_delete_menu")
    )
    markup.row(
        InlineKeyboardButton("📤 Send SMS", callback_data="sms_send_menu"),
        InlineKeyboardButton("↪️ Forward Settings", callback_data="sms_forward_menu")
    )
    markup.row(
        InlineKeyboardButton("📊 Queue Status", callback_data="sms_queue_status"),
        InlineKeyboardButton("🔄 Sync Now", callback_data="action_sync_now")
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_main")
    )
    return markup

# ─────────────────────────────────────────
# SMS MENU TEXT
# ─────────────────────────────────────────
def sms_menu_text():
    return (
        "📱 <b>SMS Menu</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        "Select an option:"
    )

# ─────────────────────────────────────────
# SMS READ MENU
# ─────────────────────────────────────────
def sms_read_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📋 All SMS", callback_data="sms_read_all"),
        InlineKeyboardButton("🔍 By Sender", callback_data="sms_read_by_sender")
    )
    markup.row(
        InlineKeyboardButton("⚡ OTPs Only", callback_data="sms_read_otps"),
        InlineKeyboardButton("🔄 Refresh", callback_data="sms_read")
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_sms")
    )
    return markup

# ─────────────────────────────────────────
# SMS DELETE MENU
# ─────────────────────────────────────────
def sms_delete_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🗑 Delete by ID", callback_data="sms_delete_by_id"),
        InlineKeyboardButton("🗑 Delete All", callback_data="sms_delete_all_confirm")
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_sms")
    )
    return markup

# ─────────────────────────────────────────
# SMS SEND MENU
# ─────────────────────────────────────────
def sms_send_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📤 Send New SMS", callback_data="sms_send_new"),
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_sms")
    )
    return markup

# ─────────────────────────────────────────
# SMS FORWARD MENU
# ─────────────────────────────────────────
def sms_forward_menu(number_enabled: bool = False, tg_enabled: bool = False):
    markup = InlineKeyboardMarkup()
    number_label = f"📞 Number Forward: {'🟢 ON' if number_enabled else '🔴 OFF'}"
    tg_label = f"💬 TG Forward: {'🟢 ON' if tg_enabled else '🔴 OFF'}"
    markup.row(
        InlineKeyboardButton(number_label, callback_data="sms_toggle_number_forward")
    )
    markup.row(
        InlineKeyboardButton(tg_label, callback_data="sms_toggle_tg_forward")
    )
    markup.row(
        InlineKeyboardButton("📊 Forward Status", callback_data="sms_forward_status"),
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_sms")
    )
    return markup

# ─────────────────────────────────────────
# SMS FORWARD MENU TEXT
# ─────────────────────────────────────────
def sms_forward_menu_text():
    return (
        "↪️ <b>Forward Settings</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        "Toggle optional forwarding:"
    )

# ─────────────────────────────────────────
# SMS QUEUE STATUS MENU
# ─────────────────────────────────────────
def sms_queue_status_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔄 Refresh", callback_data="sms_queue_status"),
        InlineKeyboardButton("🗑 Clear SMS Queue", callback_data="sms_clear_queue_confirm")
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_sms")
    )
    return markup

# ─────────────────────────────────────────
# SMS CONFIRM DELETE ALL
# ─────────────────────────────────────────
def sms_confirm_delete_all():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Yes, Delete All", callback_data="sms_delete_all"),
        InlineKeyboardButton("❌ Cancel", callback_data="menu_sms")
    )
    return markup

# ─────────────────────────────────────────
# SMS CONFIRM CLEAR QUEUE
# ─────────────────────────────────────────
def sms_confirm_clear_queue():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Yes, Clear Queue", callback_data="sms_clear_queue"),
        InlineKeyboardButton("❌ Cancel", callback_data="menu_sms")
    )
    return markup

# ─────────────────────────────────────────
# SMS PAGINATION MENU
# ─────────────────────────────────────────
def sms_pagination_menu(page: int, total_pages: int):
    markup = InlineKeyboardMarkup()
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"sms_page_{page - 1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="sms_page_info"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"sms_page_{page + 1}"))
    markup.row(*nav_buttons)
    markup.row(InlineKeyboardButton("🔙 Back", callback_data="menu_sms"))
    return markup

# ─────────────────────────────────────────
# FORWARD SETTINGS MENU — UPDATED
# ─────────────────────────────────────────
def sms_forward_settings_menu(number_enabled: bool = False, tg_enabled: bool = False, format_label: str = "Default"):
    markup = InlineKeyboardMarkup()
    number_label = f"📞 Number Forward: {'🟢 ON' if number_enabled else '🔴 OFF'}"
    tg_label = f"💬 Telegram Forward: {'🟢 ON' if tg_enabled else '🔴 OFF'}"
    markup.row(InlineKeyboardButton(number_label, callback_data="sms_toggle_number_forward"))
    markup.row(InlineKeyboardButton("📱 Manage Forward Numbers", callback_data="fwd_num_list"))
    markup.row(InlineKeyboardButton(tg_label, callback_data="sms_toggle_tg_forward"))
    markup.row(InlineKeyboardButton("💬 Manage Telegram Targets", callback_data="fwd_tg_list"))
    markup.row(InlineKeyboardButton(f"🎨 Custom Format: {format_label}", callback_data="sms_custom_format_menu"))
    markup.row(
        InlineKeyboardButton("📊 Forward Status", callback_data="sms_forward_status"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_sms")
    )
    return markup

# ─────────────────────────────────────────
# CUSTOM FORMAT MENU
# ─────────────────────────────────────────
def sms_custom_format_menu(current_fmt: str = "default"):
    markup = InlineKeyboardMarkup()
    formats = [
        ("format1", "1️⃣ Format 1 — Simple"),
        ("format2", "2️⃣ Format 2 — Detailed"),
        ("format3", "3️⃣ Format 3 — Minimal"),
        ("format4", "4️⃣ Format 4 — OTP Focus"),
        ("format5", "✏️ Format 5 — Custom"),
    ]
    for fmt_key, fmt_label in formats:
        check = "✅" if current_fmt == fmt_key else "⬜"
        markup.row(InlineKeyboardButton(
            f"{check} {fmt_label}",
            callback_data=f"sms_select_format_{fmt_key}"
        ))
    markup.row(
        InlineKeyboardButton("🗑 Delete Format", callback_data="sms_delete_format_confirm"),
        InlineKeyboardButton("🔙 Back", callback_data="sms_forward_menu")
    )
    return markup

# ─────────────────────────────────────────
# CONFIRM DELETE FORMAT
# ─────────────────────────────────────────
def sms_confirm_delete_format(format_label: str = ""):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Yes Delete", callback_data="sms_delete_format"),
        InlineKeyboardButton("❌ Cancel", callback_data="sms_custom_format_menu")
    )
    return markup

# ─────────────────────────────────────────
# SET TELEGRAM TARGET MENU
# ─────────────────────────────────────────
def sms_set_tg_target_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔙 Back", callback_data="sms_forward_menu"))
    return markup


# ─────────────────────────────────────────
# FORWARD NUMBERS MENU
# ─────────────────────────────────────────
def forward_numbers_menu(numbers: list):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("➕ Add Number", callback_data="fwd_num_add"))
    if numbers:
        markup.row(InlineKeyboardButton("✏️ Edit Number", callback_data="fwd_num_edit"))
        markup.row(InlineKeyboardButton("🗑 Delete Number", callback_data="fwd_num_delete"))
    markup.row(InlineKeyboardButton("🔙 Back", callback_data="sms_forward_menu"))
    return markup


# ─────────────────────────────────────────
# SELECT NUMBER TO EDIT MENU
# ─────────────────────────────────────────
def select_number_menu(numbers: list, action: str):
    markup = InlineKeyboardMarkup()
    for n in numbers:
        markup.row(InlineKeyboardButton(
            n["number"],
            callback_data=f"fwd_num_{action}_{n['number']}"
        ))
    markup.row(InlineKeyboardButton("🔙 Back", callback_data="fwd_num_list"))
    return markup


# ─────────────────────────────────────────
# CONFIRM DELETE NUMBER MENU
# ─────────────────────────────────────────
def confirm_delete_number_menu(number: str):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Yes Delete", callback_data=f"fwd_num_confirm_delete_{number}"),
        InlineKeyboardButton("❌ Cancel", callback_data="fwd_num_list")
    )
    return markup


# ─────────────────────────────────────────
# TELEGRAM TARGETS MENU
# ─────────────────────────────────────────
def telegram_targets_menu(targets: list):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("➕ Add Target", callback_data="fwd_tg_add"))
    if targets:
        markup.row(InlineKeyboardButton("✏️ Edit Target", callback_data="fwd_tg_edit"))
        markup.row(InlineKeyboardButton("🗑 Delete Target", callback_data="fwd_tg_delete"))
    markup.row(InlineKeyboardButton("🔙 Back", callback_data="sms_forward_menu"))
    return markup


# ─────────────────────────────────────────
# SELECT TELEGRAM TARGET MENU
# ─────────────────────────────────────────
def select_target_menu(targets: list, action: str):
    markup = InlineKeyboardMarkup()
    for t in targets:
        from bot.services.forward_manager import forward_manager
        emoji = forward_manager.get_type_emoji(t.get("target_type", "unknown"))
        markup.row(InlineKeyboardButton(
            f"{t['target']} {emoji}",
            callback_data=f"fwd_tg_{action}_{t['target']}"
        ))
    markup.row(InlineKeyboardButton("🔙 Back", callback_data="fwd_tg_list"))
    return markup


# ─────────────────────────────────────────
# CONFIRM DELETE TARGET MENU
# ─────────────────────────────────────────
def confirm_delete_target_menu(target: str):
    markup = InlineKeyboardMarkup()
    safe = target.replace("@", "AT_").replace("-", "MINUS_")
    markup.row(
        InlineKeyboardButton("✅ Yes Delete", callback_data=f"fwd_tg_confirm_delete_{safe}"),
        InlineKeyboardButton("❌ Cancel", callback_data="fwd_tg_list")
    )
    return markup
