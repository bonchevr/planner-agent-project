from __future__ import annotations

import math
import re
from datetime import date
from typing import Optional

import bleach
import mistune

from app.models.project import ProjectInput

# ---------------------------------------------------------------------------
# Markdown renderer (for the gameplan viewer)
# ---------------------------------------------------------------------------

_ALLOWED_TAGS: frozenset[str] = frozenset({
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "ul", "ol", "li", "blockquote", "pre", "code",
    "strong", "em", "a", "hr", "br",
    "table", "thead", "tbody", "tr", "th", "td",
    "input",  # task-list checkboxes
})
_ALLOWED_ATTRS: dict[str, list[str]] = {
    "a": ["href", "title"],
    "td": ["align"],
    "th": ["align"],
    "input": ["type", "checked", "disabled"],  # checkbox only
}
_md_renderer = mistune.create_markdown(plugins=["table"])


def render_md(text: str) -> str:
    """Render Markdown to sanitised HTML (safe to inject with |safe in templates)."""
    # Normalise legacy &nbsp; separators stored in older DB records so they
    # don't get double-escaped by bleach and display as literal text.
    text = text.replace("&nbsp;", "\u00a0")
    # Rewrite old single-line blockquote metadata into per-field lines.
    # Matches: > **Key:** Value · **Key:** Value ...
    import re as _re
    def _expand_meta(m: _re.Match) -> str:
        parts = _re.split(r"\s*[·\|]\s*", m.group(1))
        return "\n".join(f"> {p.strip()}" for p in parts if p.strip())
    text = _re.sub(
        r"^> (.+(?:\*\*(?:Generated|Status|Team|Timeline):\*\*).+)$",
        _expand_meta,
        text,
        flags=_re.MULTILINE,
    )
    raw_html = _md_renderer(text)
    return bleach.clean(raw_html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True)


# ---------------------------------------------------------------------------
# Stack recommendation — extended with data/ml, game, embedded profiles
# ---------------------------------------------------------------------------

_STACK_MAP: dict[str, dict[str, str]] = {
    "web": {
        "Language": "Python 3.12+",
        "Framework": "FastAPI + Jinja2",
        "UI Layer": "HTMX + Alpine.js",
        "Database": "SQLite (dev) / PostgreSQL (prod)",
        "Auth": "JWT / session cookies",
        "Hosting": "Docker + Fly.io / Railway",
        "CI/CD": "GitHub Actions",
    },
    "api": {
        "Language": "Python 3.12+",
        "Framework": "FastAPI",
        "Database": "PostgreSQL + SQLAlchemy",
        "Auth": "OAuth2 / API keys",
        "Caching": "Redis",
        "Hosting": "Docker + Fly.io / Railway",
        "CI/CD": "GitHub Actions",
    },
    "cli": {
        "Language": "Python 3.12+",
        "Framework": "Typer + Rich",
        "Config": "TOML / dotenv",
        "Testing": "pytest",
        "Distribution": "PyPI / pipx / Homebrew",
        "CI/CD": "GitHub Actions",
    },
    "mobile": {
        "Language": "TypeScript",
        "Framework": "React Native + Expo",
        "State": "Zustand / React Query",
        "Backend": "FastAPI or Supabase",
        "Notifications": "Expo Push / OneSignal",
        "CI/CD": "GitHub Actions + EAS Build",
    },
    "desktop": {
        "Language": "Python 3.12+",
        "Framework": "Tauri (Rust/WebView) or PyQt6",
        "Bundler": "PyInstaller / tauri-bundler",
        "Auto-update": "Tauri updater / Sparkle",
        "CI/CD": "GitHub Actions",
    },
    "data": {
        "Language": "Python 3.12+",
        "Core Libraries": "pandas, numpy, scikit-learn",
        "Notebooks": "JupyterLab",
        "Tracking": "MLflow / DVC",
        "Serving": "FastAPI + Pydantic",
        "CI/CD": "GitHub Actions + DVC pipelines",
    },
    "game": {
        "Language": "GDScript / C# or TypeScript",
        "Engine": "Godot 4 or Phaser 3",
        "Assets": "Aseprite / Blender",
        "Distribution": "itch.io / Steam",
        "CI/CD": "GitHub Actions",
    },
    "embedded": {
        "Language": "C / Rust",
        "SDK": "ESP-IDF / embassy-rs",
        "Protocol": "MQTT / BLE",
        "Toolchain": "PlatformIO / probe-rs",
        "CI/CD": "GitHub Actions + hardware-in-loop tests",
    },
}

