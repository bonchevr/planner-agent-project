import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.auth import _csrf_serializer, _signer, hash_password
from app.db import get_session
from app.main import app
from app.models.project import User


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    # Override get_session with the in-memory test session.
    # Do NOT use TestClient as a context manager — that would trigger the
    # lifespan and try to create/open the main planner.db file.
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(name="user")
def user_fixture(session: Session) -> User:
    u = User(username="testuser", hashed_password=hash_password("password123"))
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


@pytest.fixture(name="csrf_token")
def csrf_token_fixture() -> str:
    return _csrf_serializer.dumps("csrf")


@pytest.fixture(name="auth_client")
def auth_client_fixture(session: Session, user: User, csrf_token: str):
    """TestClient pre-loaded with a valid session cookie and CSRF cookie."""
    app.dependency_overrides[get_session] = lambda: session
    session_token = _signer.sign(str(user.id)).decode()
    client = TestClient(
        app,
        cookies={"session": session_token, "csrf_token": csrf_token},
    )
    yield client
    app.dependency_overrides.clear()
