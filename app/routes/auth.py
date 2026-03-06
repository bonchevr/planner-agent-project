from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.auth import (
    clear_session,
    csrf_protect,
    generate_csrf_token,
    get_current_user,
    hash_password,
    make_csrf_token,
    set_csrf_cookie,
    set_session,
    verify_password,
)
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
) -> HTMLResponse | RedirectResponse:
    if user:
        return RedirectResponse(url="/gameplans", status_code=303)
    token = make_csrf_token()
    resp = templates.TemplateResponse(request, "login.html", {"csrf_token": token})
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