_PLATFORM_KEYWORDS: dict[str, list[str]] = {
    "web": ["web", "website", "browser", "frontend", "full-stack", "fullstack", "saas", "webapp"],
    "api": ["api", "rest", "graphql", "backend", "service", "microservice", "webhook"],
    "cli": ["cli", "command", "terminal", "script", "tool", "devtool"],
    "mobile": ["mobile", "ios", "android", "app", "smartphone", "tablet"],
    "desktop": ["desktop", "native", "electron", "gui", "cross-platform", "windows", "macos", "linux app"],
    "data": ["data", "machine learning", "ml", "ai", "analytics", "pipeline", "etl", "notebook", "model"],
    "game": ["game", "2d", "3d", "platformer", "puzzle", "rpg", "godot", "unity", "phaser"],
    "embedded": ["embedded", "iot", "firmware", "microcontroller", "arduino", "esp32", "raspberry"],
}


class StackRecommender:
    @staticmethod
    def recommend(project: ProjectInput) -> dict[str, str]:
        # Scan all free-text fields to get richer context
        all_text = " ".join([
            project.target_platform,
            project.problem_statement,
            project.core_features,
            project.constraints,
            project.preferred_language,
        ]).lower()

        matched_key = "web"
        for key, keywords in _PLATFORM_KEYWORDS.items():
            if any(kw in all_text for kw in keywords):
                matched_key = key
                break
        stack = dict(_STACK_MAP[matched_key])

        # Language + framework override from preferred_language field
        if project.preferred_language.strip():
            lang = project.preferred_language.strip()
            lang_lower = lang.lower()
            stack["Language"] = lang
            if "django" in lang_lower or "django" in all_text:
                stack["Framework"] = "Django + Django REST Framework"
            elif "flask" in lang_lower or "flask" in all_text:
                stack["Framework"] = "Flask + Flask-RESTX"
            elif "go" in lang_lower or lang_lower == "go":
                stack["Language"] = "Go"
                stack["Framework"] = "Chi / Gin"
            elif "rust" in lang_lower:
                stack["Language"] = "Rust"
                stack["Framework"] = "Axum"
            elif any(k in lang_lower for k in ["node", "javascript", "typescript"]):
                stack["Language"] = "TypeScript / Node.js"
                if matched_key in ("web", "api"):
                    stack["Framework"] = "Express.js / Fastify"

        # UI layer overrides for web apps
        if matched_key == "web" and "UI Layer" in stack:
            if "next.js" in all_text or "nextjs" in all_text:
                stack["UI Layer"] = "Next.js (React SSR)"
            elif "react" in all_text:
                stack["UI Layer"] = "React + Vite"
            elif "vue" in all_text:
                stack["UI Layer"] = "Vue 3 + Vite"
            elif "svelte" in all_text:
                stack["UI Layer"] = "SvelteKit"
            elif "angular" in all_text:
                stack["UI Layer"] = "Angular"

        # Database overrides
        if "Database" in stack:
            if "supabase" in all_text:
                stack["Database"] = "Supabase (PostgreSQL)"
            elif "firebase" in all_text or "firestore" in all_text:
                stack["Database"] = "Firestore (Firebase)"
            elif "mongodb" in all_text or "mongo" in all_text:
                stack["Database"] = "MongoDB + Motor (async)"
            elif "mysql" in all_text or "mariadb" in all_text:
                stack["Database"] = "MySQL + SQLAlchemy"
            elif "postgres" in all_text or "postgresql" in all_text:
                stack["Database"] = "PostgreSQL + SQLAlchemy"

        # Hosting overrides
        if "Hosting" in stack:
            if "aws" in all_text or "amazon web" in all_text:
                stack["Hosting"] = "AWS (ECS / Lambda)"
            elif "gcp" in all_text or "google cloud" in all_text:
                stack["Hosting"] = "Google Cloud Run"
            elif "azure" in all_text:
                stack["Hosting"] = "Azure Container Apps"
            elif "digitalocean" in all_text or "digital ocean" in all_text:
                stack["Hosting"] = "DigitalOcean App Platform"
            elif "vercel" in all_text:
                stack["Hosting"] = "Vercel"
            elif "netlify" in all_text:
                stack["Hosting"] = "Netlify"
            elif "heroku" in all_text:
                stack["Hosting"] = "Heroku"

        # CI/CD overrides (only if user explicitly mentioned a different tool)
        if "gitlab" in all_text:
            stack["CI/CD"] = "GitLab CI/CD"
        elif "jenkins" in all_text:
            stack["CI/CD"] = "Jenkins"
        elif "circleci" in all_text:
            stack["CI/CD"] = "CircleCI"
        elif "bitbucket" in all_text:
            stack["CI/CD"] = "Bitbucket Pipelines"
        elif "azure devops" in all_text:
            stack["CI/CD"] = "Azure DevOps Pipelines"

        # Auth overrides
        if "Auth" in stack:
            if "auth0" in all_text:
                stack["Auth"] = "Auth0"
            elif "supabase" in all_text:
                stack["Auth"] = "Supabase Auth"
            elif "firebase" in all_text:
                stack["Auth"] = "Firebase Auth"
            elif "keycloak" in all_text:
                stack["Auth"] = "Keycloak"

        return stack


