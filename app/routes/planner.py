import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlmodel import Session, select

from app.auth import csrf_protect, make_csrf_token, require_user, set_csrf_cookie
from app.config import settings
from app.db import get_session
from app.generator import GameplanGenerator, StackRecommender, render_md
from app.models.project import PROJECT_STATUSES, GameplanRecord, ProjectInput, User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["render_md"] = render_md


# ── helpers ─────────────────────────────────────────────────────────

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


def _assert_owner(record: GameplanRecord, user: User) -> None:
    """Raise 403 if the record doesn't belong to the current user."""
    if record.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your gameplan.")


# ── public pages ───────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@router.get("/share/{share_token}", response_class=HTMLResponse)
async def public_gameplan(
    request: Request,
    share_token: str,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Read-only public view — no authentication required."""
    record = session.exec(
        select(GameplanRecord).where(GameplanRecord.share_token == share_token)
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Shared gameplan not found.")
    return templates.TemplateResponse(
        request,
        "shared_gameplan.html",
        {"record": record},
    )


@router.get("/share/{share_token}/download")
async def public_download(
    share_token: str,
    session: Session = Depends(get_session),
) -> Response:
    """Download the .md file — no authentication required."""
    record = session.exec(
        select(GameplanRecord).where(GameplanRecord.share_token == share_token)
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Shared gameplan not found.")
    return Response(
        content=record.gameplan_md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{record.slug}.md"'},
    )


# ── protected pages (require login) ───────────────────────────────

@router.get("/interview", response_class=HTMLResponse)
async def interview_form(
    request: Request,
    user: User = Depends(require_user),
) -> HTMLResponse:
    token = make_csrf_token()
    resp = templates.TemplateResponse(request, "interview.html", {"user": user, "csrf_token": token})
    set_csrf_cookie(resp, token)
    return resp


@router.get("/gameplans", response_class=HTMLResponse)
async def list_gameplans(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    q: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
) -> HTMLResponse:
    query = select(GameplanRecord).where(GameplanRecord.user_id == user.id)
    if status_filter and status_filter in PROJECT_STATUSES:
        query = query.where(GameplanRecord.status == status_filter)
    query = query.order_by(GameplanRecord.created_at.desc())
    records = session.exec(query).all()

    # Client-side text search (case-insensitive substring across name + problem)
    if q:
        q_lower = q.lower()
        records = [
            r for r in records
            if q_lower in r.project_name.lower()
            or q_lower in r.problem_statement.lower()
            or q_lower in r.tags.lower()
        ]

    token = make_csrf_token()
    resp = templates.TemplateResponse(
        request,
        "gameplans.html",
        {
            "records": records,
            "user": user,
            "csrf_token": token,
            "q": q or "",
            "status_filter": status_filter or "",
            "all_statuses": PROJECT_STATUSES,
        },
    )
    set_csrf_cookie(resp, token)
    return resp


@router.get("/gameplan/{record_id}", response_class=HTMLResponse)
async def view_gameplan(
    request: Request,
    record_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    _assert_owner(record, user)
    token = make_csrf_token()
    share_url = (
        f"{settings.base_url}/share/{record.share_token}"
        if record.share_token
        else None
    )
    resp = templates.TemplateResponse(
        request,
        "gameplan.html",
        {"record": record, "user": user, "csrf_token": token, "share_url": share_url},
    )
    set_csrf_cookie(resp, token)
    return resp


@router.get("/gameplan/{record_id}/edit", response_class=HTMLResponse)
async def edit_gameplan_form(
    request: Request,
    record_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    _assert_owner(record, user)
    token = make_csrf_token()
    resp = templates.TemplateResponse(
        request,
        "interview.html",
        {
            "prefill": record,
            "record_id": record_id,
            "form_action": f"/gameplan/{record_id}/edit",
            "user": user,
            "csrf_token": token,
        },
    )
    set_csrf_cookie(resp, token)
    return resp


@router.get("/gameplan/{record_id}/download")
async def download_gameplan(
    record_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
) -> Response:
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    _assert_owner(record, user)
    return Response(
        content=record.gameplan_md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{record.slug}.md"'},
    )


# ── protected form submissions ──────────────────────────────────────

@router.post("/generate")
async def generate(
    request: Request,
    _csrf: None = Depends(csrf_protect),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    project_name: str = Form(...),
    problem_statement: str = Form(...),
    core_features: str = Form(...),
    target_platform: str = Form(...),
    preferred_language: str = Form(""),
    team_size: str = Form("solo"),
    timeline: str = Form(""),
    constraints: str = Form(""),
    tags: str = Form(""),
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
                "user": user,
            },
            status_code=422,
        )

    stack = StackRecommender.recommend(project_input)
    gameplan_md = GameplanGenerator.generate(project_input, stack)

    # Normalise tags
    clean_tags = ", ".join(t.strip() for t in tags.split(",") if t.strip())

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
        tags=clean_tags,
        user_id=user.id,
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    return RedirectResponse(url=f"/gameplan/{record.id}", status_code=303)


@router.post("/gameplan/{record_id}/edit")
async def edit_gameplan_save(
    request: Request,
    record_id: int,
    _csrf: None = Depends(csrf_protect),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    project_name: str = Form(...),
    problem_statement: str = Form(...),
    core_features: str = Form(...),
    target_platform: str = Form(...),
    preferred_language: str = Form(""),
    team_size: str = Form("solo"),
    timeline: str = Form(""),
    constraints: str = Form(""),
    tags: str = Form(""),
):
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    _assert_owner(record, user)

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
                "user": user,
            },
            status_code=422,
        )

    stack = StackRecommender.recommend(project_input)
    gameplan_md = GameplanGenerator.generate(project_input, stack)
    clean_tags = ", ".join(t.strip() for t in tags.split(",") if t.strip())

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
    record.tags = clean_tags

    session.add(record)
    session.commit()

    return RedirectResponse(url=f"/gameplan/{record_id}", status_code=303)


@router.post("/gameplan/{record_id}/delete")
async def delete_gameplan(
    record_id: int,
    _csrf: None = Depends(csrf_protect),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    _assert_owner(record, user)
    session.delete(record)
    session.commit()
    return RedirectResponse(url="/gameplans", status_code=303)


@router.post("/gameplan/{record_id}/share")
async def share_gameplan(
    record_id: int,
    _csrf: None = Depends(csrf_protect),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    """Generate a UUID share token for this gameplan (idempotent — existing token kept)."""
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    _assert_owner(record, user)
    if not record.share_token:
        record.share_token = str(uuid.uuid4())
        session.add(record)
        session.commit()
    return RedirectResponse(url=f"/gameplan/{record_id}", status_code=303)


@router.post("/gameplan/{record_id}/revoke")
async def revoke_share(
    record_id: int,
    _csrf: None = Depends(csrf_protect),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    """Remove the share token, making the gameplan private again."""
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    _assert_owner(record, user)
    record.share_token = None
    session.add(record)
    session.commit()
    return RedirectResponse(url=f"/gameplan/{record_id}", status_code=303)


@router.post("/download")
async def download_post(
    _csrf: None = Depends(csrf_protect),
    user: User = Depends(require_user),
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


# ── Status & progress updates ───────────────────────────────────────────

@router.post("/gameplan/{record_id}/status")
async def update_status(
    record_id: int,
    _csrf: None = Depends(csrf_protect),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    status: str = Form(...),
):
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    _assert_owner(record, user)
    if status not in PROJECT_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status value.")
    record.status = status
    session.add(record)
    session.commit()
    return RedirectResponse(url=f"/gameplan/{record_id}", status_code=303)


@router.post("/gameplan/{record_id}/progress")
async def update_progress(
    record_id: int,
    _csrf: None = Depends(csrf_protect),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    progress: int = Form(...),
):
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    _assert_owner(record, user)
    record.progress = max(0, min(100, progress))
    session.add(record)
    session.commit()
    return RedirectResponse(url=f"/gameplan/{record_id}", status_code=303)


@router.post("/gameplan/{record_id}/notes")
async def update_notes(
    record_id: int,
    _csrf: None = Depends(csrf_protect),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    notes: str = Form(""),
):
    record = session.get(GameplanRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Gameplan not found")
    _assert_owner(record, user)
    record.notes = notes.strip()
    session.add(record)
    session.commit()
    return RedirectResponse(url=f"/gameplan/{record_id}", status_code=303)

