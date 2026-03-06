# Planner Agent — Project Gameplan

> Generated: 5 March 2026
> Last updated: 6 March 2026
> Status: v0.2.0 — Phase 4 Complete ✅

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
- [x] Project directory structure created
- [x] `requirements.txt` and `requirements-dev.txt` pinned
- [x] FastAPI app boots (`uvicorn app.main:app`)
- [x] Base HTML template with navigation
- [x] `Makefile` with `dev`, `test`, `lint`, `docker-build` targets
- [x] `.gitignore` and `README.md`
- [x] GitHub Actions CI: lint + test on push

### Phase 1 — MVP Core  _(~1.5 weeks)_
_Goal: End-to-end flow: user completes interview → gameplan is generated and displayed._
- [x] Multi-step interview form (interview questions based on `project.agent.md`, now removed — superseded by the app itself)
- [x] Pydantic model for `ProjectInput`
- [x] `GameplanGenerator` class: builds markdown from `ProjectInput`
- [x] Tech-stack recommender: maps platform + language preference → stack table
- [x] Gameplan viewer page (rendered Markdown → HTML)
- [x] Download gameplan as `.md` file
- [x] Unit tests for `GameplanGenerator`

### Phase 2 — Persistence & Polish  _(~1 week)_
_Goal: Users can save, list, and reload their gameplans._
- [x] SQLite DB schema: `Project`, `Gameplan` tables (via SQLModel)
- [x] Save gameplan to DB on generation
- [x] Gameplans list page
- [x] Load & edit existing gameplan
- [x] Delete gameplan (with confirmation)
- [x] Form validation with clear error messages
- [x] Responsive CSS (mobile-friendly)

### Phase 3 — Launch Prep  _(~3 days)_
_Goal: Production-ready, tested, documented, containerised._
- [x] Security review (OWASP checklist — see §5)
- [x] Dockerfile + `docker-compose.yml`
- [x] Deployment runbook (`plans/deploy/planner-agent-production.md`)
- [x] Performance baseline (< 200 ms p99 for gameplan generation)
- [x] User-facing `README.md` with screenshots
- [x] `CHANGELOG.md` v1.0.0 entry

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
| 1 | Authentication needed? (multi-user vs single-user) | High | Deferred to v2 — add before any public deployment |
| 2 | Markdown rendering library: `mistune` vs `markdown2` | Low | Resolved: `mistune` v3 with `bleach` sanitisation |
| 3 | SQLite concurrency if deployed with multiple workers | Med | Resolved: single Uvicorn worker in v1; PostgreSQL planned for v2 |
| 4 | XSS risk in rendered Markdown output | High | Resolved: `bleach.clean()` strips disallowed tags and attributes |

---

## 6. Definition of Done (v1)

- [x] All Phase 1 & 2 acceptance criteria met
- [x] `pytest` suite passes with ≥ 80% coverage (current: 90%, 44/44 tests)
- [x] No P0 or P1 findings from `code-review.agent.md`
- [x] Runs cleanly inside Docker container
- [x] Deployment runbook exists at `plans/deploy/planner-agent-production.md`
- [x] README includes setup instructions and a screenshot placeholder

**v1.0.0 is shipped. ✅**

---

## 7. File Structure (target)

```
planner-agent/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app factory
│   ├── config.py             # Settings (env vars)
│   ├── generator.py          # GameplanGenerator + StackRecommender + render_md
│   ├── models/
│   │   ├── __init__.py
│   │   └── project.py        # Pydantic + SQLModel models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── planner.py        # /interview, /generate, /gameplan/{id}
│   │   ├── auth.py           # /register, /login, /logout
│   │   └── health.py         # GET /health
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── interview.html
│   │   ├── gameplan.html
│   │   ├── gameplans.html
│   │   ├── login.html
│   │   └── register.html
│   └── static/
│       └── style.css
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_generator.py
│   └── test_routes.py
├── agents/
│   ├── code-review.agent.md  # VS Code Copilot: code-review workflow
│   └── devops.agent.md       # VS Code Copilot: infra / ops tasks
├── plans/
│   ├── planner-agent.md      # This file — project roadmap
│   └── deploy/
│       └── planner-agent-production.md  # Deployment runbook
├── .github/
│   └── workflows/
│       └── ci.yml
├── entrypoint.sh
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── CHANGELOG.md
├── README.md
├── requirements.txt
└── requirements-dev.txt
```

---

## 8. v2 Roadmap (post-v1)

Items deferred from v1, ordered by impact.

### Phase 4 — Multi-user & Auth  _(complete)_ ✅
_Goal: Make the app safely shareable and publicly deployable._

- [x] `User` model with bcrypt-hashed password
- [x] `user_id` FK on `GameplanRecord`; all queries filtered by owner
- [x] Signed session cookie (`itsdangerous` TimestampSigner, 7-day)
- [x] CSRF double-submit cookie protection on all POST routes
- [x] `/register`, `/login`, `/logout` routes with validation
- [x] Conditional nav (guest vs. logged-in), username display, sign-out form
- [x] Auth CSS (`.auth-card`, `.nav-username`, `.btn-nav-logout`)
- [x] Full test suite updated (44/44 passing, auth tests in `test_auth.py`)
- [x] CHANGELOG v0.2.0 entry

### Phase 5 — Scale & Observability  _(candidate)_
_Goal: Production-grade reliability for multi-user load._

| # | Feature | Priority | Notes |
|---|---------|----------|-------|
| 1 | Swap SQLite → PostgreSQL | P1 | Unblocks multi-worker Uvicorn; use `asyncpg` + Alembic migrations |
| 2 | Structured logging | P1 | `structlog` or `loguru`; emit JSON logs for log aggregation |
| 3 | Metrics + uptime alerting | P2 | Prometheus `/metrics` endpoint; alert on error rate |
| 4 | Async DB session | P2 | Switch to `AsyncSession` for full async path |

### Phase 6 — UX & Features  _(candidate)_
_Goal: Richer output and better user experience._

| # | Feature | Priority | Notes |
|---|---------|----------|-------|
| 1 | Export as PDF | P2 | `weasyprint` or headless Chrome |
| 2 | Gameplan templates / presets | P2 | Pre-fill the form for common project types |
| 3 | AI-assisted description improvement | P3 | Optional LLM call to enrich the problem statement |
| 4 | Dark-/light-mode toggle | P3 | CSS `prefers-color-scheme` + JS toggle |
| 5 | Shareable public link per gameplan | P3 | UUID slug + read-only view, no auth required |
