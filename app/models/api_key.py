from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class APIKey(Base):
    """API key used by a business's external systems to POST transactions."""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)

    key_hash = Column(String(128), nullable=False, unique=True, index=True)
    key_prefix = Column(String(12), nullable=False)  # shown in UI, e.g. "frp_ab12"
    label = Column(String(255), nullable=True)        # e.g. "Production server key"

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    business = relationship("Business", back_populates="api_keys")
