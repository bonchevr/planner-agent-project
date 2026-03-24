from loguru import logger

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.auth import (
    csrf_protect,
    generate_reset_token,
    hash_password,
    make_csrf_token,
    require_admin,
    set_csrf_cookie,
)
from app.config import settings
from app.db import get_session
from app.email import send_password_reset_email
from app.models.project import GameplanRecord, User

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


# ── Admin panel ───────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def admin_panel(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_session),
) -> HTMLResponse:
    users = db.exec(select(User).order_by(User.created_at)).all()
    token = make_csrf_token()
    resp = templates.TemplateResponse(
        request,
        "admin.html",
        {"user": admin, "csrf_token": token, "users": users},
    )
    set_csrf_cookie(resp, token)
    return resp


# ── Deactivate / reactivate user ─────────────────────────────────────────

@router.post("/{user_id}/deactivate", response_model=None)
async def deactivate_user(
    user_id: int,
    _csrf: None = Depends(csrf_protect),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_session),
) -> RedirectResponse:
    target = db.get(User, user_id)
    if target and target.id != admin.id:
        target.is_active = False
        db.add(target)
        db.commit()
        logger.info("[ADMIN] {} deactivated user id={}", admin.username, user_id)
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/{user_id}/activate", response_model=None)
async def activate_user(
    user_id: int,
    _csrf: None = Depends(csrf_protect),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_session),
) -> RedirectResponse:
    target = db.get(User, user_id)
    if target:
        target.is_active = True
        db.add(target)
        db.commit()
        logger.info("[ADMIN] {} activated user id={}", admin.username, user_id)
    return RedirectResponse(url="/admin", status_code=303)


# ── Toggle admin ──────────────────────────────────────────────────────────

@router.post("/{user_id}/make-admin", response_model=None)
async def make_admin(
    user_id: int,
    _csrf: None = Depends(csrf_protect),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_session),
) -> RedirectResponse:
    target = db.get(User, user_id)
    if target and target.id != admin.id:
        target.is_admin = True
        db.add(target)
        db.commit()
        logger.info("[ADMIN] {} granted admin to user id={}", admin.username, user_id)
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/{user_id}/remove-admin", response_model=None)
async def remove_admin(
    user_id: int,
    _csrf: None = Depends(csrf_protect),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_session),
) -> RedirectResponse:
    target = db.get(User, user_id)
    if target and target.id != admin.id:
        target.is_admin = False
        db.add(target)
        db.commit()
        logger.info("[ADMIN] {} removed admin from user id={}", admin.username, user_id)
    return RedirectResponse(url="/admin", status_code=303)


# ── Delete user ───────────────────────────────────────────────────────────

@router.post("/{user_id}/delete", response_model=None)
async def delete_user(
    user_id: int,
    _csrf: None = Depends(csrf_protect),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_session),
) -> RedirectResponse:
    target = db.get(User, user_id)
    if target and target.id != admin.id:
        # Remove all gameplans first (foreign key)
        gameplans = db.exec(select(GameplanRecord).where(GameplanRecord.user_id == user_id)).all()
        for gp in gameplans:
            db.delete(gp)
        db.delete(target)
        db.commit()
        logger.info("[ADMIN] {} deleted user id={}", admin.username, user_id)
    return RedirectResponse(url="/admin", status_code=303)


# ── Reset password ────────────────────────────────────────────────────────

@router.post("/{user_id}/reset-password", response_model=None)
async def admin_reset_password(
    request: Request,
    user_id: int,
    _csrf: None = Depends(csrf_protect),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_session),
) -> RedirectResponse:
    target = db.get(User, user_id)
    if target and target.email:
        reset_token = generate_reset_token(target)
        reset_url = f"{settings.base_url}/reset-password?token={reset_token}"
        if settings.app_env == "production":
            send_password_reset_email(target.email, reset_url)
        else:
            logger.info("[ADMIN PASSWORD RESET] {} → {}", target.username, reset_url)
        logger.info("[ADMIN] {} triggered password reset for user id={}", admin.username, user_id)
    return RedirectResponse(url="/admin", status_code=303)
