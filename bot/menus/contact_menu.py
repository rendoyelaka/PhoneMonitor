import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# CONTACTS MAIN MENU
# ─────────────────────────────────────────
def contact_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📋 All Contacts", callback_data="contact_all"),
        InlineKeyboardButton("🔍 Search", callback_data="contact_search")
    )
    markup.row(
        InlineKeyboardButton("🔄 Refresh", callback_data="menu_contacts"),
        InlineKeyboardButton("🔙 Back", callback_data="menu_main")
    )
    return markup

# ─────────────────────────────────────────
# CONTACTS MENU TEXT
# ─────────────────────────────────────────
def contact_menu_text():
    return (
        "👥 <b>Contacts Menu</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        "Select an option:"
    )

# ─────────────────────────────────────────
# CONTACTS PAGINATION MENU
# ─────────────────────────────────────────
def contact_pagination_menu(page: int, total_pages: int):
    markup = InlineKeyboardMarkup()
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"contact_page_{page - 1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="contact_page_info"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"contact_page_{page + 1}"))
    markup.row(*nav_buttons)
    markup.row(InlineKeyboardButton("🔙 Back", callback_data="menu_contacts"))
    return markup

# ─────────────────────────────────────────
# CONTACT SEARCH RESULT MENU
# ─────────────────────────────────────────
def contact_search_result_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔍 Search Again", callback_data="contact_search"),
        InlineKeyboardButton("📋 All Contacts", callback_data="contact_all")
    )
    markup.row(
        InlineKeyboardButton("🔙 Back", callback_data="menu_contacts")
    )
    return markup
