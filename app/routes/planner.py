import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlmodel import Session, select

from app.db import get_session
from app.generator import GameplanGenerator, StackRecommender, render_md
from app.models.project import GameplanRecord, ProjectInput

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["render_md"] = render_md


# ── helpers ───────────────────────────────────────────────────────────────

def _try_build_project_input(
    project_name: str,
    problem_statement: str,
    core_features: str,
    target_platform: str,
    preferred_language: str,
    team_size: str,
    timeline: str,
    constraints: str,
) -> tuple["ProjectInput | None", "dict[str, str]"]:
    """Return (ProjectInput, {}) on success, or (None, {field: message}) on failure."""
    try:
        return (
            ProjectInput(
                project_name=project_name,
                problem_statement=problem_statement,
                core_features=core_features,
                target_platform=target_platform,
                preferred_language=preferred_language,
                team_size=team_size,
                timeline=timeline,
                constraints=constraints,
            ),
            {},
        )
    except ValidationError as exc:
        errors = {
            str(e["loc"][0]): e["msg"].removeprefix("Value error, ")
            for e in exc.errors()
        }
        return None, errors


def _prefill_dict(
    project_name: str,
    problem_statement: str,
    core_features: str,
    target_platform: str,
    preferred_language: str,
    team_size: str,
    timeline: str,
    constraints: str,
) -> dict:
    return {
        "project_name": project_name,
        "problem_statement": problem_statement,
        "core_features": core_features,
        "target_platform": target_platform,
        "preferred_language": preferred_language,
        "team_size": team_size,
        "timeline": timeline,
        "constraints": constraints,
    }


# ── pages ────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@router.get("/interview", response_class=HTMLResponse)
async def interview_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "interview.html")


@router.get("/gameplans", response_class=HTMLResponse)
async def list_gameplans(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    records = session.exec(
        select(GameplanRecord).order_by(GameplanRecord.created_at.desc())
    ).all()
    return templates.TemplateResponse(request, "gameplans.html", {"records": records})


@router.get("/gameplan/{record_id}", response_class=HTMLResponse)
async def view_gameplan(
    request: Request,
    record_id: int,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    return templates.TemplateResponse(request, "gameplan.html", {"record": record})


@router.get("/gameplan/{record_id}/edit", response_class=HTMLResponse)
async def edit_gameplan_form(
    request: Request,
    record_id: int,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    return templates.TemplateResponse(
        request,
        "interview.html",
        {
            "prefill": record,
            "record_id": record_id,
            "form_action": f"/gameplan/{record_id}/edit",
        },
    )


@router.get("/gameplan/{record_id}/download")
async def download_gameplan(
    record_id: int,
    session: Session = Depends(get_session),
) -> Response:
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    return Response(
        content=record.gameplan_md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{record.slug}.md"'},
    )


# ── form submissions ──────────────────────────────────────────────────────

@router.post("/generate")
async def generate(
    request: Request,
    session: Session = Depends(get_session),
    project_name: str = Form(...),
    problem_statement: str = Form(...),
    core_features: str = Form(...),
    target_platform: str = Form(...),
    preferred_language: str = Form(""),
    team_size: str = Form("solo"),
    timeline: str = Form(""),
    constraints: str = Form(""),
):
    project_input, errors = _try_build_project_input(
        project_name, problem_statement, core_features, target_platform,
        preferred_language, team_size, timeline, constraints,
    )
    if errors:
        return templates.TemplateResponse(
            request,
            "interview.html",
            {
                "errors": errors,
                "prefill": _prefill_dict(
                    project_name, problem_statement, core_features, target_platform,
                    preferred_language, team_size, timeline, constraints,
                ),
            },
            status_code=422,
        )

    stack = StackRecommender.recommend(project_input)
    gameplan_md = GameplanGenerator.generate(project_input, stack)

    record = GameplanRecord(
        slug=project_input.slug,
        project_name=project_input.project_name,
        problem_statement=project_input.problem_statement,
        core_features=project_input.core_features,
        target_platform=project_input.target_platform,
        preferred_language=project_input.preferred_language,
        team_size=project_input.team_size,
        timeline=project_input.timeline,
        constraints=project_input.constraints,
        gameplan_md=gameplan_md,
        stack_json=json.dumps(stack),
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    return RedirectResponse(url=f"/gameplan/{record.id}", status_code=303)


@router.post("/gameplan/{record_id}/edit")
async def edit_gameplan_save(
    request: Request,
    record_id: int,
    session: Session = Depends(get_session),
    project_name: str = Form(...),
    problem_statement: str = Form(...),
    core_features: str = Form(...),
    target_platform: str = Form(...),
    preferred_language: str = Form(""),
    team_size: str = Form("solo"),
    timeline: str = Form(""),
    constraints: str = Form(""),
):
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")

    project_input, errors = _try_build_project_input(
        project_name, problem_statement, core_features, target_platform,
        preferred_language, team_size, timeline, constraints,
    )
    if errors:
        return templates.TemplateResponse(
            request,
            "interview.html",
            {
                "errors": errors,
                "prefill": _prefill_dict(
                    project_name, problem_statement, core_features, target_platform,
                    preferred_language, team_size, timeline, constraints,
                ),
                "record_id": record_id,
                "form_action": f"/gameplan/{record_id}/edit",
            },
            status_code=422,
        )

    stack = StackRecommender.recommend(project_input)
    gameplan_md = GameplanGenerator.generate(project_input, stack)

    record.slug = project_input.slug
    record.project_name = project_input.project_name
    record.problem_statement = project_input.problem_statement
    record.core_features = project_input.core_features
    record.target_platform = project_input.target_platform
    record.preferred_language = project_input.preferred_language
    record.team_size = project_input.team_size
    record.timeline = project_input.timeline
    record.constraints = project_input.constraints
    record.gameplan_md = gameplan_md
    record.stack_json = json.dumps(stack)

    session.add(record)
    session.commit()

    return RedirectResponse(url=f"/gameplan/{record_id}", status_code=303)


@router.post("/gameplan/{record_id}/delete")
async def delete_gameplan(
    record_id: int,
    session: Session = Depends(get_session),
):
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    session.delete(record)
    session.commit()
    return RedirectResponse(url="/gameplans", status_code=303)


@router.post("/download")
async def download_post(
    project_name: str = Form(...),
    problem_statement: str = Form(...),
    core_features: str = Form(...),
    target_platform: str = Form(...),
    preferred_language: str = Form(""),
    team_size: str = Form("solo"),
    timeline: str = Form(""),
    constraints: str = Form(""),
) -> Response:
    """Generate and stream a .md file without persisting to DB."""
    project_input, errors = _try_build_project_input(
        project_name, problem_statement, core_features, target_platform,
        preferred_language, team_size, timeline, constraints,
    )
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    stack = StackRecommender.recommend(project_input)
    gameplan_md = GameplanGenerator.generate(project_input, stack)
    filename = f"{project_input.slug}.md"
    return Response(
        content=gameplan_md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



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
