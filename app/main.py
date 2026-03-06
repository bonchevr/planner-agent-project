from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app.db import create_db_and_tables
from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.planner import router as planner_router


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


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

