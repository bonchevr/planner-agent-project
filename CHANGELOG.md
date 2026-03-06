# Changelog

All notable changes to **Planner Agent** are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
