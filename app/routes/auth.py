from loguru import logger

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.auth import (
    clear_session,
    csrf_protect,
    generate_reset_token,
    get_current_user,
    hash_password,
    make_csrf_token,
    set_csrf_cookie,
    set_session,
    verify_password,
    verify_reset_token,
)
from app.config import settings
from app.db import get_session
from app.models.project import User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ── Register ──────────────────────────────────────────────────────────────

@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request) -> HTMLResponse:
    token = make_csrf_token()
    resp = templates.TemplateResponse(request, "register.html", {"csrf_token": token})
    set_csrf_cookie(resp, token)
    return resp


@router.post("/register", response_model=None)
async def register(
    request: Request,
    _csrf: None = Depends(csrf_protect),
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_session),
) -> HTMLResponse | RedirectResponse:
    errors: dict[str, str] = {}

    username = username.strip().lower()
    if len(username) < 3:
        errors["username"] = "Must be at least 3 characters."
    if len(password) < 8:
        errors["password"] = "Must be at least 8 characters."
    if password != password_confirm:
        errors["password_confirm"] = "Passwords do not match."

    if not errors:
        existing = db.exec(select(User).where(User.username == username)).first()
        if existing:
            errors["username"] = "Username already taken."

    if errors:
        token = make_csrf_token()
        resp = templates.TemplateResponse(
            request,
            "register.html",
            {"errors": errors, "prefill_username": username, "csrf_token": token},
            status_code=422,
        )
        set_csrf_cookie(resp, token)
        return resp

    user = User(username=username, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)

    redirect = RedirectResponse(url="/gameplans", status_code=303)
    set_session(redirect, user.id)
    return redirect


# ── Login ─────────────────────────────────────────────────────────────────

@router.get("/login", response_model=None)
async def login_form(
    request: Request,
    user: User | None = Depends(get_current_user),
    reset: str = Query(default=""),
) -> HTMLResponse | RedirectResponse:
    if user:
        return RedirectResponse(url="/gameplans", status_code=303)
    token = make_csrf_token()
    resp = templates.TemplateResponse(
        request, "login.html",
        {"csrf_token": token, "reset_success": reset == "1"},
    )
    set_csrf_cookie(resp, token)
    return resp


@router.post("/login", response_model=None)
async def login(
    request: Request,
    _csrf: None = Depends(csrf_protect),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_session),
) -> HTMLResponse | RedirectResponse:
    username = username.strip().lower()
    user = db.exec(select(User).where(User.username == username)).first()
    if not user or not verify_password(password, user.hashed_password):
        token = make_csrf_token()
        resp = templates.TemplateResponse(
            request,
            "login.html",
            {
                "error": "Invalid username or password.",
                "prefill_username": username,
                "csrf_token": token,
            },
            status_code=401,
        )
        set_csrf_cookie(resp, token)
        return resp

    redirect = RedirectResponse(url="/gameplans", status_code=303)
    set_session(redirect, user.id)
    return redirect


# ── Logout ────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(_csrf: None = Depends(csrf_protect)) -> RedirectResponse:
    redirect = RedirectResponse(url="/login", status_code=303)
    clear_session(redirect)
    return redirect


# ── Forgot password ───────────────────────────────────────────────────────

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_form(request: Request) -> HTMLResponse:
    token = make_csrf_token()
    resp = templates.TemplateResponse(request, "forgot_password.html", {"csrf_token": token})
    set_csrf_cookie(resp, token)
    return resp


@router.post("/forgot-password", response_model=None)
async def forgot_password_submit(
    request: Request,
    _csrf: None = Depends(csrf_protect),
    username: str = Form(...),
    db: Session = Depends(get_session),
) -> HTMLResponse:
    user = db.exec(select(User).where(User.username == username.strip().lower())).first()

    reset_url: str | None = None
    if user:
        reset_token = generate_reset_token(user)
        reset_url = f"{settings.base_url}/reset-password?token={reset_token}"
        logger.info("[PASSWORD RESET] %s → %s", user.username, reset_url)

    token = make_csrf_token()
    resp = templates.TemplateResponse(
        request,
        "forgot_password.html",
        {
            "csrf_token": token,
            "sent": True,
            "app_env": settings.app_env,
            # Only expose the link in non-production (dev/staging convenience)
            "reset_url": reset_url if settings.app_env != "production" else None,
        },
    )
    set_csrf_cookie(resp, token)
    return resp


# ── Reset password ────────────────────────────────────────────────────────

@router.get("/reset-password", response_model=None)
async def reset_password_form(
    request: Request,
    token: str = Query(default=""),
) -> HTMLResponse | RedirectResponse:
    if not token:
        return RedirectResponse(url="/forgot-password", status_code=303)
    csrf = make_csrf_token()
    resp = templates.TemplateResponse(
        request, "reset_password.html", {"token": token, "csrf_token": csrf}
    )
    set_csrf_cookie(resp, csrf)
    return resp


@router.post("/reset-password", response_model=None)
async def reset_password_submit(
    request: Request,
    _csrf: None = Depends(csrf_protect),
    token: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_session),
) -> HTMLResponse | RedirectResponse:
    user = verify_reset_token(token, db)

    errors: dict[str, str] = {}
    if user is None:
        errors["token"] = "This reset link is invalid or has expired. Please request a new one."
    if len(password) < 8:
        errors["password"] = "Must be at least 8 characters."
    if password != password_confirm:
        errors["password_confirm"] = "Passwords do not match."

    if errors:
        csrf = make_csrf_token()
        resp = templates.TemplateResponse(
            request,
            "reset_password.html",
            {"token": token, "errors": errors, "csrf_token": csrf},
            status_code=422,
        )
        set_csrf_cookie(resp, csrf)
        return resp

    user.hashed_password = hash_password(password)  # type: ignore[union-attr]
    db.add(user)
    db.commit()
    logger.info("[PASSWORD RESET] Password changed for user id=%s", user.id)

    return RedirectResponse(url="/login?reset=1", status_code=303)