# ---------------------------------------------------------------------------
# Risk analysis — derive risks from project attributes
# ---------------------------------------------------------------------------

def _build_risks(project: ProjectInput) -> list[tuple[str, str, str]]:
    """Return list of (risk, likelihood, mitigation) tuples."""
    risks: list[tuple[str, str, str]] = []
    features = [f.strip() for f in project.core_features.splitlines() if f.strip()]

    if len(features) > 6:
        risks.append(("Scope creep — too many v1 features", "High",
                       "Cut to the 3 most critical features; defer the rest to v2 backlog"))
    if "solo" in project.team_size.lower():
        risks.append(("Bus-factor of 1 — single contributor", "Medium",
                       "Write thorough docs and keep the repo public or backed up off-site"))
    if not project.timeline.strip():
        risks.append(("Undefined timeline leads to drift", "Medium",
                       "Timebox milestones even if delivery date is flexible"))
    if any(kw in project.target_platform.lower() for kw in ["mobile", "ios", "android"]):
        risks.append(("App store review delays", "Medium",
                       "Submit to TestFlight / Play beta early; build review time into the plan"))
    if any(kw in project.problem_statement.lower() for kw in ["payment", "billing", "stripe", "subscription"]):
        risks.append(("Payment integration complexity", "High",
                       "Use a battle-tested provider (Stripe); never store raw card data"))
    if not project.constraints.strip():
        risks.append(("Unknown constraints discovered late", "Low",
                       "Run a brief constraints workshop / spike in Phase 0"))
    if not risks:
        risks.append(("Unforeseen technical dependency", "Low",
                       "Identify all third-party services and check SLAs before Phase 1"))
    return risks[:5]


# ---------------------------------------------------------------------------
# Timeline estimator — derive rough week estimates from team + features
# ---------------------------------------------------------------------------

def _estimate_weeks(project: ProjectInput) -> dict[str, int]:
    features = [f.strip() for f in project.core_features.splitlines() if f.strip()]
    n = max(1, len(features))
    team_factor = {"solo": 1.0, "2": 0.65, "4": 0.45, "8": 0.35}.get(
        project.team_size.split()[0].lower(), 0.8
    )
    base = math.ceil(n * 0.75 * team_factor)
    return {
        "setup": 1,
        "mvp_core": max(2, base),
        "polish": max(1, math.ceil(base * 0.5)),
        "launch_prep": 1,
    }


# ---------------------------------------------------------------------------
# Gameplan generator — dynamic, project-aware structure
# ---------------------------------------------------------------------------

