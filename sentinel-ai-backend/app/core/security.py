"""
Password hashing + JWT.

Uses the `bcrypt` library directly rather than passlib. passlib 1.7.4's
bcrypt backend is broken against bcrypt >= 4.1 (it misreads the backend
version and mishandles the 72-byte limit), and it is unmaintained; calling
bcrypt directly is fewer moving parts and one fewer thing to debug at 2am
before a review. Passwords are truncated to bcrypt's hard 72-byte limit
explicitly, which is what every bcrypt implementation does anyway.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(password), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, role: str, session_id: str) -> str:
    """Short-lived. `sid` ties the token to a server-side session row, so
    logout and replay detection can kill it before it expires. `role` is
    informational only — authorization reads the role from the database."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "type": "access", "sid": session_id, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str, session_id: str, jti: str, expires_at: int) -> str:
    """Single-use. `jti` must match the session row's current value; using it
    rotates that value. `expires_at` (epoch seconds) is fixed at login, so
    refreshing never extends a session beyond its original lifetime."""
    payload = {"sub": subject, "type": "refresh", "sid": session_id, "jti": jti, "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
