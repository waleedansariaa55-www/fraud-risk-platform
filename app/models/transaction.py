import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class TransactionSource(str, enum.Enum):
    MANUAL = "manual"
    CSV_IMPORT = "csv_import"
    API = "api"


class PaymentMethod(str, enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    WALLET = "wallet"
    CRYPTO = "crypto"
    CASH_ON_DELIVERY = "cash_on_delivery"
    OTHER = "other"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Business-facing transaction identifier (may come from their own system,
    # e.g. via CSV/API). Unique per business, not globally.
    external_transaction_id = Column(String(255), nullable=False, index=True)

    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)

    # --- Core transaction fields (per spec) ---
    customer_id = Column(String(255), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    transaction_datetime = Column(DateTime, nullable=False, index=True)
    payment_method = Column(Enum(PaymentMethod), nullable=False, default=PaymentMethod.OTHER)

    ip_address = Column(String(64), nullable=True)
    location = Column(String(255), nullable=True)          # e.g. "Lahore, PK"
    device_info = Column(String(255), nullable=True)        # e.g. "iOS 17 / Safari"

    customer_account_age_days = Column(Integer, nullable=True)
    previous_transaction_count = Column(Integer, nullable=True)

    # --- Metadata ---
    source = Column(Enum(TransactionSource), nullable=False, default=TransactionSource.MANUAL)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    business = relationship("Business", back_populates="transactions")
    created_by = relationship("User")
