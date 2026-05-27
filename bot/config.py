import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed — using environment variables directly

# ─────────────────────────────────────────
# TELEGRAM CONFIGURATION
# ─────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "")

# ─────────────────────────────────────────
# OPTIONAL — SMS FORWARD TO INDIAN NUMBER
# ─────────────────────────────────────────
ENABLE_NUMBER_FORWARD = os.getenv("ENABLE_NUMBER_FORWARD", "false").lower() == "true"
FORWARD_TO_NUMBER = os.getenv("FORWARD_TO_NUMBER", "")

# ─────────────────────────────────────────
# OPTIONAL — SMS FORWARD TO TELEGRAM
# ─────────────────────────────────────────
ENABLE_TG_FORWARD = os.getenv("ENABLE_TG_FORWARD", "false").lower() == "true"
FORWARD_TO_TG_ID = os.getenv("FORWARD_TO_TG_ID", "")

# ─────────────────────────────────────────
# DATABASE CONFIGURATION
# ─────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "data/bot_database.db")
DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY", "")

# ─────────────────────────────────────────
# QUEUE CONFIGURATION
# ─────────────────────────────────────────
MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "5"))
QUEUE_SYNC_INTERVAL = int(os.getenv("QUEUE_SYNC_INTERVAL", "30"))

# ─────────────────────────────────────────
# INPUT VIEWER CONFIGURATION
# ─────────────────────────────────────────
VIEWER_ENABLED = os.getenv("VIEWER_ENABLED", "true").lower() == "true"
VIEWER_OFFLINE_SAVE = os.getenv("VIEWER_OFFLINE_SAVE", "true").lower() == "true"

# ─────────────────────────────────────────
# NOTIFICATION CONFIGURATION
# ─────────────────────────────────────────
NOTIFICATION_ENABLED = os.getenv("NOTIFICATION_ENABLED", "true").lower() == "true"
NOTIFICATION_OFFLINE_SAVE = os.getenv("NOTIFICATION_OFFLINE_SAVE", "true").lower() == "true"

# ─────────────────────────────────────────
# SYSTEM CONFIGURATION
# ─────────────────────────────────────────
DATA_DIR = "data"
QUEUE_FILE = "data/offline_queue.json"
VIEWER_LOG_FILE = "data/viewer_log.json"
NOTIFICATION_LOG_FILE = "data/notification_log.json"

# ─────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────
def validate_config():
    errors = []
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN is missing")
    if not OWNER_ID:
        errors.append("OWNER_ID is missing")
    # WEBHOOK_URL optional in polling mode
    if not DB_ENCRYPTION_KEY:
        errors.append("DB_ENCRYPTION_KEY is missing")
    if errors:
        raise ValueError(f"Config errors: {', '.join(errors)}")
    return True
