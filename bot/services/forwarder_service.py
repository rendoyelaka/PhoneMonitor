import logging
import re
import requests
from datetime import datetime
from bot.database.db_manager import db
from bot.config import (
    BOT_TOKEN,
    ENABLE_NUMBER_FORWARD,
    FORWARD_TO_NUMBER,
    ENABLE_TG_FORWARD,
    FORWARD_TO_TG_ID
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# FORMAT CONSTANTS
# ─────────────────────────────────────────
FORMAT_DEFAULT  = "default"
FORMAT_SIMPLE   = "format1"
FORMAT_DETAILED = "format2"
FORMAT_MINIMAL  = "format3"
FORMAT_OTP      = "format4"
FORMAT_CUSTOM   = "format5"

FORMAT_LABELS = {
    FORMAT_DEFAULT:  "Default",
    FORMAT_SIMPLE:   "Format 1 — Simple",
    FORMAT_DETAILED: "Format 2 — Detailed",
    FORMAT_MINIMAL:  "Format 3 — Minimal",
    FORMAT_OTP:      "Format 4 — OTP Focus",
    FORMAT_CUSTOM:   "Format 5 — Custom",
}

# ─────────────────────────────────────────
# FORWARDER SERVICE CLASS
# ─────────────────────────────────────────
class ForwarderService:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    # ─────────────────────────────────────────
    # CHECK IF NUMBER FORWARD IS ENABLED
    # ─────────────────────────────────────────
    def is_number_forward_enabled(self) -> bool:
        try:
            setting = db.get_setting("number_forward_enabled", "false")
            return setting == "true" and ENABLE_NUMBER_FORWARD
        except Exception as e:
            logger.error(f"Check number forward error: {e}")
            return False

    # ─────────────────────────────────────────
    # CHECK IF TELEGRAM FORWARD IS ENABLED
    # ─────────────────────────────────────────
    def is_tg_forward_enabled(self) -> bool:
        try:
            setting = db.get_setting("tg_forward_enabled", "false")
            return setting == "true"
        except Exception as e:
            logger.error(f"Check TG forward error: {e}")
            return False

    # ─────────────────────────────────────────
    # ENABLE / DISABLE NUMBER FORWARD
    # ─────────────────────────────────────────
    def enable_number_forward(self) -> bool:
        try:
            db.set_setting("number_forward_enabled", "true")
            return True
        except Exception as e:
            logger.error(f"Enable number forward error: {e}")
            return False

    def disable_number_forward(self) -> bool:
        try:
            db.set_setting("number_forward_enabled", "false")
            return True
        except Exception as e:
            logger.error(f"Disable number forward error: {e}")
            return False

    # ─────────────────────────────────────────
    # ENABLE / DISABLE TELEGRAM FORWARD
    # ─────────────────────────────────────────
    def enable_tg_forward(self) -> bool:
        try:
            db.set_setting("tg_forward_enabled", "true")
            return True
        except Exception as e:
            logger.error(f"Enable TG forward error: {e}")
            return False

    def disable_tg_forward(self) -> bool:
        try:
            db.set_setting("tg_forward_enabled", "false")
            return True
        except Exception as e:
            logger.error(f"Disable TG forward error: {e}")
            return False

    # ─────────────────────────────────────────
    # SET TELEGRAM FORWARD TARGET
    # Accepts any one of 5 fields
    # ─────────────────────────────────────────
    def set_tg_forward_target(self, field: int, value: str) -> dict:
        try:
            value = value.strip()
            field_map = {
                1: "forward_tg_username",
                2: "forward_tg_channel_name",
                3: "forward_tg_channel_id",
                4: "forward_tg_page_name",
                5: "forward_tg_bot_username",
            }
            if field not in field_map:
                return {"success": False, "reason": "Invalid field number"}

            # Clear all 5 fields first
            for key in field_map.values():
                db.set_setting(key, "")

            # Save the one field chosen
            db.set_setting(field_map[field], value)
            logger.info(f"Telegram forward target set: field={field} value={value}")
            return {"success": True, "field": field, "value": value}
        except Exception as e:
            logger.error(f"Set TG forward target error: {e}")
            return {"success": False, "reason": str(e)}

    # ─────────────────────────────────────────
    # RESOLVE TELEGRAM TARGET
    # Returns the active target value
    # ─────────────────────────────────────────
    def resolve_tg_target(self) -> str:
        try:
            checks = [
                "forward_tg_username",
                "forward_tg_channel_name",
                "forward_tg_channel_id",
                "forward_tg_page_name",
                "forward_tg_bot_username",
            ]
            for key in checks:
                val = db.get_setting(key, "")
                if val and val.strip():
                    return val.strip()
            # Fall back to config
            return FORWARD_TO_TG_ID or ""
        except Exception as e:
            logger.error(f"Resolve TG target error: {e}")
            return ""

    # ─────────────────────────────────────────
    # GET TG TARGET STATUS
    # ─────────────────────────────────────────
    def get_tg_target_status(self) -> dict:
        try:
            return {
                "username":     db.get_setting("forward_tg_username", ""),
                "channel_name": db.get_setting("forward_tg_channel_name", ""),
                "channel_id":   db.get_setting("forward_tg_channel_id", ""),
                "page_name":    db.get_setting("forward_tg_page_name", ""),
                "bot_username": db.get_setting("forward_tg_bot_username", ""),
            }
        except Exception as e:
            logger.error(f"Get TG target status error: {e}")
            return {}

    # ─────────────────────────────────────────
    # EXTRACT OTP FROM MESSAGE
    # ─────────────────────────────────────────
    def _extract_otp(self, message: str) -> str:
        try:
            match = re.search(r'\b\d{4,8}\b', message)
            return match.group(0) if match else ""
        except Exception:
            return ""

    # ─────────────────────────────────────────
    # APPLY FORWARD FORMAT
    # ─────────────────────────────────────────
    def apply_forward_format(self, sender: str, message: str, timestamp: str) -> str:
        try:
            fmt = db.get_setting("sms_forward_format", FORMAT_DEFAULT)
            otp = self._extract_otp(message)
            date_part = timestamp[:10] if len(timestamp) >= 10 else timestamp
            time_part = timestamp[11:19] if len(timestamp) >= 19 else timestamp

            if fmt == FORMAT_SIMPLE or fmt == FORMAT_DEFAULT:
                return (
                    f"📱 SMS — {sender}\n"
                    f"{message}\n"
                    f"🕐 {date_part} {time_part}"
                )

            elif fmt == FORMAT_DETAILED:
                return (
                    f"━━━━━━━━━━━━━━━━\n"
                    f"📱 New SMS\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"📞 From: {sender}\n"
                    f"💬 Message:\n{message}\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"🕐 Date: {date_part}\n"
                    f"⏰ Time: {time_part}"
                )

            elif fmt == FORMAT_MINIMAL:
                return f"{sender} | {otp if otp else message[:30]} | {time_part[:5]}"

            elif fmt == FORMAT_OTP:
                if otp:
                    return (
                        f"⚡ OTP ALERT\n"
                        f"━━━━━━━━━━━━\n"
                        f"{otp}\n"
                        f"━━━━━━━━━━━━\n"
                        f"From: {sender}\n"
                        f"Time: {time_part}"
                    )
                else:
                    return (
                        f"📱 SMS — {sender}\n"
                        f"{message}\n"
                        f"🕐 {time_part}"
                    )

            elif fmt == FORMAT_CUSTOM:
                custom_text = db.get_setting("sms_forward_custom_text", "")
                if custom_text:
                    return (
                        custom_text
                        .replace("{sender}", sender)
                        .replace("{message}", message)
                        .replace("{date}", date_part)
                        .replace("{time}", time_part)
                        .replace("{otp}", otp)
                    )
                else:
                    return f"📱 SMS — {sender}\n{message}\n🕐 {time_part}"

            # fallback
            return f"📱 SMS — {sender}\n{message}\n🕐 {time_part}"

        except Exception as e:
            logger.error(f"Apply forward format error: {e}")
            return f"📱 SMS from {sender}: {message}"

    # ─────────────────────────────────────────
    # GET FORWARD FORMAT PREVIEW
    # ─────────────────────────────────────────
    def get_format_preview(self, fmt: str) -> str:
        try:
            sender  = "HDFC Bank"
            message = "Your OTP is 482910. Valid for 10 minutes. Do not share."
            timestamp = "2026-05-27 14:31:45"
            otp = "482910"
            date_part = "2026-05-27"
            time_part = "14:31:45"

            if fmt == FORMAT_SIMPLE or fmt == FORMAT_DEFAULT:
                return (
                    f"📱 SMS — {sender}\n"
                    f"{message}\n"
                    f"🕐 {date_part} {time_part}"
                )
            elif fmt == FORMAT_DETAILED:
                return (
                    f"━━━━━━━━━━━━━━━━\n"
                    f"📱 New SMS\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"📞 From: {sender}\n"
                    f"💬 Message:\n{message}\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"🕐 Date: {date_part}\n"
                    f"⏰ Time: {time_part}"
                )
            elif fmt == FORMAT_MINIMAL:
                return f"{sender} | {otp} | {time_part[:5]}"
            elif fmt == FORMAT_OTP:
                return (
                    f"⚡ OTP ALERT\n"
                    f"━━━━━━━━━━━━\n"
                    f"{otp}\n"
                    f"━━━━━━━━━━━━\n"
                    f"From: {sender}\n"
                    f"Time: {time_part}"
                )
            elif fmt == FORMAT_CUSTOM:
                custom_text = db.get_setting("sms_forward_custom_text", "")
                if custom_text:
                    return (
                        custom_text
                        .replace("{sender}", sender)
                        .replace("{message}", message)
                        .replace("{date}", date_part)
                        .replace("{time}", time_part)
                        .replace("{otp}", otp)
                    )
                return "No custom format set yet."
            return f"📱 SMS — {sender}\n{message}\n🕐 {time_part}"
        except Exception as e:
            logger.error(f"Get format preview error: {e}")
            return "Preview unavailable"

    # ─────────────────────────────────────────
    # SET FORWARD FORMAT
    # ─────────────────────────────────────────
    def set_forward_format(self, fmt: str) -> bool:
        try:
            db.set_setting("sms_forward_format", fmt)
            logger.info(f"Forward format set: {fmt}")
            return True
        except Exception as e:
            logger.error(f"Set forward format error: {e}")
            return False

    # ─────────────────────────────────────────
    # SET CUSTOM FORMAT TEXT
    # ─────────────────────────────────────────
    def set_custom_format_text(self, text: str) -> bool:
        try:
            db.set_setting("sms_forward_custom_text", text)
            db.set_setting("sms_forward_format", FORMAT_CUSTOM)
            logger.info("Custom format text saved")
            return True
        except Exception as e:
            logger.error(f"Set custom format text error: {e}")
            return False

    # ─────────────────────────────────────────
    # GET CURRENT FORMAT
    # ─────────────────────────────────────────
    def get_current_format(self) -> str:
        try:
            return db.get_setting("sms_forward_format", FORMAT_DEFAULT)
        except Exception as e:
            logger.error(f"Get current format error: {e}")
            return FORMAT_DEFAULT

    # ─────────────────────────────────────────
    # DELETE FORMAT — RESET TO DEFAULT
    # ─────────────────────────────────────────
    def delete_forward_format(self) -> bool:
        try:
            db.set_setting("sms_forward_format", FORMAT_DEFAULT)
            db.set_setting("sms_forward_custom_text", "")
            logger.info("Forward format deleted — reset to default")
            return True
        except Exception as e:
            logger.error(f"Delete forward format error: {e}")
            return False

    # ─────────────────────────────────────────
    # FORWARD SMS TO INDIAN NUMBER (OPTIONAL)
    # ─────────────────────────────────────────
    def forward_to_number(self, sender: str, message: str, timestamp: str) -> bool:
        try:
            if not self.is_number_forward_enabled():
                return False
            if not FORWARD_TO_NUMBER:
                logger.warning("No forward number configured")
                return False
            formatted = self.apply_forward_format(sender, message, timestamp)
            # ── Wire SMS gateway API here e.g. Fast2SMS, MSG91, Twilio ──
            logger.info(f"SMS forwarded to number: {FORWARD_TO_NUMBER}")
            db.set_setting("last_number_forward", datetime.now().isoformat())
            return True
        except Exception as e:
            logger.error(f"Forward to number error: {e}")
            return False

    # ─────────────────────────────────────────
    # FORWARD SMS TO TELEGRAM
    # ─────────────────────────────────────────
    def forward_to_telegram(self, sender: str, message: str, timestamp: str) -> bool:
        try:
            if not self.is_tg_forward_enabled():
                return False
            target = self.resolve_tg_target()
            if not target:
                logger.warning("No Telegram forward target configured")
                return False
            formatted = self.apply_forward_format(sender, message, timestamp)
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": target,
                "text": formatted,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            success = response.status_code == 200
            if success:
                db.set_setting("last_tg_forward", datetime.now().isoformat())
                logger.info(f"SMS forwarded to Telegram: {target}")
            return success
        except Exception as e:
            logger.error(f"Forward to Telegram error: {e}")
            return False

    # ─────────────────────────────────────────
    # GET FULL FORWARDER STATUS
    # ─────────────────────────────────────────
    def get_forwarder_status(self) -> dict:
        try:
            tg_target = self.get_tg_target_status()
            active_target = self.resolve_tg_target()
            current_fmt = self.get_current_format()
            return {
                "number_forward_enabled": self.is_number_forward_enabled(),
                "tg_forward_enabled": self.is_tg_forward_enabled(),
                "forward_number": FORWARD_TO_NUMBER or "Not set",
                "tg_target": active_target or "Not set",
                "tg_target_details": tg_target,
                "last_number_forward": db.get_setting("last_number_forward", "Never"),
                "last_tg_forward": db.get_setting("last_tg_forward", "Never"),
                "current_format": current_fmt,
                "format_label": FORMAT_LABELS.get(current_fmt, "Default"),
            }
        except Exception as e:
            logger.error(f"Get forwarder status error: {e}")
            return {}

    # ─────────────────────────────────────────
    # FORMAT STATUS MESSAGE
    # ─────────────────────────────────────────
    def format_forwarder_status(self) -> str:
        try:
            s = self.get_forwarder_status()
            number_status = "🟢 ON" if s.get("number_forward_enabled") else "🔴 OFF"
            tg_status = "🟢 ON" if s.get("tg_forward_enabled") else "🔴 OFF"
            return (
                f"↪️ <b>Forward Status</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📞 Number Forward: {number_status}\n"
                f"📲 Number: {s.get('forward_number', 'Not set')}\n"
                f"🕐 Last: {s.get('last_number_forward', 'Never')}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"💬 Telegram Forward: {tg_status}\n"
                f"📌 Target: {s.get('tg_target', 'Not set')}\n"
                f"🕐 Last: {s.get('last_tg_forward', 'Never')}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🎨 Format: {s.get('format_label', 'Default')}\n"
            )
        except Exception as e:
            logger.error(f"Format forwarder status error: {e}")
            return "⚠️ Status unavailable"


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
forwarder_service = ForwarderService()
