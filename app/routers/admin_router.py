from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.security import hash_password
from app.models.user import User, Business, UserRole
from app.schemas.user_schemas import BusinessCreate, BusinessOut, UserOut, UserInvite

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/businesses", response_model=BusinessOut, status_code=201)
def create_business(
    payload: BusinessCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    business = Business(name=payload.name, industry=payload.industry)
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


@router.get("/businesses", response_model=list[BusinessOut])
def list_businesses(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    return db.query(Business).order_by(Business.created_at.desc()).all()


@router.post("/businesses/{business_id}/managers", response_model=UserOut, status_code=201)
def create_business_manager(
    business_id: int,
    payload: UserInvite,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    if payload.role != UserRole.BUSINESS_MANAGER:
        raise HTTPException(status_code=400, detail="This endpoint only creates Business Managers.")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.BUSINESS_MANAGER,
        business_id=business.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserOut])
def list_all_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    return db.query(User).order_by(User.created_at.desc()).all()
