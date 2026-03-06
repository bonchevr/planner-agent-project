"""
Authentication utilities:
  - Password hashing/verification  (bcrypt)
  - Signed session cookie          (itsdangerous TimestampSigner)
  - CSRF double-submit token       (itsdangerous URLSafeSerializer)
  - FastAPI dependencies           (get_current_user, require_user, csrf_protect)
"""
from __future__ import annotations

from typing import Optional

import bcrypt as _bcrypt
from fastapi import Cookie, Depends, Form, HTTPException, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner, URLSafeSerializer, URLSafeTimedSerializer
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.models.project import User

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# Session cookie  (signed, 7-day max-age)
# ---------------------------------------------------------------------------

_SESSION_COOKIE = "session"
_SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days in seconds
_signer = TimestampSigner(settings.secret_key)


def set_session(response: Response, user_id: int) -> None:
    token = _signer.sign(str(user_id)).decode()
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=token,
        max_age=_SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(key=_SESSION_COOKIE, samesite="lax")


def _user_id_from_cookie(session_cookie: Optional[str]) -> Optional[int]:
    if not session_cookie:
        return None
    try:
        raw = _signer.unsign(session_cookie, max_age=_SESSION_MAX_AGE)
        return int(raw)
    except (BadSignature, SignatureExpired, ValueError):
        return None


# ---------------------------------------------------------------------------
# CSRF  (double-submit cookie, signed value)
# ---------------------------------------------------------------------------

_CSRF_COOKIE = "csrf_token"
_csrf_serializer = URLSafeSerializer(settings.secret_key, salt="csrf")


def make_csrf_token() -> str:
    """Generate and return a CSRF token string without setting any cookie."""
    return _csrf_serializer.dumps("csrf")


def set_csrf_cookie(response: Response, token: str) -> None:
    """Set the CSRF cookie directly on a response object."""
    response.set_cookie(
        key=_CSRF_COOKIE,
        value=token,
        httponly=False,
        samesite="lax",
        secure=settings.app_env == "production",
    )


def generate_csrf_token(response: Response) -> str:
    """Generate a CSRF token, set it as a cookie on *response*, and return the value.

    IMPORTANT: pass the actual Response/TemplateResponse that will be returned to
    the client — NOT the FastAPI-injected ``Response`` background parameter, because
    FastAPI does not merge background-response cookies into returned Response
    subclasses (e.g. TemplateResponse).
    """
    token = make_csrf_token()
    set_csrf_cookie(response, token)
    return token


def _validate_csrf(cookie_token: Optional[str], form_token: Optional[str]) -> bool:
    if not cookie_token or not form_token:
        return False
    if cookie_token != form_token:
        return False
    try:
        _csrf_serializer.loads(cookie_token)
        return True
    except BadSignature:
        return False


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

def get_current_user(
    request: Request,
    db: Session = Depends(get_session),
) -> Optional[User]:
    """Return the logged-in User or None."""
    token = request.cookies.get(_SESSION_COOKIE)
    user_id = _user_id_from_cookie(token)
    if user_id is None:
        return None
    return db.get(User, user_id)


def require_user(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Raise 401 if not logged in. Use as a route dependency."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return user


def csrf_protect(
    request: Request,
    csrf_token: str = Form(default=""),
) -> None:
    """Validate CSRF token on POST requests. Use as a route dependency."""
    cookie_token = request.cookies.get(_CSRF_COOKIE)
    if not _validate_csrf(cookie_token, csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token.")


# ---------------------------------------------------------------------------
# Password-reset token  (time-limited, self-invalidating after password change)
# ---------------------------------------------------------------------------

_RESET_MAX_AGE = 60 * 60  # 1 hour
_reset_serializer = URLSafeTimedSerializer(settings.secret_key, salt="password-reset")


def generate_reset_token(user: User) -> str:
    """Return a signed, time-limited reset token.

    Embeds a snippet of the current password hash so the token is
    automatically invalidated the moment the password is changed.
    """
    return _reset_serializer.dumps({"uid": user.id, "ph": user.hashed_password[:10]})


def verify_reset_token(token: str, db: Session) -> "Optional[User]":
    """Return the User if the token is valid and unexpired, else None."""
    try:
        data = _reset_serializer.loads(token, max_age=_RESET_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    user = db.get(User, data.get("uid"))
    if not user:
        return None
    # Invalidate if password already changed since token was issued
    if user.hashed_password[:10] != data.get("ph"):
        return None
    return user
