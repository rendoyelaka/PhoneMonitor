import logging
from datetime import datetime
from bot.database.db_manager import db
from bot.services.sms_service import sms_service
from bot.services.forwarder_service import forwarder_service
from bot.services.queue_manager import queue_manager
from bot.utils.delivery_tracker import delivery_tracker
from bot.menus.sms_menu import (
    sms_menu, sms_menu_text, sms_read_menu, sms_delete_menu,
    sms_send_menu, sms_forward_menu, sms_forward_menu_text,
    sms_queue_status_menu, sms_confirm_delete_all,
    sms_confirm_clear_queue, sms_pagination_menu
)
from bot.menus.main_menu import back_to_main

logger = logging.getLogger(__name__)

SMS_PER_PAGE = 5

# ─────────────────────────────────────────
# STATE TRACKER FOR MULTI-STEP INPUTS
# ─────────────────────────────────────────
sms_state = {}

# ─────────────────────────────────────────
# REGISTER SMS HANDLERS
# ─────────────────────────────────────────
def register_sms_handlers(bot):

    # ── OPEN SMS MENU ──
    @bot.callback_query_handler(func=lambda c: c.data == "menu_sms")
    def handle_sms_menu(call):
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=sms_menu_text(),
                reply_markup=sms_menu(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"SMS menu error: {e}")

    # ── READ SMS MENU ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_read")
    def handle_sms_read(call):
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="📨 <b>Read SMS</b>\n━━━━━━━━━━━━━━━━\nSelect read option:",
                reply_markup=sms_read_menu(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"SMS read menu error: {e}")

    # ── READ ALL SMS ──
    @bot.callback_query_handler(func=lambda c: c.data in ["sms_read_all"] or c.data.startswith("sms_page_"))
    def handle_sms_read_all(call):
        try:
            page = 1
            if call.data.startswith("sms_page_"):
                page = int(call.data.split("_")[-1])

            all_sms = sms_service.read_all_sms(limit=100)
            if not all_sms:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="📭 <b>No SMS found in inbox</b>",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
                return

            total_pages = max(1, (len(all_sms) + SMS_PER_PAGE - 1) // SMS_PER_PAGE)
            page = max(1, min(page, total_pages))
            start = (page - 1) * SMS_PER_PAGE
            end = start + SMS_PER_PAGE
            page_sms = all_sms[start:end]

            text = f"📱 <b>SMS Inbox</b> — Page {page}/{total_pages}\n━━━━━━━━━━━━━━━━\n"
            for i, sms in enumerate(page_sms, start + 1):
                text += (
                    f"{i}. 👤 <b>{sms['sender']}</b>\n"
                    f"   💬 {sms['message'][:60]}{'...' if len(sms['message']) > 60 else ''}\n"
                    f"   🕐 {sms['timestamp']}\n"
                    f"   🆔 <code>{sms['sms_id']}</code>\n\n"
                )

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=sms_pagination_menu(page, total_pages),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Read all SMS error: {e}")

    # ── READ SMS BY SENDER ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_read_by_sender")
    def handle_sms_read_by_sender(call):
        try:
            sms_state[call.from_user.id] = "awaiting_sender"
            msg = bot.send_message(
                chat_id=call.message.chat.id,
                text="🔍 <b>Search by Sender</b>\n━━━━━━━━━━━━━━━━\nSend the sender name or number:",
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg, process_sms_by_sender)
        except Exception as e:
            logger.error(f"SMS read by sender error: {e}")

    def process_sms_by_sender(message):
        try:
            sender = message.text.strip()
            sms_list = sms_service.read_sms_by_sender(sender)
            if not sms_list:
                bot.send_message(
                    chat_id=message.chat.id,
                    text=f"📭 No SMS found from: <b>{sender}</b>",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
                return
            text = f"📱 <b>SMS from {sender}</b>\n━━━━━━━━━━━━━━━━\n"
            for i, sms in enumerate(sms_list[:10], 1):
                text += (
                    f"{i}. 💬 {sms['message'][:80]}{'...' if len(sms['message']) > 80 else ''}\n"
                    f"   🕐 {sms['timestamp']}\n\n"
                )
            bot.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=back_to_main(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Process SMS by sender error: {e}")

    # ── READ OTPs ONLY ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_read_otps")
    def handle_sms_read_otps(call):
        try:
            all_sms = sms_service.read_all_sms(limit=100)
            otp_keywords = ["otp", "one time", "verification", "verify", "code", "pin", "password", "token"]
            otps = [s for s in all_sms if any(k in s['message'].lower() for k in otp_keywords)]
            if not otps:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="📭 <b>No OTP messages found</b>",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
                return
            text = f"⚡ <b>OTP Messages ({len(otps)})</b>\n━━━━━━━━━━━━━━━━\n"
            for i, sms in enumerate(otps[:10], 1):
                text += (
                    f"{i}. 👤 <b>{sms['sender']}</b>\n"
                    f"   💬 {sms['message'][:80]}\n"
                    f"   🕐 {sms['timestamp']}\n\n"
                )
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=back_to_main(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Read OTPs error: {e}")

    # ── DELETE SMS MENU ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_delete_menu")
    def handle_sms_delete_menu(call):
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="🗑 <b>Delete SMS</b>\n━━━━━━━━━━━━━━━━\nSelect delete option:",
                reply_markup=sms_delete_menu(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"SMS delete menu error: {e}")

    # ── DELETE SMS BY ID ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_delete_by_id")
    def handle_sms_delete_by_id(call):
        try:
            msg = bot.send_message(
                chat_id=call.message.chat.id,
                text="🗑 <b>Delete SMS by ID</b>\n━━━━━━━━━━━━━━━━\nSend the SMS ID to delete:\n(Find ID under each SMS in inbox)",
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg, process_delete_sms_by_id)
        except Exception as e:
            logger.error(f"Delete SMS by ID error: {e}")

    def process_delete_sms_by_id(message):
        try:
            sms_id = message.text.strip()
            success = sms_service.delete_sms(sms_id)
            if success:
                bot.send_message(
                    chat_id=message.chat.id,
                    text=f"✅ SMS deleted successfully\n🆔 ID: <code>{sms_id}</code>",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id=message.chat.id,
                    text=f"❌ SMS not found or delete failed\n🆔 ID: <code>{sms_id}</code>",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Process delete SMS error: {e}")

    # ── DELETE ALL SMS CONFIRM ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_delete_all_confirm")
    def handle_sms_delete_all_confirm(call):
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="⚠️ <b>Delete ALL SMS?</b>\n━━━━━━━━━━━━━━━━\nThis will delete all SMS from the database.\nAre you sure?",
                reply_markup=sms_confirm_delete_all(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"SMS delete all confirm error: {e}")

    # ── DELETE ALL SMS ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_delete_all")
    def handle_sms_delete_all(call):
        try:
            with db.get_connection() as conn:
                conn.execute("DELETE FROM sms_inbox")
                conn.commit()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ <b>All SMS deleted successfully</b>",
                reply_markup=back_to_main(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Delete all SMS error: {e}")

    # ── SEND SMS MENU ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_send_menu")
    def handle_sms_send_menu(call):
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="📤 <b>Send SMS</b>\n━━━━━━━━━━━━━━━━\nSelect option:",
                reply_markup=sms_send_menu(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"SMS send menu error: {e}")

    # ── SEND NEW SMS ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_send_new")
    def handle_sms_send_new(call):
        try:
            msg = bot.send_message(
                chat_id=call.message.chat.id,
                text="📤 <b>Send SMS</b>\n━━━━━━━━━━━━━━━━\nSend recipient number:\n(Format: +91XXXXXXXXXX)",
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg, process_sms_send_recipient)
        except Exception as e:
            logger.error(f"Send SMS error: {e}")

    def process_sms_send_recipient(message):
        try:
            recipient = message.text.strip()
            sms_state[message.from_user.id] = {"step": "awaiting_message", "recipient": recipient}
            msg = bot.send_message(
                chat_id=message.chat.id,
                text=f"📤 <b>Send SMS</b>\n━━━━━━━━━━━━━━━━\nTo: <b>{recipient}</b>\nNow send your message:",
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg, process_sms_send_message)
        except Exception as e:
            logger.error(f"Process SMS recipient error: {e}")

    def process_sms_send_message(message):
        try:
            state = sms_state.get(message.from_user.id, {})
            recipient = state.get("recipient", "")
            sms_text = message.text.strip()
            success = sms_service.send_sms(recipient, sms_text)
            if success:
                bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"✅ <b>SMS Sent</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📞 To: {recipient}\n"
                        f"💬 Message: {sms_text}\n"
                        f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}"
                    ),
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ <b>SMS send failed</b>",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
            sms_state.pop(message.from_user.id, None)
        except Exception as e:
            logger.error(f"Process SMS message error: {e}")

    # ── SMS FORWARD MENU — Full version with Set Target + Custom Format ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_forward_menu")
    def handle_sms_forward_menu(call):
        try:
            from bot.menus.sms_menu import sms_forward_settings_menu
            from bot.services.forwarder_service import FORMAT_LABELS
            number_enabled = forwarder_service.is_number_forward_enabled()
            tg_enabled = forwarder_service.is_tg_forward_enabled()
            fmt = forwarder_service.get_current_format()
            fmt_label = FORMAT_LABELS.get(fmt, "Default")
            tg_status = forwarder_service.get_tg_target_status()
            active_target = forwarder_service.resolve_tg_target()
            text = (
                f"↪️ <b>Forward Settings</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📞 Number Forward: {'🟢 ON' if number_enabled else '🔴 OFF'}\n"
                f"💬 Telegram Forward: {'🟢 ON' if tg_enabled else '🔴 OFF'}\n"
                f"📌 Target: {active_target or 'Not set'}\n"
                f"🎨 Format: {fmt_label}\n"
            )
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=sms_forward_settings_menu(number_enabled, tg_enabled, fmt_label),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"SMS forward menu error: {e}")

    # ── SMS QUEUE STATUS ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_queue_status")
    def handle_sms_queue_status(call):
        try:
            stats = delivery_tracker.format_stats_message()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=stats,
                reply_markup=sms_queue_status_menu(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"SMS queue status error: {e}")

    # ── CLEAR SMS QUEUE CONFIRM ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_clear_queue_confirm")
    def handle_sms_clear_queue_confirm(call):
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="⚠️ <b>Clear SMS Queue?</b>\n━━━━━━━━━━━━━━━━\nAll pending SMS in queue will be cleared.\nAre you sure?",
                reply_markup=sms_confirm_clear_queue(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"SMS clear queue confirm error: {e}")

    # ── CLEAR SMS QUEUE ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_clear_queue")
    def handle_sms_clear_queue(call):
        try:
            with db.get_connection() as conn:
                conn.execute("DELETE FROM sms_queue")
                conn.commit()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ <b>SMS Queue cleared successfully</b>",
                reply_markup=back_to_main(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Clear SMS queue error: {e}")


# ─────────────────────────────────────────
# FORWARD & CUSTOM FORMAT HANDLERS
# Added below existing register_sms_handlers
# Call register_sms_forward_handlers(bot)
# from main.py after register_sms_handlers
# ─────────────────────────────────────────
def register_sms_forward_handlers(bot):
    from bot.menus.sms_menu import (
        sms_forward_settings_menu, sms_custom_format_menu,
        sms_confirm_delete_format, sms_set_tg_target_menu
    )
    from bot.services.forwarder_service import forwarder_service, FORMAT_LABELS, FORMAT_CUSTOM
    from bot.menus.main_menu import back_to_main


    # ── TOGGLE NUMBER FORWARD ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_toggle_number_forward")
    def handle_toggle_number_forward(call):
        try:
            current = forwarder_service.is_number_forward_enabled()
            if current:
                forwarder_service.disable_number_forward()
                status = "🔴 Disabled"
            else:
                forwarder_service.enable_number_forward()
                status = "🟢 Enabled"
            number_enabled = forwarder_service.is_number_forward_enabled()
            tg_enabled = forwarder_service.is_tg_forward_enabled()
            fmt_label = FORMAT_LABELS.get(forwarder_service.get_current_format(), "Default")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"📞 <b>Number Forward {status}</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Auto forward all SMS to number and Telegram:"
                ),
                reply_markup=sms_forward_settings_menu(number_enabled, tg_enabled, fmt_label),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Toggle number forward error: {e}")

    # ── TOGGLE TELEGRAM FORWARD ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_toggle_tg_forward")
    def handle_toggle_tg_forward(call):
        try:
            current = forwarder_service.is_tg_forward_enabled()
            if current:
                forwarder_service.disable_tg_forward()
                status = "🔴 Disabled"
            else:
                forwarder_service.enable_tg_forward()
                status = "🟢 Enabled"
            number_enabled = forwarder_service.is_number_forward_enabled()
            tg_enabled = forwarder_service.is_tg_forward_enabled()
            fmt_label = FORMAT_LABELS.get(forwarder_service.get_current_format(), "Default")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"💬 <b>Telegram Forward {status}</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Auto forward all SMS to number and Telegram:"
                ),
                reply_markup=sms_forward_settings_menu(number_enabled, tg_enabled, fmt_label),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Toggle TG forward error: {e}")


    # ── CUSTOM FORMAT MENU ──
    @bot.callback_query_handler(func=lambda c: c.data in ["sms_custom_format_menu", "sms_format_menu_back"])
    def handle_custom_format_menu(call):
        try:
            current_fmt = forwarder_service.get_current_format()
            fmt_label = FORMAT_LABELS.get(current_fmt, "Default")
            preview = forwarder_service.get_format_preview(current_fmt)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"🎨 <b>Custom Format</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Select format for Auto Forward:\n\n"
                    f"✅ Current: <b>{fmt_label}</b>\n\n"
                    f"<b>Preview:</b>\n"
                    f"<code>{preview}</code>"
                ),
                reply_markup=sms_custom_format_menu(current_fmt),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Custom format menu error: {e}")

    # ── SELECT FORMAT ──
    @bot.callback_query_handler(func=lambda c: c.data.startswith("sms_select_format_"))
    def handle_select_format(call):
        try:
            fmt = call.data.replace("sms_select_format_", "")
            if fmt == FORMAT_CUSTOM:
                # Ask for custom text
                msg = bot.send_message(
                    chat_id=call.message.chat.id,
                    text=(
                        f"✏️ <b>Custom Format</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"Available tags:\n\n"
                        f"<code>{{sender}}</code>  → HDFC Bank\n"
                        f"<code>{{message}}</code> → Your OTP is 482910\n"
                        f"<code>{{date}}</code>    → 27/05/2026\n"
                        f"<code>{{time}}</code>    → 14:31:45\n"
                        f"<code>{{otp}}</code>     → 482910\n\n"
                        f"Send your custom format now:\n"
                        f"Example: <code>SMS from {{sender}}: {{message}} at {{time}}</code>"
                    ),
                    parse_mode="HTML"
                )
                bot.register_next_step_handler(msg, process_custom_format_input)
                return

            forwarder_service.set_forward_format(fmt)
            fmt_label = FORMAT_LABELS.get(fmt, "Default")
            preview = forwarder_service.get_format_preview(fmt)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"🎨 <b>Custom Format</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Select format for Auto Forward:\n\n"
                    f"✅ Current: <b>{fmt_label}</b>\n\n"
                    f"<b>Preview:</b>\n"
                    f"<code>{preview}</code>"
                ),
                reply_markup=sms_custom_format_menu(fmt),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Select format error: {e}")

    def process_custom_format_input(message):
        try:
            custom_text = message.text.strip()
            forwarder_service.set_custom_format_text(custom_text)
            preview = forwarder_service.get_format_preview(FORMAT_CUSTOM)
            bot.send_message(
                chat_id=message.chat.id,
                text=(
                    f"✅ <b>Custom Format Saved</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"<b>Preview:</b>\n"
                    f"<code>{preview}</code>"
                ),
                reply_markup=back_to_main(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Process custom format input error: {e}")

    # ── CONFIRM DELETE FORMAT ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_delete_format_confirm")
    def handle_delete_format_confirm(call):
        try:
            current_fmt = forwarder_service.get_current_format()
            fmt_label = FORMAT_LABELS.get(current_fmt, "Default")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"⚠️ <b>Delete {fmt_label}?</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Format will be removed.\n"
                    f"Auto forward will use Default."
                ),
                reply_markup=sms_confirm_delete_format(fmt_label),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Delete format confirm error: {e}")

    # ── DELETE FORMAT ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_delete_format")
    def handle_delete_format(call):
        try:
            forwarder_service.delete_forward_format()
            preview = forwarder_service.get_format_preview("default")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"✅ <b>Format Deleted</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Now using Default format.\n\n"
                    f"<b>Preview:</b>\n"
                    f"<code>{preview}</code>"
                ),
                reply_markup=sms_custom_format_menu("default"),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Delete format error: {e}")

    # ── FORWARD STATUS ──
    @bot.callback_query_handler(func=lambda c: c.data == "sms_forward_status")
    def handle_sms_forward_status(call):
        try:
            text = forwarder_service.format_forwarder_status()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=back_to_main(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Forward status error: {e}")


# ─────────────────────────────────────────
# SET INDIAN NUMBER HANDLER
# Added separately — sets forward number
# ─────────────────────────────────────────
def register_sms_number_handler(bot):
    from bot.database.db_manager import db
    from bot.menus.main_menu import back_to_main

    @bot.callback_query_handler(func=lambda c: c.data == "sms_set_forward_number")
    def handle_set_forward_number(call):
        try:
            current = db.get_setting("forward_to_number", "")
            msg = bot.send_message(
                chat_id=call.message.chat.id,
                text=(
                    f"📱 <b>Set Indian Number</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Current: <b>{current or 'Not set'}</b>\n\n"
                    f"Send your Indian number:\n"
                    f"Example: <code>+919876543210</code>"
                ),
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg, process_forward_number)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Set forward number error: {e}")

    def process_forward_number(message):
        try:
            number = message.text.strip()
            if not number.startswith("+"):
                number = "+91" + number.lstrip("0")
            db.set_setting("forward_to_number", number)
            bot.send_message(
                chat_id=message.chat.id,
                text=(
                    f"✅ <b>Number Set</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"📱 Forward Number: <b>{number}</b>\n\n"
                    f"Now enable Number Forward in Forward Settings."
                ),
                reply_markup=back_to_main(),
                parse_mode="HTML"
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Process forward number error: {e}")
