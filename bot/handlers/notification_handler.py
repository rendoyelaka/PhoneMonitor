import logging
from bot.database.db_manager import db
from bot.menus.notification_menu import (
    notification_menu, notification_menu_text,
    notification_recent_menu, notification_confirm_clear,
    notification_queue_menu, notification_confirm_clear_queue
)
from bot.menus.main_menu import back_to_main

logger = logging.getLogger(__name__)

NOTIF_PER_PAGE = 5

# ─────────────────────────────────────────
# REGISTER ALERT MONITOR HANDLERS
# ─────────────────────────────────────────
def register_notification_handlers(bot):

    # ── OPEN NOTIFICATIONS MENU ──
    @bot.callback_query_handler(func=lambda c: c.data == "menu_notifications")
    def handle_notification_menu(call):
        try:
            monitor_active = db.get_setting("notification_enabled", "true") == "true"
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=notification_menu_text(monitor_active),
                reply_markup=notification_menu(monitor_active),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Notification menu error: {e}")

    # ── START ALERT MONITOR ──
    @bot.callback_query_handler(func=lambda c: c.data == "notif_start")
    def handle_notif_start(call):
        try:
            db.set_setting("notification_enabled", "true")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    "▶️ <b>Alert Monitor Started</b>\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "✅ Monitoring all incoming notifications.\n"
                    "Alerts will be forwarded here instantly."
                ),
                reply_markup=notification_menu(monitor_active=True),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Notif start error: {e}")

    # ── STOP ALERT MONITOR ──
    @bot.callback_query_handler(func=lambda c: c.data == "notif_stop")
    def handle_notif_stop(call):
        try:
            db.set_setting("notification_enabled", "false")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    "⏹ <b>Alert Monitor Stopped</b>\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "🔴 Notification monitoring is now inactive."
                ),
                reply_markup=notification_menu(monitor_active=False),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Notif stop error: {e}")

    # ── RECENT NOTIFICATIONS ──
    @bot.callback_query_handler(func=lambda c: c.data in ["notif_recent"] or c.data.startswith("notif_page_"))
    def handle_notif_recent(call):
        try:
            page = 1
            if call.data.startswith("notif_page_"):
                try:
                    page = int(call.data.split("_")[-1])
                except ValueError:
                    page = 1

            all_notifs = db.get_notifications(limit=200)
            if not all_notifs:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=(
                        "🔔 <b>Recent Notifications</b>\n"
                        "━━━━━━━━━━━━━━━━\n"
                        "No notifications received yet.\n"
                        "Start the monitor to begin capturing alerts."
                    ),
                    reply_markup=back_to_main(),
                    parse_mode="HTML"
                )
                return

            total_pages = max(1, (len(all_notifs) + NOTIF_PER_PAGE - 1) // NOTIF_PER_PAGE)
            page = max(1, min(page, total_pages))
            start = (page - 1) * NOTIF_PER_PAGE
            end = start + NOTIF_PER_PAGE
            page_notifs = all_notifs[start:end]

            text = f"🔔 <b>Notifications</b> — Page {page}/{total_pages}\n━━━━━━━━━━━━━━━━\n"
            for i, notif in enumerate(page_notifs, start + 1):
                text += (
                    f"{i}. 📲 <b>{notif['app_name']}</b>\n"
                    f"   📌 {notif['title']}\n"
                    f"   💬 {notif['content'][:80]}{'...' if len(notif['content']) > 80 else ''}\n"
                    f"   🕐 {notif['timestamp']}\n\n"
                )

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=notification_recent_menu(page, total_pages),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Notif recent error: {e}")

    # ── PAGE INFO (no-op tap on page counter) ──
    @bot.callback_query_handler(func=lambda c: c.data == "notif_page_info")
    def handle_notif_page_info(call):
        try:
            bot.answer_callback_query(call.id, "Current page indicator")
        except Exception as e:
            logger.error(f"Notif page info error: {e}")

    # ── CONFIRM CLEAR NOTIFICATIONS ──
    @bot.callback_query_handler(func=lambda c: c.data == "notif_clear_confirm")
    def handle_notif_clear_confirm(call):
        try:
            with db.get_connection() as conn:
                count = conn.execute("SELECT COUNT(*) as count FROM notifications").fetchone()["count"]
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"⚠️ <b>Clear All Notifications?</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Total stored notifications: <b>{count}</b>\n"
                    f"All will be permanently deleted.\n"
                    f"Are you sure?"
                ),
                reply_markup=notification_confirm_clear(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Notif clear confirm error: {e}")

    # ── CLEAR NOTIFICATIONS ──
    @bot.callback_query_handler(func=lambda c: c.data == "notif_clear")
    def handle_notif_clear(call):
        try:
            with db.get_connection() as conn:
                conn.execute("DELETE FROM notifications")
                conn.commit()
            monitor_active = db.get_setting("notification_enabled", "true") == "true"
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ <b>All notifications cleared successfully</b>",
                reply_markup=notification_menu(monitor_active),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Notif clear error: {e}")

    # ── QUEUE STATUS ──
    @bot.callback_query_handler(func=lambda c: c.data == "notif_queue_status")
    def handle_notif_queue_status(call):
        try:
            queue = db.get_notification_queue()
            with db.get_connection() as conn:
                total_queued = conn.execute(
                    "SELECT COUNT(*) as count FROM notification_queue"
                ).fetchone()["count"]
                pending = conn.execute(
                    "SELECT COUNT(*) as count FROM notification_queue WHERE retry_count < 3"
                ).fetchone()["count"]
                failed = conn.execute(
                    "SELECT COUNT(*) as count FROM notification_queue WHERE retry_count >= 3"
                ).fetchone()["count"]

            text = (
                f"📊 <b>Notification Queue Status</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📥 Total in queue: <b>{total_queued}</b>\n"
                f"⏳ Pending delivery: <b>{pending}</b>\n"
                f"❌ Failed (max retries): <b>{failed}</b>\n\n"
            )

            if queue:
                text += "🕐 <b>Pending Items:</b>\n"
                for item in queue[:5]:
                    text += (
                        f"• 📲 {item['app_name']} — {item['title'][:40]}\n"
                        f"  Retry: {item['retry_count']}/3\n"
                    )
                if len(queue) > 5:
                    text += f"\n<i>...and {len(queue) - 5} more</i>"
            else:
                text += "✅ <b>Queue is empty — all delivered</b>"

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=notification_queue_menu(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Notif queue status error: {e}")

    # ── CONFIRM CLEAR QUEUE ──
    @bot.callback_query_handler(func=lambda c: c.data == "notif_clear_queue_confirm")
    def handle_notif_clear_queue_confirm(call):
        try:
            queue = db.get_notification_queue()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"⚠️ <b>Clear Notification Queue?</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Pending items in queue: <b>{len(queue)}</b>\n"
                    f"These will be permanently deleted.\n"
                    f"Are you sure?"
                ),
                reply_markup=notification_confirm_clear_queue(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Notif clear queue confirm error: {e}")

    # ── CLEAR QUEUE ──
    @bot.callback_query_handler(func=lambda c: c.data == "notif_clear_queue")
    def handle_notif_clear_queue(call):
        try:
            with db.get_connection() as conn:
                conn.execute("DELETE FROM notification_queue")
                conn.commit()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ <b>Notification queue cleared successfully</b>",
                reply_markup=back_to_main(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Notif clear queue error: {e}")
