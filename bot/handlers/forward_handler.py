import logging
from bot.services.forward_manager import forward_manager
from bot.menus.sms_menu import (
    forward_numbers_menu, select_number_menu,
    confirm_delete_number_menu, telegram_targets_menu,
    select_target_menu, confirm_delete_target_menu
)
from bot.menus.main_menu import back_to_main

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# STATE TRACKER
# ─────────────────────────────────────────
_edit_state = {}


def register_forward_handlers(bot):

    # ─────────────────────────────────────────
    # ── NUMBERS SECTION ──
    # ─────────────────────────────────────────

    # ── SHOW ALL NUMBERS ──
    @bot.callback_query_handler(func=lambda c: c.data == "fwd_num_list")
    def handle_fwd_num_list(call):
        try:
            numbers = forward_manager.get_all_numbers()
            numbers_text = forward_manager.format_numbers_list(numbers)
            text = (
                f"📱 <b>Forward Numbers</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"{numbers_text}"
            )
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=forward_numbers_menu(numbers),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"FWD num list error: {e}")

    # ── ADD NUMBER ──
    @bot.callback_query_handler(func=lambda c: c.data == "fwd_num_add")
    def handle_fwd_num_add(call):
        try:
            msg = bot.send_message(
                chat_id=call.message.chat.id,
                text=(
                    f"📱 <b>Add Forward Number</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Send your Indian number:\n"
                    f"Example: <code>+919876543210</code>"
                ),
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg, process_add_number)
        except Exception as e:
            logger.error(f"FWD num add error: {e}")

    def process_add_number(message):
        try:
            number = message.text.strip()
            result = forward_manager.add_number(number)
            if result.get("success"):
                numbers = forward_manager.get_all_numbers()
                numbers_text = forward_manager.format_numbers_list(numbers)
                bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"✅ <b>Number Added Successfully</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📞 Number: <b>{result['number']}</b>\n"
                        f"🟢 Auto Forward: Active\n\n"
                        f"Every incoming SMS will be\n"
                        f"forwarded to this number.\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📱 <b>All Forward Numbers:</b>\n"
                        f"{numbers_text}"
                    ),
                    reply_markup=forward_numbers_menu(numbers),
                    parse_mode="HTML"
                )
            elif result.get("reason") == "already_exists":
                bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"⚠️ <b>Number Already Exists</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📞 {result['number']} is already added."
                    ),
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id=message.chat.id,
                    text=f"❌ Failed to add number. Please try again.",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Process add number error: {e}")

    # ── EDIT NUMBER — SELECT ──
    @bot.callback_query_handler(func=lambda c: c.data == "fwd_num_edit")
    def handle_fwd_num_edit(call):
        try:
            numbers = forward_manager.get_all_numbers()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"✏️ <b>Select Number To Edit</b>\n"
                    f"━━━━━━━━━━━━━━━━"
                ),
                reply_markup=select_number_menu(numbers, "edit_select"),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"FWD num edit error: {e}")

    # ── EDIT NUMBER — SELECTED ──
    @bot.callback_query_handler(func=lambda c: c.data.startswith("fwd_num_edit_select_"))
    def handle_fwd_num_edit_selected(call):
        try:
            old_number = call.data.replace("fwd_num_edit_select_", "")
            _edit_state[call.from_user.id] = {"type": "number", "old": old_number}
            msg = bot.send_message(
                chat_id=call.message.chat.id,
                text=(
                    f"✏️ <b>Edit Number</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Current: <b>{old_number}</b>\n\n"
                    f"Send new number:"
                ),
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg, process_edit_number)
        except Exception as e:
            logger.error(f"FWD num edit selected error: {e}")

    def process_edit_number(message):
        try:
            state = _edit_state.pop(message.from_user.id, {})
            old_number = state.get("old", "")
            new_number = message.text.strip()
            result = forward_manager.update_number(old_number, new_number)
            if result.get("success"):
                bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"✅ <b>Number Updated Successfully</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"Old: <s>{result['old']}</s>\n"
                        f"New: <b>{result['new']}</b>\n"
                        f"🟢 Auto Forward: Active"
                    ),
                    reply_markup=forward_numbers_menu(forward_manager.get_all_numbers()),
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Failed to update number.",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Process edit number error: {e}")

    # ── DELETE NUMBER — SELECT ──
    @bot.callback_query_handler(func=lambda c: c.data == "fwd_num_delete")
    def handle_fwd_num_delete(call):
        try:
            numbers = forward_manager.get_all_numbers()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"🗑 <b>Select Number To Delete</b>\n"
                    f"━━━━━━━━━━━━━━━━"
                ),
                reply_markup=select_number_menu(numbers, "delete_select"),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"FWD num delete error: {e}")

    # ── DELETE NUMBER — CONFIRM ──
    @bot.callback_query_handler(func=lambda c: c.data.startswith("fwd_num_delete_select_"))
    def handle_fwd_num_delete_selected(call):
        try:
            number = call.data.replace("fwd_num_delete_select_", "")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"⚠️ <b>Delete {number}?</b>\n"
                    f"━━━━━━━━━━━━━━━━"
                ),
                reply_markup=confirm_delete_number_menu(number),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"FWD num delete selected error: {e}")

    # ── DELETE NUMBER — CONFIRMED ──
    @bot.callback_query_handler(func=lambda c: c.data.startswith("fwd_num_confirm_delete_"))
    def handle_fwd_num_confirm_delete(call):
        try:
            number = call.data.replace("fwd_num_confirm_delete_", "")
            result = forward_manager.delete_number(number)
            numbers = forward_manager.get_all_numbers()
            numbers_text = forward_manager.format_numbers_list(numbers)
            if result.get("success"):
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=(
                        f"✅ <b>Deleted Successfully</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"🗑 Deleted: <b>{number}</b>\n\n"
                        f"📱 <b>Remaining Numbers:</b>\n"
                        f"{numbers_text if numbers_text else 'None'}"
                    ),
                    reply_markup=forward_numbers_menu(numbers),
                    parse_mode="HTML"
                )
            else:
                bot.answer_callback_query(call.id, "❌ Delete failed")
        except Exception as e:
            logger.error(f"FWD num confirm delete error: {e}")

    # ─────────────────────────────────────────
    # ── TELEGRAM TARGETS SECTION ──
    # ─────────────────────────────────────────

    # ── SHOW ALL TARGETS ──
    @bot.callback_query_handler(func=lambda c: c.data == "fwd_tg_list")
    def handle_fwd_tg_list(call):
        try:
            targets = forward_manager.get_all_telegram_targets()
            targets_text = forward_manager.format_targets_list(targets)
            text = (
                f"💬 <b>Telegram Targets</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"{targets_text}"
            )
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=telegram_targets_menu(targets),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"FWD TG list error: {e}")

    # ── ADD TARGET ──
    @bot.callback_query_handler(func=lambda c: c.data == "fwd_tg_add")
    def handle_fwd_tg_add(call):
        try:
            msg = bot.send_message(
                chat_id=call.message.chat.id,
                text=(
                    f"💬 <b>Add Telegram Target</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Paste anything — bot detects automatically:\n\n"
                    f"✅ <code>@username</code>\n"
                    f"✅ <code>https://t.me/username</code>\n"
                    f"✅ <code>-100123456789</code>\n"
                    f"✅ Channel or Group name\n"
                    f"✅ <code>@botusername</code>\n\n"
                    f"Send it now:"
                ),
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg, process_add_tg_target)
        except Exception as e:
            logger.error(f"FWD TG add error: {e}")

    def process_add_tg_target(message):
        try:
            target = message.text.strip()
            result = forward_manager.add_telegram_target(target)
            if result.get("success"):
                targets = forward_manager.get_all_telegram_targets()
                targets_text = forward_manager.format_targets_list(targets)
                bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"✅ <b>Target Added Successfully</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"💬 Target: <b>{result['target']}</b>\n"
                        f"📌 Type: {result['emoji']} {result['target_type'].replace('_', ' ').title()}\n"
                        f"🟢 Auto Forward: Active\n\n"
                        f"Every incoming SMS will be\n"
                        f"forwarded to this target.\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"💬 <b>All Targets:</b>\n"
                        f"{targets_text}"
                    ),
                    reply_markup=telegram_targets_menu(targets),
                    parse_mode="HTML"
                )
            elif result.get("reason") == "already_exists":
                bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"⚠️ <b>Target Already Exists</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"💬 {result['target']} is already added."
                    ),
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Failed to add target. Please try again.",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Process add TG target error: {e}")

    # ── EDIT TARGET — SELECT ──
    @bot.callback_query_handler(func=lambda c: c.data == "fwd_tg_edit")
    def handle_fwd_tg_edit(call):
        try:
            targets = forward_manager.get_all_telegram_targets()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"✏️ <b>Select Target To Edit</b>\n"
                    f"━━━━━━━━━━━━━━━━"
                ),
                reply_markup=select_target_menu(targets, "edit_select"),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"FWD TG edit error: {e}")

    # ── EDIT TARGET — SELECTED ──
    @bot.callback_query_handler(func=lambda c: c.data.startswith("fwd_tg_edit_select_"))
    def handle_fwd_tg_edit_selected(call):
        try:
            old_target = call.data.replace("fwd_tg_edit_select_", "")
            _edit_state[call.from_user.id] = {"type": "tg", "old": old_target}
            msg = bot.send_message(
                chat_id=call.message.chat.id,
                text=(
                    f"✏️ <b>Edit Target</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Current: <b>{old_target}</b>\n\n"
                    f"Send new target\n"
                    f"(username, link, ID, name, bot):"
                ),
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg, process_edit_tg_target)
        except Exception as e:
            logger.error(f"FWD TG edit selected error: {e}")

    def process_edit_tg_target(message):
        try:
            state = _edit_state.pop(message.from_user.id, {})
            old_target = state.get("old", "")
            new_target = message.text.strip()
            result = forward_manager.update_telegram_target(old_target, new_target)
            if result.get("success"):
                bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"✅ <b>Target Updated Successfully</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"Old: <s>{result['old']}</s>\n"
                        f"New: <b>{result['new']}</b>\n"
                        f"📌 Type: {result['emoji']} {result['target_type'].replace('_', ' ').title()}\n"
                        f"🟢 Auto Forward: Active"
                    ),
                    reply_markup=telegram_targets_menu(forward_manager.get_all_telegram_targets()),
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Failed to update target.",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Process edit TG target error: {e}")

    # ── DELETE TARGET — SELECT ──
    @bot.callback_query_handler(func=lambda c: c.data == "fwd_tg_delete")
    def handle_fwd_tg_delete(call):
        try:
            targets = forward_manager.get_all_telegram_targets()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"🗑 <b>Select Target To Delete</b>\n"
                    f"━━━━━━━━━━━━━━━━"
                ),
                reply_markup=select_target_menu(targets, "delete_select"),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"FWD TG delete error: {e}")

    # ── DELETE TARGET — CONFIRM ──
    @bot.callback_query_handler(func=lambda c: c.data.startswith("fwd_tg_delete_select_"))
    def handle_fwd_tg_delete_selected(call):
        try:
            target = call.data.replace("fwd_tg_delete_select_", "")
            safe = target.replace("@", "AT_").replace("-", "MINUS_")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"⚠️ <b>Delete {target}?</b>\n"
                    f"━━━━━━━━━━━━━━━━"
                ),
                reply_markup=confirm_delete_target_menu(target),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"FWD TG delete selected error: {e}")

    # ── DELETE TARGET — CONFIRMED ──
    @bot.callback_query_handler(func=lambda c: c.data.startswith("fwd_tg_confirm_delete_"))
    def handle_fwd_tg_confirm_delete(call):
        try:
            safe = call.data.replace("fwd_tg_confirm_delete_", "")
            target = safe.replace("AT_", "@").replace("MINUS_", "-")
            result = forward_manager.delete_telegram_target(target)
            targets = forward_manager.get_all_telegram_targets()
            targets_text = forward_manager.format_targets_list(targets)
            if result.get("success"):
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=(
                        f"✅ <b>Deleted Successfully</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"🗑 Deleted: <b>{target}</b>\n\n"
                        f"💬 <b>Remaining Targets:</b>\n"
                        f"{targets_text if targets_text else 'None'}"
                    ),
                    reply_markup=telegram_targets_menu(targets),
                    parse_mode="HTML"
                )
            else:
                bot.answer_callback_query(call.id, "❌ Delete failed")
        except Exception as e:
            logger.error(f"FWD TG confirm delete error: {e}")
