# Changelog

All notable changes to **Planner Agent** are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
