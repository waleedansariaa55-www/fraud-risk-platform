from typing import Optional

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token, hash_api_key
from app.models.user import User, UserRole
from app.models.api_key import APIKey

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(*allowed_roles: UserRole):
    """Dependency factory: restricts an endpoint to specific roles."""
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' is not permitted to perform this action.",
            )
        return current_user
    return checker


def get_business_scope(current_user: User = Depends(get_current_user)) -> Optional[int]:
    """
    Returns the business_id a non-admin user is scoped to.
    Admins get None, meaning "no restriction" (endpoints handle this explicitly).
    """
    if current_user.role == UserRole.ADMIN:
        return None
    if current_user.business_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a business.",
        )
    return current_user.business_id


def get_business_from_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> APIKey:
    """Authenticates an inbound transaction POST via API key (for external systems)."""
    key_hash = hash_api_key(x_api_key)
    api_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash, APIKey.is_active == True  # noqa: E712
    ).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key.",
        )
    return api_key
