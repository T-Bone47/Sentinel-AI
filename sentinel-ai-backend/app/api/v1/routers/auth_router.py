"""
Authentication, server-side sessions, and the permission guard.

Sessions
  Each login creates one `auth_sessions` row. The access token is short-lived
  and carries that row's id, so logout (or replay detection) revokes it
  immediately instead of waiting for it to expire. The refresh token is
  single-use: every refresh rotates it, and presenting one that was already
  used revokes the whole session, because that only happens when a token has
  been copied.

Authorization
  `require_permission(...)` is the only route guard. It consults the central
  matrix in `app/core/permissions.py` using the role stored on the user's
  database row — the role claim inside the token is never trusted.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import permissions
from app.core.config import settings
from app.core.login_throttle import throttle
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database.session import get_db
from app.models import AuthSession, User

router = APIRouter()
bearer = HTTPBearer(auto_error=False)

# Security-relevant events (token reuse, lockouts). Never log a token, a
# password or an email address: users are identified by their UUID, and an
# email that may not belong to any account by `_account_ref`.
logger = logging.getLogger("sentinel.auth")


def _account_ref(email: str) -> str:
    """Short SHA-256 of the normalised email, so repeated lockouts of one
    address can be correlated in the log without writing the address down.
    Pseudonymous, not anonymous: anyone who guesses the address can confirm it."""
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:12]

# Compared against when the email is unknown, so a login attempt costs one
# bcrypt verification either way and response time does not reveal which
# addresses are registered.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


def _unauthorized(detail: str = "Invalid or expired token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"}
    )


async def _load_session(db: AsyncSession, payload: dict[str, Any]) -> tuple[User, AuthSession] | None:
    """The live (user, session) pair a token refers to, or None."""
    session_id, subject = payload.get("sid"), payload.get("sub")
    if not isinstance(session_id, str) or not isinstance(subject, str):
        return None
    row = (
        await db.execute(
            select(User, AuthSession)
            .join(AuthSession, AuthSession.user_id == User.id)
            .where(AuthSession.id == session_id, User.email == subject)
        )
    ).first()
    if row is None:
        return None
    user, session = row
    if session.revoked_at is not None or not user.is_active:
        return None
    return user, session


async def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, AuthSession]:
    if credentials is None:
        raise _unauthorized("Missing bearer token")
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise _unauthorized()
    current = await _load_session(db, payload)
    if current is None:
        raise _unauthorized()
    return current


async def get_current_user(current: tuple[User, AuthSession] = Depends(get_current_session)) -> User:
    return current[0]


def ensure_allowed(user: User, *resources: str, action: str = permissions.READ) -> None:
    """403 unless the user's role holds `action` on every listed resource."""
    if not all(permissions.is_allowed(user.role, resource, action) for resource in resources):
        raise HTTPException(status_code=403, detail="You do not have permission to access this resource")


@lru_cache(maxsize=None)
def require_permission(*resources: str, action: str = permissions.READ) -> Callable:
    """Route guard. List every dataset the endpoint returns rows from:

        @router.get("/x", dependencies=[Depends(require_permission("risks", "controls"))])

    Cached so the same guard used at router level and as a handler parameter
    is one dependency and runs once per request.
    """

    async def dependency(user: User = Depends(get_current_user)) -> User:
        ensure_allowed(user, *resources, action=action)
        return user

    dependency.permission_resources = resources  # introspection for tests and docs
    return dependency


def _tokens(user: User, session_id: str, refresh_jti: str, expires_at: int) -> dict[str, str]:
    return {
        "access_token": create_access_token(user.email, user.role.value, session_id),
        "refresh_token": create_refresh_token(user.email, session_id, refresh_jti, expires_at),
        "token_type": "bearer",
    }


@router.post("/login", tags=["auth"], summary="Exchange email + password for a session", response_model=None)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    wait = throttle.retry_after(body.email)
    if wait:
        raise HTTPException(
            status_code=429,
            detail="Too many failed sign-in attempts. Try again later.",
            headers={"Retry-After": str(wait)},
        )

    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    # bcrypt is deliberately slow (~0.25 s). Run it off the event loop, or every
    # sign-in attempt stalls every other request in the process.
    password_ok = await asyncio.to_thread(
        verify_password, body.password, user.hashed_password if user else _DUMMY_HASH
    )
    if user is None or not password_ok:
        throttle.record_failure(body.email)
        if throttle.retry_after(body.email):
            logger.warning("sign-in locked after repeated failures (account_ref=%s)", _account_ref(body.email))
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    throttle.record_success(body.email)

    now = int(time.time())
    # Housekeeping: this user's dead sessions are no longer needed for anything.
    await db.execute(
        delete(AuthSession).where(
            AuthSession.user_id == user.id,
            or_(AuthSession.expires_at < now, AuthSession.revoked_at.is_not(None)),
        )
    )
    session_id, refresh_jti = str(uuid.uuid4()), str(uuid.uuid4())
    expires_at = now + settings.refresh_token_expire_days * 86400
    db.add(AuthSession(id=session_id, user_id=user.id, refresh_jti=refresh_jti, expires_at=expires_at))
    await db.commit()

    return {
        "data": {
            **_tokens(user, session_id, refresh_jti, expires_at),
            "role": user.role.value,
            "email": user.email,
            "full_name": user.full_name,
        },
        "error": None,
    }


@router.post("/refresh", tags=["auth"], summary="Rotate the refresh token and get a new access token", response_model=None)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    invalid = _unauthorized("Invalid or expired refresh token")
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh" or not isinstance(payload.get("jti"), str):
        raise invalid
    current = await _load_session(db, payload)
    if current is None:
        raise invalid
    user, session = current
    session_id, expires_at = session.id, session.expires_at

    # Atomic single use: only the request holding the current jti can swap it.
    new_jti = str(uuid.uuid4())
    rotated = await db.execute(
        update(AuthSession)
        .where(
            AuthSession.id == session_id,
            AuthSession.refresh_jti == payload["jti"],
            AuthSession.revoked_at.is_(None),
        )
        .values(refresh_jti=new_jti)
    )
    if rotated.rowcount != 1:
        # A refresh token that was already used has been presented again.
        # That means it was copied, so the whole session is ended.
        await db.execute(
            update(AuthSession).where(AuthSession.id == session_id).values(revoked_at=datetime.now(timezone.utc))
        )
        logger.warning(
            "refresh token reuse detected; session ended (user_id=%s session_id=%s)", user.id, session_id
        )
        await db.commit()
        raise invalid
    await db.commit()

    return {"data": _tokens(user, session_id, new_jti, expires_at), "error": None}


@router.post("/logout", tags=["auth"], summary="End the current session", response_model=None)
async def logout(
    current: tuple[User, AuthSession] = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _, session = current
    await db.execute(
        update(AuthSession).where(AuthSession.id == session.id).values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"data": {"logged_out": True}, "error": None}


@router.get("/me", tags=["auth"], summary="Current authenticated user", response_model=None)
async def me(user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "data": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_active": user.is_active,
            "employee_id": user.employee_id,
            # Resources this role may read, so a client can hide what would
            # only return 403. Informational: the server enforces regardless.
            "permissions": permissions.readable_resources(user.role),
        },
        "error": None,
    }
