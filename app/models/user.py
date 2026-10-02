import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"                    # Full platform access, manages all businesses/users
    BUSINESS_MANAGER = "business_manager"  # Manages one business's transactions, users, settings
    ANALYST = "analyst"                # Read-heavy: views transactions, flags, reports; limited write


class Business(Base):
    """A tenant / company account. Business Managers and Analysts belong to one Business."""
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100), nullable=True)  # e.g. e-commerce, fintech, marketplace
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    users = relationship("User", back_populates="business")
    transactions = relationship("Transaction", back_populates="business")
    api_keys = relationship("APIKey", back_populates="business")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.ANALYST)

    # Admins have business_id = None (platform-wide). Business Managers / Analysts
    # are scoped to exactly one business.
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    business = relationship("Business", back_populates="users")
