import logging
import re
import requests
from datetime import datetime
from bot.database.db_manager import db
from bot.config import BOT_TOKEN

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# FORWARD MANAGER
# Handles multiple forward numbers
# and multiple Telegram targets
# ─────────────────────────────────────────
class ForwardManager:

    # ─────────────────────────────────────────
    # AUTO DETECT TELEGRAM TARGET TYPE
    # Handles all formats:
    # https://t.me/username
    # https://t.me/+invitelink
    # t.me/username
    # @username
    # @botusername
    # -100123456789
    # ─────────────────────────────────────────
    def detect_target_type(self, target: str) -> str:
        target = target.strip()
        # Invite link — https://t.me/+XXXXX
        if "t.me/+" in target:
            return "invite_link"
        # Channel ID — starts with -100
        if target.startswith("-100") and target[4:].isdigit():
            return "channel_id"
        # Full link — https://t.me/username or t.me/username
        if target.startswith("https://t.me/") or target.startswith("t.me/"):
            name = target.replace("https://t.me/", "").replace("t.me/", "").lower()
            if name.endswith("bot"):
                return "bot"
            return "channel"
        # Username — starts with @
        if target.startswith("@"):
            name = target[1:].lower()
            if name.endswith("bot"):
                return "bot"
            return "channel"
        # Plain number — channel ID
        if target.lstrip("-").isdigit():
            return "channel_id"
        # Default — channel name
        return "channel_name"

    # ─────────────────────────────────────────
    # GET TYPE EMOJI
    # ─────────────────────────────────────────
    def get_type_emoji(self, target_type: str) -> str:
        emojis = {
            "channel": "📢",
            "channel_id": "📢",
            "channel_name": "📢",
            "link": "🔗",
            "invite_link": "🔗",
            "bot": "🤖",
            "group": "👥",
            "unknown": "💬"
        }
        return emojis.get(target_type, "💬")

    # ─────────────────────────────────────────
    # NORMALISE NUMBER
    # Ensures number has +91 prefix
    # ─────────────────────────────────────────
    def normalise_number(self, number: str) -> str:
        number = number.strip().replace(" ", "").replace("-", "")
        if number.startswith("0"):
            number = "+91" + number[1:]
        elif number.startswith("91") and not number.startswith("+"):
            number = "+" + number
        elif not number.startswith("+"):
            number = "+91" + number
        return number

    # ─────────────────────────────────────────
    # NORMALISE TELEGRAM TARGET
    # Handles all formats:
    # https://t.me/username  → @username
    # https://t.me/+invite   → keeps as is
    # t.me/username          → @username
    # @username              → keeps as is
    # -100XXXXXX             → keeps as is
    # ─────────────────────────────────────────
    def normalise_target(self, target: str) -> str:
        target = target.strip()
        # Keep invite links as-is
        if "t.me/+" in target:
            return target
        # Convert https://t.me/username → @username
        if target.startswith("https://t.me/"):
            username = target.replace("https://t.me/", "").strip("/")
            return "@" + username
        # Convert t.me/username → @username
        if target.startswith("t.me/"):
            username = target.replace("t.me/", "").strip("/")
            return "@" + username
        # Already @username or channel ID — keep as is
        return target

    # ─────────────────────────────────────────
    # ADD FORWARD NUMBER
    # ─────────────────────────────────────────
    def add_number(self, number: str) -> dict:
        try:
            number = self.normalise_number(number)
            if db.number_exists(number):
                return {"success": False, "reason": "already_exists", "number": number}
            db.add_forward_number(number)
            return {"success": True, "number": number}
        except Exception as e:
            logger.error(f"Add number error: {e}")
            return {"success": False, "reason": str(e)}

    # ─────────────────────────────────────────
    # UPDATE FORWARD NUMBER
    # ─────────────────────────────────────────
    def update_number(self, old_number: str, new_number: str) -> dict:
        try:
            new_number = self.normalise_number(new_number)
            db.update_forward_number(old_number, new_number)
            return {"success": True, "old": old_number, "new": new_number}
        except Exception as e:
            logger.error(f"Update number error: {e}")
            return {"success": False, "reason": str(e)}

    # ─────────────────────────────────────────
    # DELETE FORWARD NUMBER
    # ─────────────────────────────────────────
    def delete_number(self, number: str) -> dict:
        try:
            db.delete_forward_number(number)
            return {"success": True, "number": number}
        except Exception as e:
            logger.error(f"Delete number error: {e}")
            return {"success": False, "reason": str(e)}

    # ─────────────────────────────────────────
    # GET ALL NUMBERS
    # ─────────────────────────────────────────
    def get_all_numbers(self) -> list:
        return db.get_forward_numbers()

    # ─────────────────────────────────────────
    # ADD TELEGRAM TARGET
    # ─────────────────────────────────────────
    def add_telegram_target(self, target: str) -> dict:
        try:
            target = self.normalise_target(target)
            target_type = self.detect_target_type(target)
            if db.telegram_target_exists(target):
                return {"success": False, "reason": "already_exists", "target": target}
            db.add_telegram_target(target, target_type)
            return {
                "success": True,
                "target": target,
                "target_type": target_type,
                "emoji": self.get_type_emoji(target_type)
            }
        except Exception as e:
            logger.error(f"Add telegram target error: {e}")
            return {"success": False, "reason": str(e)}

    # ─────────────────────────────────────────
    # UPDATE TELEGRAM TARGET
    # ─────────────────────────────────────────
    def update_telegram_target(self, old_target: str, new_target: str) -> dict:
        try:
            new_target = self.normalise_target(new_target)
            new_type = self.detect_target_type(new_target)
            db.update_telegram_target(old_target, new_target, new_type)
            return {
                "success": True,
                "old": old_target,
                "new": new_target,
                "target_type": new_type,
                "emoji": self.get_type_emoji(new_type)
            }
        except Exception as e:
            logger.error(f"Update telegram target error: {e}")
            return {"success": False, "reason": str(e)}

    # ─────────────────────────────────────────
    # DELETE TELEGRAM TARGET
    # ─────────────────────────────────────────
    def delete_telegram_target(self, target: str) -> dict:
        try:
            db.delete_telegram_target(target)
            return {"success": True, "target": target}
        except Exception as e:
            logger.error(f"Delete telegram target error: {e}")
            return {"success": False, "reason": str(e)}

    # ─────────────────────────────────────────
    # GET ALL TELEGRAM TARGETS
    # ─────────────────────────────────────────
    def get_all_telegram_targets(self) -> list:
        return db.get_telegram_targets()

    # ─────────────────────────────────────────
    # FORMAT NUMBERS LIST TEXT
    # ─────────────────────────────────────────
    def format_numbers_list(self, numbers: list) -> str:
        if not numbers:
            return "No numbers added yet."
        text = ""
        for i, n in enumerate(numbers, 1):
            text += f"{i}. {n['number']}  🟢\n"
        return text

    # ─────────────────────────────────────────
    # FORMAT TARGETS LIST TEXT
    # ─────────────────────────────────────────
    def format_targets_list(self, targets: list) -> str:
        if not targets:
            return "No targets added yet."
        text = ""
        for i, t in enumerate(targets, 1):
            emoji = self.get_type_emoji(t.get("target_type", "unknown"))
            text += f"{i}. {t['target']}  {emoji}  🟢\n"
        return text

    # ─────────────────────────────────────────
    # FORWARD SMS TO ALL NUMBERS
    # ─────────────────────────────────────────
    def forward_to_all_numbers(self, sender: str, message: str, timestamp: str) -> dict:
        numbers = self.get_all_numbers()
        if not numbers:
            return {"success": False, "reason": "no_numbers", "sent": 0}
        sent = 0
        failed = 0
        for n in numbers:
            try:
                # Wire SMS gateway here e.g. Fast2SMS
                # For now logs the forward
                logger.info(f"SMS forwarded to number: {n['number']}")
                sent += 1
            except Exception as e:
                logger.error(f"Forward to number {n['number']} error: {e}")
                failed += 1
        return {"success": True, "sent": sent, "failed": failed}

    # ─────────────────────────────────────────
    # FORWARD SMS TO ALL TELEGRAM TARGETS
    # ─────────────────────────────────────────
    def forward_to_all_telegram(self, sender: str, message: str, timestamp: str, formatted: str) -> dict:
        targets = self.get_all_telegram_targets()
        if not targets:
            return {"success": False, "reason": "no_targets", "sent": 0}
        sent = 0
        failed = 0
        base_url = f"https://api.telegram.org/bot{BOT_TOKEN}"
        for t in targets:
            try:
                response = requests.post(
                    f"{base_url}/sendMessage",
                    json={
                        "chat_id": t["target"],
                        "text": formatted,
                        "parse_mode": "HTML"
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    sent += 1
                    logger.info(f"SMS forwarded to Telegram: {t['target']}")
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Forward to Telegram {t['target']} error: {e}")
                failed += 1
        return {"success": True, "sent": sent, "failed": failed}


# ─────────────────────────────────────────
# SINGLETON
# ─────────────────────────────────────────
forward_manager = ForwardManager()
