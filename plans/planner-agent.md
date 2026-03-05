# Planner Agent — Project Gameplan

> Generated: 5 March 2026
> Status: Active

## 1. Overview

**One-line summary:** A Python web app that walks users through a structured interview and generates a ready-to-use project gameplan as a Markdown document.

**Problem:** Solo developers and small teams start projects without a clear plan, leading to scope creep, missed milestones, and undefined success criteria. There is no lightweight, guided tool that produces a structured, reusable project gameplan in minutes.

**Target users:** Solo developers, small engineering teams, technical leads who want to plan before they code.

**Success metric:** A user can go from zero to a downloaded, fully populated project gameplan in under 5 minutes.

---

## 2. Tech Stack

| Layer        | Choice                  | Reason                                                                 |
|--------------|-------------------------|------------------------------------------------------------------------|
| Language     | Python 3.11+            | Primary language of the workspace; strong ecosystem for web & tooling. |
| Framework    | FastAPI + Jinja2        | Lightweight, async-ready API + server-side HTML templates; minimal JS. |
| UI layer     | HTMX                    | Progressive form steps without a JS SPA framework; keeps it Python-first. |
| Database     | SQLite (via SQLModel)   | Zero-config for solo dev; SQLModel gives Pydantic + SQLAlchemy in one. |
| Package mgr  | uv                      | Already used in this workspace (`scripts/uv_install.sh`).              |
| CI/CD        | GitHub Actions          | Standard, free for personal projects.                                  |
| Hosting      | Docker + Fly.io / Render| Simple container deploy, free tier available.                          |

---

## 3. Milestones

### Phase 0 — Setup & Foundations  _(~3 days)_
_Goal: A running FastAPI app with routing, templates, and test scaffold in place._
- [ ] Project directory structure created
- [ ] `requirements.txt` and `requirements-dev.txt` pinned
- [ ] FastAPI app boots (`uvicorn app.main:app`)
- [ ] Base HTML template with navigation
- [ ] `Makefile` with `dev`, `test`, `lint`, `docker-build` targets
- [ ] `.gitignore` and `README.md`
- [ ] GitHub Actions CI: lint + test on push

### Phase 1 — MVP Core  _(~1.5 weeks)_
_Goal: End-to-end flow: user completes interview → gameplan is generated and displayed._
- [ ] Multi-step interview form (questions from `project.agent.md`)
- [ ] Pydantic model for `ProjectInput`
- [ ] `GameplanGenerator` class: builds markdown from `ProjectInput`
- [ ] Tech-stack recommender: maps platform + language preference → stack table
- [ ] Gameplan viewer page (rendered Markdown → HTML)
- [ ] Download gameplan as `.md` file
- [ ] Unit tests for `GameplanGenerator`

### Phase 2 — Persistence & Polish  _(~1 week)_
_Goal: Users can save, list, and reload their gameplans._
- [ ] SQLite DB schema: `Project`, `Gameplan` tables (via SQLModel)
- [ ] Save gameplan to DB on generation
- [ ] Gameplans list page
- [ ] Load & edit existing gameplan
- [ ] Delete gameplan (with confirmation)
- [ ] Form validation with clear error messages
- [ ] Responsive CSS (mobile-friendly)

### Phase 3 — Launch Prep  _(~3 days)_
_Goal: Production-ready, tested, documented, containerised._
- [ ] Security review (OWASP checklist — see §5)
- [ ] Dockerfile + `docker-compose.yml`
- [ ] Deployment runbook (`plans/deploy/planner-agent-production.md`)
- [ ] Performance baseline (< 200 ms p99 for gameplan generation)
- [ ] User-facing `README.md` with screenshots
- [ ] `CHANGELOG.md` v1.0.0 entry

---

## 4. Detailed Task Breakdown

### Phase 0 tasks

