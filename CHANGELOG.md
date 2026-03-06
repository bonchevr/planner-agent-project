# Changelog

All notable changes to **Planner Agent** are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.4.0] — 2026-03-06

### Added
- **Shareable public links** — owners can generate a UUID4 share token for any gameplan via the "Create share link" button. The public URL (`/share/{uuid}`) is accessible without authentication and renders a read-only view with rendered Markdown, meta tags, download-as-.md, and copy-to-clipboard. Sharing is off by default; the owner can revoke the link at any time.
- `GET /share/{share_token}` — public read-only gameplan view (`shared_gameplan.html`).
- `GET /share/{share_token}/download` — public .md download (no auth required).
- `POST /gameplan/{id}/share` — generates UUID4 token (idempotent: subsequent calls keep the same token).
- `POST /gameplan/{id}/revoke` — clears share token, restoring private-only access.
- `share_token` column on `GameplanRecord` (nullable `VARCHAR`, unique index).
- Alembic migration `002_add_share_token`.
- `shared_gameplan.html` template with "Made with Planner Agent" footer.
- `.share-box`, `.share-url-row`, `.share-label`, `.btn-sm`, `.shared-footer` CSS.
- 6 new tests: unknown token 404, share creates link, public view accessible, public download, revoke removes access, share is idempotent.

### Changed
- `gameplan.html` — added share/revoke UI below the download bar.
- `base.html` — updated footer version to v0.3.0.
- Test suite: **61 tests** (was 55).

---

## [0.3.0] — 2026-03-06

### Added
- **PostgreSQL support** — `psycopg2-binary` added; `DATABASE_URL` in `docker-compose.yml` now points to a bundled `postgres:16-alpine` service.
- **Alembic migrations** — `alembic/` directory with `env.py`, `script.py.mako`, and an initial migration (`001_initial_schema`) that creates the `user` and `gameplanrecord` tables in the correct schema. Migration runs automatically on container start via `entrypoint.sh`.
- **Multi-worker Uvicorn** — container now starts 4 workers (was 1); safe because PostgreSQL handles concurrent connections.
- **Structured logging (`loguru`)** — `app/logging_config.py` wires loguru as the single log pipeline. Development: colourised output; production: JSON to stdout for log aggregators. All stdlib logging (uvicorn, SQLAlchemy) is intercepted and forwarded.
- **Prometheus metrics** — `GET /metrics` endpoint (Prometheus text format, excluded from Swagger UI) exposes `http_requests_total` (counter, labelled by method/path/status) and `http_request_duration_seconds` (histogram) tracked in `SecurityHeadersMiddleware`.
- `prometheus-client==0.24.1` added to `requirements.txt`.
- `alembic==1.18.4` and `Mako` added to `requirements.txt`.
- `loguru==0.7.3` added to `requirements.txt`.
- `psycopg2-binary==2.9.11` added to `requirements.txt`.
- `BASE_URL` added to `app/config.py` and `.env.example`.

### Changed
- `docker-compose.yml` — replaced SQLite named volume with a `postgres:16-alpine` service (`postgres-data` volume). App service gains `depends_on: db: condition: service_healthy` to wait for DB readiness.
- `Dockerfile` — copies `alembic/` and `alembic.ini` into the image.
- `entrypoint.sh` — runs `alembic upgrade head` before starting uvicorn; workers increased from 1 → 4.
- `app/db.py` — `connect_args` is now conditional: `{"check_same_thread": False}` for SQLite only (PostgreSQL rejects this argument).
- `app/routes/auth.py` — replaced stdlib `logging.getLogger` with `from loguru import logger`.
- `app/routes/health.py` — added `/metrics` endpoint.
- Test suite: **55 tests** (was 54), `test_metrics_returns_prometheus_text` added.

---

## [0.2.1] — 2026-03-06

### Added
- **Forgot / reset password** — `GET/POST /forgot-password` and `GET/POST /reset-password` routes. Reset token is a 1-hour `URLSafeTimedSerializer` JWT that embeds the first 10 chars of the current password hash (token self-invalidates after password change). Development mode: reset link displayed on screen; production: logged only. Templates: `forgot_password.html`, `reset_password.html`; login page shows success banner on redirect.
- 10 new tests covering the full reset flow (no username enumeration, token verify, success redirect, banner display).

