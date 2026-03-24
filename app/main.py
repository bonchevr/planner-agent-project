import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from prometheus_client import Counter, Histogram
from sqlmodel import Session, select
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.db import create_db_and_tables, engine
from app.logging_config import setup_logging
from app.models.project import User
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.planner import router as planner_router

setup_logging()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        REQUEST_COUNT.labels(
            method=request.method,
            path=request.url.path,
            status_code=str(response.status_code),
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            path=request.url.path,
        ).observe(duration)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    _seed_admin()
    yield


def _seed_admin() -> None:
    """Ensure the configured admin_username has is_admin=True."""
    if not settings.admin_username:
        return
    with Session(engine) as db:
        user = db.exec(select(User).where(User.username == settings.admin_username)).first()
        if user and not user.is_admin:
            user.is_admin = True
            db.add(user)
            db.commit()
            logger.info("[STARTUP] Granted admin to '{}'", settings.admin_username)


app = FastAPI(
    title="Planner Agent",
    description="A guided project planning web app.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(planner_router)
app.include_router(admin_router)