| # | Task | Owner | Estimate | Notes |
|---|------|-------|----------|-------|
| 1 | Create `planner-agent/` directory structure | Solo | 30 min | See §File Structure |
| 2 | Pin dependencies with `uv pip compile` | Solo | 30 min | FastAPI, Jinja2, HTMX CDN, SQLModel, uvicorn |
| 3 | Implement `app/main.py` (app factory + health route) | Solo | 1 h | |
| 4 | Base HTML template (`base.html`) | Solo | 1 h | Include HTMX CDN, basic nav |
| 5 | Makefile targets | Solo | 30 min | `make dev`, `make test`, `make lint` |
| 6 | GitHub Actions workflow (`ci.yml`) | Solo | 1 h | ruff lint + pytest |

### Phase 1 tasks

| # | Task | Owner | Estimate | Notes |
|---|------|-------|----------|-------|
| 1 | `ProjectInput` Pydantic model | Solo | 1 h | Matches interview questions |
| 2 | Multi-step interview route + template | Solo | 2 h | HTMX step progression |
| 3 | `GameplanGenerator.generate()` | Solo | 3 h | Core logic; fully unit-tested |
| 4 | Stack recommender helper | Solo | 1.5 h | Rule-based map; no ML needed for v1 |
| 5 | Gameplan viewer route + template | Solo | 1.5 h | Render markdown → HTML with `mistune` |
| 6 | Download endpoint (`GET /gameplan/{id}/download`) | Solo | 1 h | Stream `.md` file as attachment |
| 7 | Unit tests for generator + recommender | Solo | 2 h | ≥ 80% coverage target |

### Phase 2 tasks

| # | Task | Owner | Estimate | Notes |
|---|------|-------|----------|-------|
| 1 | DB models (`Project`, `Gameplan`) + migration | Solo | 1.5 h | SQLModel + Alembic |
| 2 | Persist on generate; return ID in redirect | Solo | 1 h | |
| 3 | Gameplans list page | Solo | 1 h | |
| 4 | Load & edit gameplan | Solo | 2 h | Pre-populate form with saved values |
| 5 | Delete with confirmation (HTMX modal) | Solo | 1 h | |
| 6 | Input validation & error display | Solo | 1 h | FastAPI form validation |
| 7 | Responsive CSS | Solo | 1.5 h | CSS custom properties; no heavy framework |

---

## 5. Open Questions & Risks

| # | Question / Risk | Impact | Status |
|---|-----------------|--------|--------|
| 1 | Authentication needed? (multi-user vs single-user) | High | Open — default to single-user/local for v1 |
| 2 | Markdown rendering library: `mistune` vs `markdown2` | Low | Decide in Phase 1 task 5 |
| 3 | SQLite concurrency if deployed with multiple workers | Med | Use single Uvicorn worker for v1; revisit for v2 |
| 4 | XSS risk in rendered Markdown output | High | Sanitise HTML output with `bleach` before rendering |

---

## 6. Definition of Done (v1)

- [ ] All Phase 1 & 2 acceptance criteria met
- [ ] `pytest` suite passes with ≥ 80% coverage
- [ ] No P0 or P1 findings from `code-review.agent.md`
- [ ] Runs cleanly inside Docker container
- [ ] Deployment runbook exists at `plans/deploy/planner-agent-production.md`
- [ ] README includes setup instructions and a screenshot

---

## 7. File Structure (target)

```
planner-agent/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app factory
│   ├── config.py             # Settings (env vars)
│   ├── generator.py          # GameplanGenerator + StackRecommender
│   ├── models/
│   │   ├── __init__.py
│   │   └── project.py        # Pydantic + SQLModel models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── planner.py        # /interview, /generate, /gameplan/{id}
│   │   └── health.py         # GET /health
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── interview.html
│   │   └── gameplan.html
│   └── static/
│       └── style.css
├── tests/
│   ├── __init__.py
│   ├── test_generator.py
│   └── test_routes.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── README.md
├── requirements.txt
└── requirements-dev.txt
```
