from __future__ import annotations

import math
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
})
_ALLOWED_ATTRS: dict[str, list[str]] = {
    "a": ["href", "title"],
    "td": ["align"],
    "th": ["align"],
}
_md_renderer = mistune.create_markdown(plugins=["table"])


def render_md(text: str) -> str:
    """Render Markdown to sanitised HTML (safe to inject with |safe in templates)."""
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
        platform_lower = project.target_platform.lower()
        matched_key = "web"
        for key, keywords in _PLATFORM_KEYWORDS.items():
            if any(kw in platform_lower for kw in keywords):
                matched_key = key
                break
        stack = dict(_STACK_MAP[matched_key])
        if project.preferred_language.strip():
            stack["Language"] = project.preferred_language.strip()
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

        # Architecture notes based on platform type
        platform_lower = project.target_platform.lower()
        if any(k in platform_lower for k in ["web", "saas", "fullstack"]):
            arch_note = (
                "- Server-rendered HTML with progressive enhancement (HTMX/Alpine) for minimal JS bundle\n"
                "- REST endpoints for any rich client interactions\n"
                "- Relational DB with migrations from day one (Alembic / Flyway)"
            )
        elif any(k in platform_lower for k in ["api", "backend", "service"]):
            arch_note = (
                "- Async request handling from the start (FastAPI / Go / Node)\n"
                "- OpenAPI spec auto-generated — keep it accurate and versioned\n"
                "- Rate limiting and auth middleware in the router layer"
            )
        elif any(k in platform_lower for k in ["mobile", "ios", "android"]):
            arch_note = (
                "- Offline-first data model with sync on reconnect\n"
                "- Optimistic UI updates to mask network latency\n"
                "- Deep-link routing wired up from day one"
            )
        elif any(k in platform_lower for k in ["data", "ml", "ai"]):
            arch_note = (
                "- Reproducible pipelines via DVC or Makefile targets\n"
                "- Separate training, evaluation, and serving concerns\n"
                "- Version datasets alongside model artefacts"
            )
        else:
            arch_note = (
                "- Keep the module boundary between core logic and I/O thin\n"
                "- Prefer configuration over hard-coded values from day one\n"
                "- Write the README before writing the first line of code"
            )

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

> **Generated:** {today} &nbsp;|&nbsp; **Status:** Planning &nbsp;|&nbsp; **Team:** {team_note} &nbsp;|&nbsp; **Timeline:** {timeline_str}

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
