# Planner Agent — Project Gameplan

> Generated: 5 March 2026
> Last updated: 11 March 2026
> Status: v0.5.0 — Phase 8 (Email & UX Polish) Complete ✅ — Live at <https://planner-agent.fly.dev/>

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
| Database     | PostgreSQL 16 (Neon, production) / SQLite (local dev) | SQLModel gives Pydantic + SQLAlchemy in one; Neon provides managed serverless Postgres. |
| Package mgr  | uv                      | Already used in this workspace (`scripts/uv_install.sh`).              |
| CI/CD        | GitHub Actions          | Standard, free for personal projects.                                  |
| Hosting      | Fly.io (live: planner-agent.fly.dev) | Docker-native PaaS, free tier, global edge. |

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
- [x] Deployment runbook (`docs/planner-agent-production.md`)
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
| 6 | GitHub Actions workflow (`fly-deploy.yml`) | Solo | 1 h | ruff lint + pytest + deploy |

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
- [x] Deployment runbook exists at `docs/planner-agent-production.md`
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
│   ├── db.py                 # SQLAlchemy engine + session factory
│   ├── email.py              # SMTP password-reset email (SSL/STARTTLS)
│   ├── generator.py          # GameplanGenerator + StackRecommender + render_md
│   ├── logging_config.py     # loguru structured logging
│   ├── models/
│   │   ├── __init__.py
│   │   └── project.py           # Pydantic + SQLModel models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── planner.py           # /interview, /generate, /gameplan/{id}, /share/{slug}
│   │   ├── auth.py              # /register, /login, /logout, /forgot-password, /reset-password
│   │   └── health.py            # GET /health, GET /metrics
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── interview.html
│   │   ├── gameplan.html
│   │   ├── gameplans.html
│   │   ├── shared_gameplan.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── forgot_password.html
│   │   └── reset_password.html
│   └── static/
│       └── style.css
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_generator.py
│   └── test_routes.py
├── docs/
│   ├── planner-agent.md          # This file — project roadmap
│   ├── planner-agent-production.md  # Deployment runbook
│   ├── Home_page.png
│   ├── New_plan.png
│   ├── Plan_overview.png
│   └── All_plans.png
├── alembic/
│   ├── env.py
│   └── versions/               # 001–004 migration scripts
├── .github/
│   └── workflows/
│       └── fly-deploy.yml      # Push to main: test → Docker Hub + Fly.io
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
- [x] Forgot password / password reset (signed 1-hour token, dev link on screen)
- [x] Full test suite updated (54/54 passing, auth + reset tests in `test_auth.py`)
- [x] CHANGELOG v0.2.0 / v0.2.1 entries

### Phase 5 — Scale & Observability  _(complete)_ ✅
_Goal: Production-grade reliability for multi-user load._

| # | Feature | Priority | Status |
|---|---------|----------|--------|
| 1 | Swap SQLite → PostgreSQL | P1 | ✅ `psycopg2-binary` + `postgres:16-alpine` in Compose; `connect_args` conditional in `db.py` |
| 2 | Alembic migrations | P1 | ✅ `alembic/` setup with `env.py` importing SQLModel metadata; `001_initial_schema` migration; `alembic upgrade head` in `entrypoint.sh` |
| 3 | Multi-worker Uvicorn | P1 | ✅ 4 workers in `entrypoint.sh` (safe with PostgreSQL) |
| 4 | Structured logging | P1 | ✅ `loguru` via `app/logging_config.py`; dev=colourised, prod=JSON; stdlib intercepted |
| 5 | Prometheus metrics | P2 | ✅ `GET /metrics` in `health.py`; `http_requests_total` + `http_request_duration_seconds` in middleware |

### Phase 6 — UX & Features  _(complete)_ ✅
_Goal: Richer output and better user experience._

| # | Feature | Priority | Status |
|---|---------|----------|--------|
| 1 | Export as PDF | P2 | ⏳ candidate |
| 2 | Gameplan templates / presets | P2 | ⏳ candidate |
| 3 | AI-assisted description improvement | P3 | ⏳ candidate |
| 4 | Dark-/light-mode toggle | P3 | ⏳ candidate |
| 5 | Shareable public link per gameplan | P3 | ✅ UUID slug + read-only view + revoke; 6 tests |

### Phase 7 — Production Deployment  _(complete)_ ✅
_Goal: App live on a public URL with CI/CD, PostgreSQL, and resilient startup._

| # | Feature | Priority | Status |
|---|---------|----------|--------|
| 1 | Fly.io deployment (`fly.toml`, `entrypoint.sh`) | P1 | ✅ Deployed at planner-agent.fly.dev, region `lhr` |
| 2 | Migrate from SQLite to PostgreSQL (production) | P1 | ✅ Neon managed serverless Postgres; Alembic migrations on startup |
| 3 | Connection pool resilience | P1 | ✅ `pool_pre_ping=True` + `pool_recycle=300` in `db.py` |
| 4 | Wait-for-DB loop in entrypoint | P1 | ✅ 30-retry loop before Alembic; safe for cold-start |
| 5 | GitHub Actions auto-deploy | P1 | ✅ `.github/workflows/fly-deploy.yml`: test → Docker Hub publish + Fly deploy (parallel) |
| 6 | Docker Hub image publish | P2 | ✅ `bonchevr/planner-agent:latest` + `sha-<commit>` tags |
| 7 | 1 GB VM, 2 workers, auto-stop enabled | P2 | ✅ `fly.toml` — 1 GB shared-cpu-1x; health checks every 30 s |

### Phase 8 — Email & UX Polish  _(complete)_ ✅
_Goal: Password reset via email, improved metadata display, context-aware generator, interactive progress._

| # | Feature | Priority | Status |
|---|---------|----------|--------|
| 1 | Password reset email via Resend SMTP (port 465, SSL) | P1 | ✅ `app/email.py`; sent synchronously in `auth.py` |
| 2 | Context-aware `StackRecommender` (scans all input fields) | P2 | ✅ Detects React, AWS, MongoDB, GitLab, Auth0, etc. |
| 3 | Enriched architecture notes (per-platform + per-feature) | P2 | ✅ 4+ bullets per platform; auth/payments/search addons |
| 4 | Interactive checklist progress sidebar | P2 | ✅ JS syncs checked tasks → progress counter in real-time |
| 5 | Metadata multi-line blockquote format | P3 | ✅ Generator + `render_md()` backcompat regex for old records |
| 6 | Nav & username contrast fix | P3 | ✅ `var(--text)` throughout; username badge styling |
