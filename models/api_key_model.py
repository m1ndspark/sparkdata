# models/api_key_model.py

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class APIKey(Base):
    """Database model for storing encrypted API keys."""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, unique=True, nullable=False)
    key_value = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self, mask: bool = True):
        """Return a dict representation, masking key for UI display."""
        masked_value = (
            f"{self.key_value[:4]}...{self.key_value[-4:]}"
            if mask and len(self.key_value) > 8 else self.key_value
        )
        return {
            "service_name": self.service_name,
            "key_preview": masked_value,
            "updated_at": self.updated_at.strftime("%m-%d-%Y %I:%M %p") if self.updated_at else None,
        }
