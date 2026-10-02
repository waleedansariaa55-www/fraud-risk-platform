from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class BusinessCreate(BaseModel):
    name: str
    industry: Optional[str] = None


class BusinessOut(BaseModel):
    id: int
    name: str
    industry: Optional[str] = None
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class UserRegister(BaseModel):
    """
    Self-registration is only for the FIRST admin (bootstrap) and for
    business managers creating their own business. Analysts are created
    by a Business Manager/Admin via the invite endpoint, not open registration.
    """
    full_name: str
    email: EmailStr
    password: str = Field(min_length=8)
    # If registering as a business manager, provide business_name to create a new business.
    business_name: Optional[str] = None
    industry: Optional[str] = None


class UserInvite(BaseModel):
    """Used by an Admin or Business Manager to create a new user under their business."""
    full_name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    business_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str
