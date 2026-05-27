import logging
from bot.database.db_manager import db
from bot.menus.contact_menu import (
    contact_menu, contact_menu_text,
    contact_pagination_menu, contact_search_result_menu
)
from bot.menus.main_menu import back_to_main

logger = logging.getLogger(__name__)

CONTACTS_PER_PAGE = 8

# ─────────────────────────────────────────
# REGISTER CONTACT HANDLERS
# ─────────────────────────────────────────
def register_contact_handlers(bot):

    # ── OPEN CONTACTS MENU ──
    @bot.callback_query_handler(func=lambda c: c.data == "menu_contacts")
    def handle_contact_menu(call):
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=contact_menu_text(),
                reply_markup=contact_menu(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Contact menu error: {e}")

    # ── ALL CONTACTS ──
    @bot.callback_query_handler(func=lambda c: c.data in ["contact_all"] or c.data.startswith("contact_page_"))
    def handle_contact_all(call):
        try:
            page = 1
            if call.data.startswith("contact_page_"):
                page = int(call.data.split("_")[-1])

            all_contacts = db.get_all_contacts()
            if not all_contacts:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="📭 <b>No contacts found</b>\n\nNo contacts synced yet.",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
                return

            total_pages = max(1, (len(all_contacts) + CONTACTS_PER_PAGE - 1) // CONTACTS_PER_PAGE)
            page = max(1, min(page, total_pages))
            start = (page - 1) * CONTACTS_PER_PAGE
            end = start + CONTACTS_PER_PAGE
            page_contacts = all_contacts[start:end]

            text = f"👥 <b>Contacts</b> — Page {page}/{total_pages}\n━━━━━━━━━━━━━━━━\n"
            for i, contact in enumerate(page_contacts, start + 1):
                text += (
                    f"{i}. 👤 <b>{contact['name']}</b>\n"
                    f"   📞 {contact['number']}\n"
                )
                if contact.get('email'):
                    text += f"   📧 {contact['email']}\n"
                text += "\n"

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=contact_pagination_menu(page, total_pages),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"All contacts error: {e}")

    # ── SEARCH CONTACT ──
    @bot.callback_query_handler(func=lambda c: c.data == "contact_search")
    def handle_contact_search(call):
        try:
            msg = bot.send_message(
                chat_id=call.message.chat.id,
                text="🔍 <b>Search Contact</b>\n━━━━━━━━━━━━━━━━\nSend name or number to search:",
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg, process_contact_search)
        except Exception as e:
            logger.error(f"Contact search error: {e}")

    def process_contact_search(message):
        try:
            query = message.text.strip()
            results = db.search_contact(query)
            if not results:
                bot.send_message(
                    chat_id=message.chat.id,
                    text=f"📭 <b>No contacts found for:</b> {query}",
                    reply_markup=contact_search_result_menu(),
                    parse_mode="HTML"
                )
                return

            text = f"🔍 <b>Results for:</b> {query}\n━━━━━━━━━━━━━━━━\n"
            for i, contact in enumerate(results[:10], 1):
                text += (
                    f"{i}. 👤 <b>{contact['name']}</b>\n"
                    f"   📞 {contact['number']}\n"
                )
                if contact.get('email'):
                    text += f"   📧 {contact['email']}\n"
                text += "\n"

            bot.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=contact_search_result_menu(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Process contact search error: {e}")
