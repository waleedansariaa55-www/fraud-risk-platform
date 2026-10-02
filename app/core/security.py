import secrets
import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from app.core.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

# bcrypt has a 72-byte input limit; truncate defensively (applied consistently
# on both hash and verify, so this never breaks legitimate long passwords).
_MAX_PW_BYTES = 72


def _prep(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_PW_BYTES]


# ---------- Password hashing ----------
def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(_prep(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_prep(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        return False


# ---------- JWT tokens ----------
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ---------- API keys (for transaction ingestion) ----------
def generate_api_key() -> str:
    """Returns a raw API key to show the user ONCE. Only its hash is stored."""
    return f"frp_{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()
