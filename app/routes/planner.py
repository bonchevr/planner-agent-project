from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.generator import GameplanGenerator, StackRecommender
from app.models.project import ProjectInput

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _build_project_input(
    project_name: str,
    problem_statement: str,
    core_features: str,
    target_platform: str,
    preferred_language: str,
    team_size: str,
    timeline: str,
    constraints: str,
) -> ProjectInput:
    try:
        return ProjectInput(
            project_name=project_name,
            problem_statement=problem_statement,
            core_features=core_features,
            target_platform=target_platform,
            preferred_language=preferred_language,
            team_size=team_size,
            timeline=timeline,
            constraints=constraints,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()],
        )


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@router.get("/interview", response_class=HTMLResponse)
async def interview_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "interview.html")


@router.post("/generate", response_class=HTMLResponse)
async def generate(
    request: Request,
    project_name: str = Form(...),
    problem_statement: str = Form(...),
    core_features: str = Form(...),
    target_platform: str = Form(...),
    preferred_language: str = Form(""),
    team_size: str = Form("solo"),
    timeline: str = Form(""),
    constraints: str = Form(""),
) -> HTMLResponse:
    project_input = _build_project_input(
        project_name, problem_statement, core_features, target_platform,
        preferred_language, team_size, timeline, constraints,
    )
    stack = StackRecommender.recommend(project_input)
    gameplan_md = GameplanGenerator.generate(project_input, stack)

    return templates.TemplateResponse(
        request,
        "gameplan.html",
        {
            "project": project_input,
            "gameplan_md": gameplan_md,
            "stack": stack,
        },
    )


@router.post("/download")
async def download(
    project_name: str = Form(...),
    problem_statement: str = Form(...),
    core_features: str = Form(...),
    target_platform: str = Form(...),
    preferred_language: str = Form(""),
    team_size: str = Form("solo"),
    timeline: str = Form(""),
    constraints: str = Form(""),
) -> Response:
    """Generate and stream the gameplan as a downloadable .md file."""
    project_input = _build_project_input(
        project_name, problem_statement, core_features, target_platform,
        preferred_language, team_size, timeline, constraints,
    )
    stack = StackRecommender.recommend(project_input)
    gameplan_md = GameplanGenerator.generate(project_input, stack)
    filename = f"{project_input.slug}.md"
    return Response(
        content=gameplan_md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
