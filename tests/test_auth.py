"""Tests for authentication routes: register, login, logout."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth import _csrf_serializer, _signer, hash_password
from app.db import get_session
from app.main import app
from app.models.project import User


def _make_csrf(session: Session) -> tuple[TestClient, str]:
    """Return an unauthenticated client + a valid CSRF token."""
    csrf_token = _csrf_serializer.dumps("csrf")
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app, cookies={"csrf_token": csrf_token})
    return client, csrf_token


# ── Register ──────────────────────────────────────────────────────────────────


def test_register_form_renders(session: Session):
    client, _ = _make_csrf(session)
    response = client.get("/register")
    assert response.status_code == 200
    assert b"username" in response.content
    app.dependency_overrides.clear()


def test_register_success(session: Session):
    client, csrf = _make_csrf(session)
    response = client.post(
        "/register",
        data={
            "username": "alice",
            "password": "securepass",
            "password_confirm": "securepass",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/gameplans"
    user = session.exec(__import__("sqlmodel").select(User).where(User.username == "alice")).first()
    assert user is not None
    app.dependency_overrides.clear()


def test_register_duplicate_username(session: Session):
    u = User(username="bob", hashed_password=hash_password("password123"))
    session.add(u)
    session.commit()

    client, csrf = _make_csrf(session)
    response = client.post(
        "/register",
        data={
            "username": "bob",
            "password": "password123",
            "password_confirm": "password123",
            "csrf_token": csrf,
        },
    )
    assert response.status_code == 422
    assert b"already taken" in response.content
    app.dependency_overrides.clear()


def test_register_password_too_short(session: Session):
    client, csrf = _make_csrf(session)
    response = client.post(
        "/register",
        data={
            "username": "carol",
            "password": "short",
            "password_confirm": "short",
            "csrf_token": csrf,
        },
    )
    assert response.status_code == 422
    assert b"8 characters" in response.content
    app.dependency_overrides.clear()


def test_register_password_mismatch(session: Session):
    client, csrf = _make_csrf(session)
    response = client.post(
        "/register",
        data={
            "username": "dave",
            "password": "password123",
            "password_confirm": "different123",
            "csrf_token": csrf,
        },
    )
    assert response.status_code == 422
    assert b"do not match" in response.content
    app.dependency_overrides.clear()


def test_register_csrf_rejected(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app, cookies={"csrf_token": "validcookie"})
    response = client.post(
        "/register",
        data={
            "username": "eve",
            "password": "password123",
            "password_confirm": "password123",
            "csrf_token": "wrong-token",
        },
    )
    assert response.status_code == 403
    app.dependency_overrides.clear()


# ── Login ─────────────────────────────────────────────────────────────────────


def test_login_form_renders(session: Session):
    client, _ = _make_csrf(session)
    response = client.get("/login")
    assert response.status_code == 200
    assert b"password" in response.content
    app.dependency_overrides.clear()


def test_login_success(session: Session):
    u = User(username="frank", hashed_password=hash_password("mypassword"))
    session.add(u)
    session.commit()

    client, csrf = _make_csrf(session)
    response = client.post(
        "/login",
        data={"username": "frank", "password": "mypassword", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/gameplans"
    assert "session" in response.cookies
    app.dependency_overrides.clear()


def test_login_wrong_password(session: Session):
    u = User(username="grace", hashed_password=hash_password("rightpass"))
    session.add(u)
    session.commit()

    client, csrf = _make_csrf(session)
    response = client.post(
        "/login",
        data={"username": "grace", "password": "wrongpass", "csrf_token": csrf},
    )
    assert response.status_code == 401
    assert b"Invalid" in response.content
    app.dependency_overrides.clear()


def test_login_unknown_user(session: Session):
    client, csrf = _make_csrf(session)
    response = client.post(
        "/login",
        data={"username": "nobody", "password": "password", "csrf_token": csrf},
    )
    assert response.status_code == 401
    app.dependency_overrides.clear()


# ── Logout ────────────────────────────────────────────────────────────────────


def test_logout_clears_session(session: Session, user: User, csrf_token: str):
    session_token = _signer.sign(str(user.id)).decode()
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(
        app,
        cookies={"session": session_token, "csrf_token": csrf_token},
    )
    response = client.post(
        "/logout",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    # The session cookie should be deleted (empty value or absent)
    session_cookie = response.cookies.get("session")
    assert not session_cookie
    app.dependency_overrides.clear()


def test_logout_csrf_rejected(session: Session, user: User):
    session_token = _signer.sign(str(user.id)).decode()
    bad_csrf = _csrf_serializer.dumps("csrf")
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(
        app,
        cookies={"session": session_token, "csrf_token": bad_csrf},
    )
    response = client.post(
        "/logout",
        data={"csrf_token": "tampered"},
    )
    assert response.status_code == 403
    app.dependency_overrides.clear()


# ── Already-logged-in redirect ────────────────────────────────────────────────


def test_login_page_redirects_when_authenticated(
    session: Session, user: User, csrf_token: str
):
    session_token = _signer.sign(str(user.id)).decode()
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(
        app,
        cookies={"session": session_token, "csrf_token": csrf_token},
    )
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/gameplans"
    app.dependency_overrides.clear()