class GameplanGenerator:
    @staticmethod
    def generate(project: ProjectInput, stack: dict[str, str]) -> str:
        today = date.today().strftime("%-d %B %Y")
        features = [f.strip() for f in project.core_features.splitlines() if f.strip()]
        feature_list = "\n".join(f"- {f}" for f in features) if features else "- _(not specified)_"

        # Tech stack table
        stack_rows = "\n".join(
            f"| {layer:<22} | {choice} |" for layer, choice in stack.items()
        )
        stack_table = (
            f"| {'Layer':<22} | Choice |\n"
            f"|{'-'*24}|--------|\n"
            f"{stack_rows}"
        )

        # Architecture notes — context-aware from platform + detected features
        platform_lower = project.target_platform.lower()
        all_text_lower = " ".join([
            project.target_platform,
            project.problem_statement,
            project.core_features,
            project.constraints,
        ]).lower()

        if any(k in platform_lower for k in ["web", "saas", "fullstack"]):
            arch_notes = [
                "Server-rendered HTML with progressive enhancement (HTMX/Alpine) keeps JS bundles lean",
                "REST endpoints for any rich client interactions — define OpenAPI contracts early",
                "Relational DB with migrations from day one (Alembic / Flyway) — never alter schema by hand in production",
                "Row-level security or explicit `WHERE user_id = ?` scoping on every authenticated query",
            ]
        elif any(k in platform_lower for k in ["api", "backend", "service"]):
            arch_notes = [
                "Async request handling from the start (FastAPI / Go / Node) — avoid retrofitting later",
                "OpenAPI spec auto-generated and versioned (`/v1/`) — treat it as a contract; breaking changes require a new version",
                "Rate limiting and authentication middleware applied at the router layer, not inside handlers",
                "Idempotency keys on any state-mutating endpoint; make retries safe by design",
            ]
        elif any(k in platform_lower for k in ["mobile", "ios", "android"]):
            arch_notes = [
                "Offline-first data model — assume no network; sync on reconnect via a conflict-free strategy",
                "Optimistic UI updates to mask network latency; roll back gracefully on server errors",
                "Deep-link routing and universal links wired up from day one (not retrofitted)",
                "Background sync and push notifications decoupled from UI state; handled in a dedicated service layer",
            ]
        elif any(k in platform_lower for k in ["data", "ml", "ai"]):
            arch_notes = [
                "Reproducible pipelines via DVC or Makefile targets — anyone can re-run training from scratch",
                "Strict separation of training, evaluation, and serving concerns to prevent data leakage",
                "Version datasets and model artefacts alongside code (DVC / MLflow)",
                "Feature store or shared preprocessing pipeline prevents training/serving skew from day one",
            ]
        else:
            arch_notes = [
                "Keep the boundary between core business logic and I/O (DB, network, filesystem) thin and explicit",
                "Prefer explicit configuration over hard-coded values — externalise all environment-specific settings",
                "Write the README before writing the first line of code; clarify the dev setup and deploy story",
                "Centralise logging and structured error reporting from the first commit",
            ]

        # Append project-specific notes based on detected features
        if any(k in all_text_lower for k in ["auth", "login", "user", "register", "jwt", "oauth", "session", "signup"]):
            arch_notes.append("Auth flows isolated in their own module — never inline credential validation in business logic")
        if any(k in all_text_lower for k in ["payment", "billing", "stripe", "subscription", "checkout", "invoice"]):
            arch_notes.append("Payment processing sandboxed behind an interface — swap providers (Stripe → Paddle etc.) without touching business code; never store raw card data")
        if any(k in all_text_lower for k in ["real-time", "realtime", "websocket", "socket.io", "live update", "push notification"]):
            arch_notes.append("Real-time layer (WebSockets / SSE) separated from the REST API; fan-out handled via pub/sub or a message broker (Redis Streams / NATS)")
        if any(k in all_text_lower for k in ["upload", "file", "image", "media", "storage", "s3", "blob", "attachment"]):
            arch_notes.append("File storage abstracted behind a `StorageBackend` interface — local ↔ S3-compatible swap without touching callers")
        if any(k in all_text_lower for k in ["cache", "redis", "performance", "speed", "fast", "latency"]):
            arch_notes.append("Cache layer introduced at the service boundary (not inside repositories) to keep cache-invalidation logic co-located with the data it protects")
        if any(k in all_text_lower for k in ["search", "elasticsearch", "algolia", "full-text", "fulltext"]):
            arch_notes.append("Search index built as a read-projection of the primary DB — kept eventually consistent via background jobs, not synchronous writes")

        arch_note = "\n".join(f"- {note}" for note in arch_notes)

        # Risk table
        risks = _build_risks(project)
        risk_rows = "\n".join(
            f"| {r[0]} | {r[1]} | {r[2]} |" for r in risks
        )
        risk_table = (
            "| Risk | Likelihood | Mitigation |\n"
            "|------|------------|------------|\n"
            f"{risk_rows}"
        )

        # Week estimates
        weeks = _estimate_weeks(project)
        total = sum(weeks.values())
        timeline_str = project.timeline.strip() or f"~{total} weeks (estimated)"

        # Feature tasks for MVP Core phase
        feature_tasks = "\n".join(
            f"- [ ] Implement: **{f}**" for f in features
        ) if features else "- [ ] Implement core features per spec"

        # Acceptance criteria (one per feature, max 5)
        ac_items = "\n".join(
            f"- [ ] `{f}` — works end-to-end on staging, edge cases handled"
            for f in features[:5]
        ) if features else "- [ ] Core user journey works end-to-end"

        constraints_note = project.constraints.strip() or "None identified yet"
        team_note = project.team_size or "Solo"

        return f"""# {project.project_name}

> **Generated:** {today}
> **Status:** Planning
> **Team:** {team_note}
> **Timeline:** {timeline_str}

---

## 1. Problem & Scope

**Problem statement:** {project.problem_statement}

**Platform:** {project.target_platform}

**Constraints:** {constraints_note}

### Core features — v1 scope

{feature_list}

> **Scope rule:** anything not in this list is explicitly out of scope for v1. Put deferred ideas in a separate "v2 backlog" section at the bottom.

---

## 2. Recommended Tech Stack

{stack_table}

### Architecture notes

{arch_note}

---

## 3. Milestones

### Phase 0 — Setup & Foundations _(~{weeks['setup']} week)_

**Goal:** every contributor can clone, run, and push in under 10 minutes.

- [ ] Repository created with `README.md`, `.gitignore`, and branch protection on `main`
- [ ] Local dev environment documented (`make dev` or equivalent one-liner)
- [ ] CI pipeline: lint + unit tests on every push and pull request
- [ ] Architecture Decision Record (ADR) stub committed
- [ ] Environments defined: `local`, `staging`, `production`
- [ ] Initial database schema / data model designed and reviewed

### Phase 1 — MVP Core _(~{weeks['mvp_core']} weeks)_

**Goal:** end-to-end happy path running locally for all v1 features.

{feature_tasks}
- [ ] Authentication / authorisation layer in place
- [ ] API contracts defined and documented (OpenAPI / README)
- [ ] Basic error handling and input validation

### Phase 2 — Polish & Hardening _(~{weeks['polish']} week)_

**Goal:** edge cases handled, UX polished, performance baseline established.

- [ ] All form inputs validated with helpful error messages
- [ ] Responsive / accessible UI (ARIA, keyboard nav, colour contrast ≥ 4.5:1)
- [ ] Integration and end-to-end tests added
- [ ] Performance profiled — no query > 200 ms under expected load
- [ ] Logging and error tracking wired up (Sentry / Loguru)

### Phase 3 — Launch Prep _(~{weeks['launch_prep']} week)_

**Goal:** production-ready, containerised, publicly documented.

- [ ] Security review against OWASP Top 10 checklist
- [ ] Dockerfile + `docker-compose.yml` tested from scratch on a clean machine
- [ ] Deployment runbook written (step-by-step from zero to live)
- [ ] Monitoring and alerting configured (uptime, error rate, latency)
- [ ] `README.md` updated with full setup and usage instructions
- [ ] Change log entry for v1.0

---

## 4. Risk Register

{risk_table}

---

## 5. Definition of Done — v1

{ac_items}
- [ ] Test suite passing with ≥ 80 % line coverage
- [ ] Zero high-severity security findings
- [ ] Deployed and accessible in the target environment
- [ ] Core user journey demoed to at least one real user

---

## 6. v2 Backlog _(deferred)_

> Add ideas here that didn't make the v1 cut. Evaluate at the v1 retrospective.

- _(add deferred features here)_
"""


# ---------------------------------------------------------------------------
# Progress helper — count checked tasks in markdown
# ---------------------------------------------------------------------------

def calculate_progress_from_md(md: str) -> int:
    """Return 0–100 percentage based on checked vs total task checkboxes."""
    total = len(re.findall(r"- \[[ xX]\]", md))
    if total == 0:
        return 0
    checked = len(re.findall(r"- \[[xX]\]", md))
    return round(checked / total * 100)
