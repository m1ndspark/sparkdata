# services/settings_service.py

from sqlalchemy.orm import Session
from models.api_key_model import APIKey
from utils.encryption import encryption_manager
from datetime import datetime

# In-memory cache for quick access
global_settings_cache = {}


class SettingsService:
    """Handles all logic for managing API keys."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_keys(self):
        """Retrieve all stored API keys (masked)."""
        keys = self.db.query(APIKey).all()
        return [key.to_dict() for key in keys]

    def get_key(self, service_name: str):
        """Retrieve one API key (masked)."""
        key = self.db.query(APIKey).filter(APIKey.service_name == service_name).first()
        if not key:
            return None
        return key.to_dict()

    def add_or_update_key(self, service_name: str, key_value: str):
        """Add a new key or update an existing one."""
        encrypted_value = encryption_manager.encrypt(key_value)
        existing = self.db.query(APIKey).filter(APIKey.service_name == service_name).first()

        if existing:
            existing.key_value = encrypted_value
            existing.updated_at = datetime.utcnow()
        else:
            new_key = APIKey(service_name=service_name, key_value=encrypted_value)
            self.db.add(new_key)

        self.db.commit()
        self.db.refresh(existing if existing else new_key)

        # Update in-memory cache
        global_settings_cache[service_name] = key_value
        return {"status": "success", "message": f"API key for {service_name} updated successfully."}

    def delete_key(self, service_name: str):
        """Delete an API key."""
        key = self.db.query(APIKey).filter(APIKey.service_name == service_name).first()
        if not key:
            return {"status": "error", "message": f"No key found for {service_name}."}

        self.db.delete(key)
        self.db.commit()
        global_settings_cache.pop(service_name, None)
        return {"status": "success", "message": f"{service_name} key deleted."}

    def test_key(self, service_name: str):
        """Stub method for testing API key validity."""
        # Placeholder: you can extend this later to ping real APIs.
        key = self.db.query(APIKey).filter(APIKey.service_name == service_name).first()
        if not key:
            return {"status": "error", "message": f"No key found for {service_name}."}

        decrypted = encryption_manager.decrypt(key.key_value)
        is_valid = bool(decrypted)
        return {
            "status": "valid" if is_valid else "invalid",
            "message": f"{service_name} key {'appears valid' if is_valid else 'failed validation'}."
        }

