from cryptography.fernet import Fernet
import os


class EncryptionManager:
    """Handles encryption and decryption of sensitive values."""

    def __init__(self):
        secret_key = os.getenv("SECRET_ENCRYPTION_KEY")
        if not secret_key:
            raise ValueError("Missing SECRET_ENCRYPTION_KEY environment variable.")
        self.fernet = Fernet(secret_key.encode() if isinstance(secret_key, str) else secret_key)

    def encrypt(self, plain_text: str) -> str:
        """Encrypt plain text into a secure string."""
        if not plain_text:
            return plain_text
        return self.fernet.encrypt(plain_text.encode()).decode()

    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt an encrypted string."""
        if not encrypted_text:
            return encrypted_text
        try:
            return self.fernet.decrypt(encrypted_text.encode()).decode()
        except Exception:
            return "[decryption failed]"


# Singleton instance (can be imported anywhere)
encryption_manager = EncryptionManager()

