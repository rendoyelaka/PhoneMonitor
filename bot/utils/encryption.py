import os
import base64
import hashlib
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from bot.config import DB_ENCRYPTION_KEY

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# ENCRYPTION MANAGER CLASS
# ─────────────────────────────────────────
class EncryptionManager:
    def __init__(self):
        self.key = self._derive_key(DB_ENCRYPTION_KEY)
        self.fernet = Fernet(self.key)

    # ─────────────────────────────────────────
    # DERIVE STRONG KEY FROM PASSWORD
    # ─────────────────────────────────────────
    def _derive_key(self, password: str) -> bytes:
        try:
            salt = hashlib.sha256(password.encode()).digest()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            return key
        except Exception as e:
            logger.error(f"Key derivation error: {e}")
            raise

    # ─────────────────────────────────────────
    # ENCRYPT TEXT
    # ─────────────────────────────────────────
    def encrypt(self, plain_text: str) -> str:
        try:
            encrypted = self.fernet.encrypt(plain_text.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return plain_text

    # ─────────────────────────────────────────
    # DECRYPT TEXT
    # ─────────────────────────────────────────
    def decrypt(self, encrypted_text: str) -> str:
        try:
            decrypted = self.fernet.decrypt(encrypted_text.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return encrypted_text

    # ─────────────────────────────────────────
    # ENCRYPT DICT
    # ─────────────────────────────────────────
    def encrypt_dict(self, data: dict) -> dict:
        try:
            encrypted_data = {}
            for key, value in data.items():
                if isinstance(value, str):
                    encrypted_data[key] = self.encrypt(value)
                else:
                    encrypted_data[key] = value
            return encrypted_data
        except Exception as e:
            logger.error(f"Encrypt dict error: {e}")
            return data

    # ─────────────────────────────────────────
    # DECRYPT DICT
    # ─────────────────────────────────────────
    def decrypt_dict(self, data: dict, fields: list) -> dict:
        try:
            decrypted_data = dict(data)
            for field in fields:
                if field in decrypted_data and isinstance(decrypted_data[field], str):
                    decrypted_data[field] = self.decrypt(decrypted_data[field])
            return decrypted_data
        except Exception as e:
            logger.error(f"Decrypt dict error: {e}")
            return data

    # ─────────────────────────────────────────
    # GENERATE SECURE HASH
    # ─────────────────────────────────────────
    def generate_hash(self, text: str) -> str:
        try:
            return hashlib.sha256(text.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Hash generation error: {e}")
            return ""

    # ─────────────────────────────────────────
    # VERIFY HASH
    # ─────────────────────────────────────────
    def verify_hash(self, text: str, hash_value: str) -> bool:
        try:
            return self.generate_hash(text) == hash_value
        except Exception as e:
            logger.error(f"Hash verification error: {e}")
            return False


# ─────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────
encryption = EncryptionManager()
