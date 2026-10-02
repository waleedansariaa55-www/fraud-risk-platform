from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.models.user import User, Business, UserRole
from app.schemas.user_schemas import (
    UserRegister, UserInvite, UserLogin, UserOut,
    TokenResponse, RefreshRequest, BusinessOut,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _issue_tokens(user: User) -> TokenResponse:
    token_data = {"sub": str(user.id), "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """
    Public self-registration.
    - If this is the very first user in the system, they become ADMIN.
    - Otherwise, if business_name is provided, a new Business is created and
      the registrant becomes its BUSINESS_MANAGER.
    - Analysts cannot self-register; they must be invited (see /auth/invite).
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    is_first_user = db.query(User).count() == 0

    if is_first_user:
        role = UserRole.ADMIN
        business_id = None
    else:
        if not payload.business_name:
            raise HTTPException(
                status_code=400,
                detail="business_name is required to register a new Business Manager account.",
            )
        business = Business(name=payload.business_name, industry=payload.industry)
        db.add(business)
        db.commit()
        db.refresh(business)
        role = UserRole.BUSINESS_MANAGER
        business_id = business.id

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=role,
        business_id=business_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _issue_tokens(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    user.last_login = datetime.utcnow()
    db.commit()

    return _issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    user = db.query(User).filter(User.id == int(data["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")

    return _issue_tokens(user)


@router.post("/invite", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def invite_user(
    payload: UserInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.BUSINESS_MANAGER)),
):
    """
    Admin or Business Manager creates a new user (typically an Analyst,
    or another Business Manager if invited by an Admin).
    - Business Managers can only invite users into their own business, and
      cannot create other Business Managers or Admins.
    - Admins can invite into any business (business_id must be handled via
      a separate admin endpoint if needed) — here, Admin-invited users
      inherit no business unless the admin is also acting on behalf of one.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    if current_user.role == UserRole.BUSINESS_MANAGER:
        if payload.role != UserRole.ANALYST:
            raise HTTPException(
                status_code=403,
                detail="Business Managers may only invite Analysts.",
            )
        business_id = current_user.business_id
    else:  # ADMIN
        if payload.role == UserRole.ADMIN:
            business_id = None
        else:
            raise HTTPException(
                status_code=400,
                detail="Admin-created Business Manager/Analyst accounts need a business_id; "
                       "use the /businesses admin endpoint to create the business first, "
                       "then have that Business Manager invite Analysts.",
            )

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        business_id=business_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
