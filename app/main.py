from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes.health import router as health_router
from app.routes.planner import router as planner_router

app = FastAPI(
    title="Planner Agent",
    description="A guided project planning web app.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

app.include_router(health_router)
app.include_router(planner_router)