### Fixed
- **CSRF cookie delivery** — FastAPI does not merge cookies set on an injected `Response` parameter into a returned `TemplateResponse`. All GET handlers now build the `TemplateResponse` first, then call `set_csrf_cookie(resp, token)` on the actual returned object. The injected `Response` dependency was removed from all affected routes.
- **Docker schema migration** — existing Docker named volume contained an old SQLite DB missing the `user_id` column. Applied `ALTER TABLE gameplanrecord ADD COLUMN user_id INTEGER REFERENCES user(id)` and created the missing index to unblock logins without data loss.

---

## [0.2.0] — 2026-03-07

### Added
- **User accounts** — `/register` and `/login` routes with username + bcrypt-hashed password. Users can sign out via the nav logout form.
- **`User` SQLModel table** — `id`, `username` (unique, indexed), `hashed_password`, `created_at`.
- **Per-user gameplan ownership** — `user_id` FK on `GameplanRecord`; all list/view/edit/delete routes filter by the authenticated owner.
- **Signed session cookie** — `itsdangerous` `TimestampSigner`; 7-day max-age, `httponly`, `SameSite=Lax`, `Secure` in production.
- **CSRF double-submit protection** — all mutating POST routes (`/generate`, `/edit`, `/delete`, `/logout`, `/register`, `/login`) validate a signed CSRF token from both cookie and form field.
- **Ownership enforcement** — `_assert_owner()` raises HTTP 403 if a user attempts to access another user's gameplan.
- **Auth CSS** — `.auth-card`, `.nav-username`, `.btn-nav-logout`, `.btn-nav` styles added to `style.css`.
- **Conditional navigation** — base template shows guest links (Sign in / Get started) or authenticated links (My Plans / New Plan / username / Sign out).
- **`app/auth.py`** — all auth utilities (hash, verify, session cookie, CSRF, FastAPI deps).
- **`app/routes/auth.py`** — register, login, logout routes.
- **`tests/test_auth.py`** — 16 auth tests (register, login, logout, CSRF rejection, ownership).

### Changed
- `app/routes/planner.py` — all protected routes now require `require_user`; all POST routes require `csrf_protect`; CSRF token injected into GET responses.
- `app/templates/base.html` — conditional nav; version footer → v0.2.0.
- `app/templates/interview.html`, `gameplans.html`, `gameplan.html` — CSRF hidden fields added to all forms.
- `requirements.txt` — replaced `passlib[bcrypt]` with direct `bcrypt==5.0.0` dependency.
- Test suite expanded: **44 tests** (was 28), all passing at ≥ 90% coverage.

---

## [1.0.0] — 2026-03-06

### Added
- **Guided project interview** — multi-field form (project name, problem, features, platform, language, team size, timeline, constraints).
- **`GameplanGenerator`** — produces a structured Markdown gameplan with phases, milestones, stack table, and definition of done.
- **`StackRecommender`** — rule-based tech-stack recommendation (web, API, CLI, mobile, desktop) with language override.
- **Gameplan viewer** — renders the stored Markdown to sanitised HTML via `mistune` + `bleach`, with copy-to-clipboard and `.md` download.
- **SQLite persistence** — gameplans stored via SQLModel; `GameplanRecord` table auto-created on startup.
- **Gameplans list** — browse, view, edit, and delete saved gameplans.
- **Edit & regenerate** — pre-populated interview form lets users update any field and regenerate the gameplan.
- **Form validation** — server-side Pydantic validation with inline error display.
- **Security headers middleware** — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` on every response.
- **Hardened Docker image** — non-root `appuser`, named volume for SQLite data.
- **`GET /health`** — JSON health-check endpoint.
- **`GET /docs`** — Swagger UI (FastAPI built-in).
- **Makefile** — `dev`, `test`, `lint`, `format`, `docker-build`, `docker-run`, `compose-up`, `compose-down` targets.
- **GitHub Actions CI** — lint (`ruff`) + test (`pytest`) on every push.
- **Deployment runbook** — `plans/deploy/planner-agent-production.md` with OWASP checklist, backup procedure, and rollback steps.

### Changed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Security
- Markdown output sanitised with `bleach` (strips `<script>` and other dangerous tags/attributes).
- Jinja2 auto-escaping active on all template variables.
- SQLModel parameterised queries prevent SQL injection.
- Container runs as a non-root user (`appuser`).
- HTTP security headers added to every response.

---

[1.0.0]: https://github.com/<your-org>/planner_agent_project/releases/tag/v1.0.0
