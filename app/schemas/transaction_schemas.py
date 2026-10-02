from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.transaction import TransactionSource, PaymentMethod


class TransactionCreate(BaseModel):
    external_transaction_id: str
    customer_id: str
    amount: float = Field(gt=0)
    currency: str = "USD"
    transaction_datetime: datetime
    payment_method: PaymentMethod = PaymentMethod.OTHER

    ip_address: Optional[str] = None
    location: Optional[str] = None
    device_info: Optional[str] = None

    customer_account_age_days: Optional[int] = None
    previous_transaction_count: Optional[int] = None

    notes: Optional[str] = None


class TransactionOut(BaseModel):
    id: int
    external_transaction_id: str
    business_id: int
    customer_id: str
    amount: float
    currency: str
    transaction_datetime: datetime
    payment_method: PaymentMethod

    ip_address: Optional[str] = None
    location: Optional[str] = None
    device_info: Optional[str] = None

    customer_account_age_days: Optional[int] = None
    previous_transaction_count: Optional[int] = None

    source: TransactionSource
    created_by_user_id: Optional[int] = None
    created_at: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[TransactionOut]


class CSVImportResult(BaseModel):
    total_rows: int
    imported: int
    failed: int
    errors: list[str] = []


class APIKeyCreateResponse(BaseModel):
    id: int
    label: Optional[str] = None
    api_key: str  # shown only once, at creation
    key_prefix: str
    created_at: datetime


class APIKeyOut(BaseModel):
    id: int
    label: Optional[str] = None
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True
