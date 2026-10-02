from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles, get_business_scope, get_business_from_api_key
from app.core.security import generate_api_key, hash_api_key
from app.models.user import User, UserRole
from app.models.transaction import Transaction, TransactionSource, PaymentMethod
from app.models.api_key import APIKey
from app.schemas.transaction_schemas import (
    TransactionCreate, TransactionOut, TransactionListResponse,
    CSVImportResult, APIKeyCreateResponse, APIKeyOut,
)
from app.services.csv_import import import_transactions_from_csv

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# ---------- 1. Add transaction manually ----------
@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.BUSINESS_MANAGER, UserRole.ANALYST)),
    business_id: Optional[int] = Depends(get_business_scope),
):
    if current_user.role == UserRole.ANALYST:
        # Analysts are read-heavy; adjust here if analysts should be allowed to add.
        raise HTTPException(status_code=403, detail="Analysts cannot add transactions.")

    if business_id is None:  # Admin with no business scope must not be creating tenant data blindly
        raise HTTPException(
            status_code=400,
            detail="Admins must act on behalf of a specific business; use a Business Manager account "
                   "to add transactions, or specify business context.",
        )

    duplicate = db.query(Transaction).filter(
        Transaction.business_id == business_id,
        Transaction.external_transaction_id == payload.external_transaction_id,
    ).first()
    if duplicate:
        raise HTTPException(status_code=400, detail="A transaction with this external_transaction_id already exists.")

    txn = Transaction(
        **payload.model_dump(),
        business_id=business_id,
        source=TransactionSource.MANUAL,
        created_by_user_id=current_user.id,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


# ---------- 2. Import transactions via CSV ----------
@router.post("/import-csv", response_model=CSVImportResult)
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.BUSINESS_MANAGER)),
    business_id: Optional[int] = Depends(get_business_scope),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")
    if business_id is None:
        raise HTTPException(
            status_code=400,
            detail="Admins must act on behalf of a specific business to import transactions.",
        )

    contents = await file.read()
    result = import_transactions_from_csv(
        file_bytes=contents,
        business_id=business_id,
        created_by_user_id=current_user.id,
        db=db,
    )
    return result


# ---------- 3. Receive transactions through API (machine-to-machine, API key auth) ----------
@router.post("/ingest", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def ingest_transaction_via_api(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    api_key: APIKey = Depends(get_business_from_api_key),
):
    """
    For external systems (e.g. the business's own checkout/payment backend)
    to push transactions in real time using an API key instead of a user login.
    """
    duplicate = db.query(Transaction).filter(
        Transaction.business_id == api_key.business_id,
        Transaction.external_transaction_id == payload.external_transaction_id,
    ).first()
    if duplicate:
        raise HTTPException(status_code=400, detail="A transaction with this external_transaction_id already exists.")

    txn = Transaction(
        **payload.model_dump(),
        business_id=api_key.business_id,
        source=TransactionSource.API,
        created_by_user_id=None,
    )
    db.add(txn)

    api_key.last_used_at = datetime.utcnow()
    db.commit()
    db.refresh(txn)
    return txn


# ---------- API key management (for Business Managers to issue keys to their own systems) ----------
@router.post("/api-keys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    label: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.BUSINESS_MANAGER)),
    business_id: Optional[int] = Depends(get_business_scope),
):
    if business_id is None:
        raise HTTPException(status_code=400, detail="Admins must specify a business to issue an API key for.")

    raw_key = generate_api_key()
    key_record = APIKey(
        business_id=business_id,
        key_hash=hash_api_key(raw_key),
        key_prefix=raw_key[:12],
        label=label,
    )
    db.add(key_record)
    db.commit()
    db.refresh(key_record)

    return APIKeyCreateResponse(
        id=key_record.id,
        label=key_record.label,
        api_key=raw_key,  # only time the raw key is ever returned
        key_prefix=key_record.key_prefix,
        created_at=key_record.created_at,
    )


@router.get("/api-keys", response_model=list[APIKeyOut])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.BUSINESS_MANAGER)),
    business_id: Optional[int] = Depends(get_business_scope),
):
    query = db.query(APIKey)
    if business_id is not None:
        query = query.filter(APIKey.business_id == business_id)
    return query.order_by(APIKey.created_at.desc()).all()


# ---------- 4/5/6. View all / search & filter / detail ----------
@router.get("", response_model=TransactionListResponse)
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    business_id: Optional[int] = Depends(get_business_scope),
    # Search & filter params
    search: Optional[str] = Query(None, description="Matches customer_id, external_transaction_id, or IP"),
    customer_id: Optional[str] = None,
    payment_method: Optional[PaymentMethod] = None,
    source: Optional[TransactionSource] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    location: Optional[str] = None,
    # Pagination
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    query = db.query(Transaction)

    if business_id is not None:
        query = query.filter(Transaction.business_id == business_id)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Transaction.customer_id.ilike(like),
                Transaction.external_transaction_id.ilike(like),
                Transaction.ip_address.ilike(like),
            )
        )
    if customer_id:
        query = query.filter(Transaction.customer_id == customer_id)
    if payment_method:
        query = query.filter(Transaction.payment_method == payment_method)
    if source:
        query = query.filter(Transaction.source == source)
    if min_amount is not None:
        query = query.filter(Transaction.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Transaction.amount <= max_amount)
    if date_from:
        query = query.filter(Transaction.transaction_datetime >= date_from)
    if date_to:
        query = query.filter(Transaction.transaction_datetime <= date_to)
    if location:
        query = query.filter(Transaction.location.ilike(f"%{location}%"))

    total = query.count()
    results = (
        query.order_by(Transaction.transaction_datetime.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TransactionListResponse(total=total, page=page, page_size=page_size, results=results)


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction_detail(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    business_id: Optional[int] = Depends(get_business_scope),
):
    query = db.query(Transaction).filter(Transaction.id == transaction_id)
    if business_id is not None:
        query = query.filter(Transaction.business_id == business_id)

    txn = query.first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return txn
