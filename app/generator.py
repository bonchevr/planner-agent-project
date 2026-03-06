from __future__ import annotations

from datetime import date

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
# Stack recommendation
# ---------------------------------------------------------------------------

_STACK_MAP: dict[str, dict[str, str]] = {
    "web": {
        "Language": "Python 3.11+",
        "Framework": "FastAPI + Jinja2",
        "UI layer": "HTMX",
        "Database": "SQLite (dev) / PostgreSQL (prod)",
        "Hosting": "Docker + Fly.io",
        "CI/CD": "GitHub Actions",
    },
    "api": {
        "Language": "Python 3.11+",
        "Framework": "FastAPI",
        "Database": "PostgreSQL",
        "Hosting": "Docker + Fly.io",
        "CI/CD": "GitHub Actions",
    },
    "cli": {
        "Language": "Python 3.11+",
        "Framework": "Typer",
        "Distribution": "PyPI / pipx",
        "CI/CD": "GitHub Actions",
    },
    "mobile": {
        "Language": "TypeScript",
        "Framework": "React Native + Expo",
        "Backend": "FastAPI (optional)",
        "CI/CD": "GitHub Actions + EAS Build",
    },
    "desktop": {
        "Language": "Python 3.11+",
        "Framework": "Tkinter / PyQt6",
        "Distribution": "PyInstaller",
        "CI/CD": "GitHub Actions",
    },
}

_PLATFORM_KEYWORDS = {
    "web": ["web", "website", "browser", "frontend", "full-stack", "fullstack"],
    "api": ["api", "rest", "graphql", "backend", "service", "microservice"],
    "cli": ["cli", "command", "terminal", "script", "tool"],
    "mobile": ["mobile", "ios", "android", "app"],
    "desktop": ["desktop", "native", "electron", "gui"],
}


class StackRecommender:
    @staticmethod
    def recommend(project: ProjectInput) -> dict[str, str]:
        platform_lower = project.target_platform.lower()
        for key, keywords in _PLATFORM_KEYWORDS.items():
            if any(kw in platform_lower for kw in keywords):
                stack = dict(_STACK_MAP[key])
                # Override language if user expressed a preference
                if project.preferred_language.strip():
                    stack["Language"] = project.preferred_language.strip()
                return stack
        # Fallback to web stack
        return dict(_STACK_MAP["web"])


# ---------------------------------------------------------------------------
# Gameplan generator
# ---------------------------------------------------------------------------

class GameplanGenerator:
    @staticmethod
    def generate(project: ProjectInput, stack: dict[str, str]) -> str:
        today = date.today().strftime("%-d %B %Y")
        features = [f.strip() for f in project.core_features.splitlines() if f.strip()]
        feature_list = "\n".join(f"- {f}" for f in features) if features else "- _(not specified)_"

        stack_table_rows = "\n".join(
            f"| {layer:<14} | {choice:<30} |" for layer, choice in stack.items()
        )
        stack_table = (
            f"| {'Layer':<14} | {'Choice':<30} |\n"
            f"|{'-'*16}|{'-'*32}|\n"
            f"{stack_table_rows}"
        )

        timeline_note = f"Target timeline: {project.timeline}" if project.timeline else "Timeline: not specified"
        constraints_note = project.constraints.strip() or "None specified"
        team_note = project.team_size.strip() or "Solo"

        return f"""# {project.project_name} — Project Gameplan

> Generated: {today}
> Status: Draft

---

## 1. Overview

**Problem:** {project.problem_statement}

**Core features (v1):**
{feature_list}

**Platform:** {project.target_platform}
**Team:** {team_note}
**{timeline_note}**
**Constraints:** {constraints_note}

---

## 2. Recommended Tech Stack

{stack_table}

---

## 3. Milestones

### Phase 0 — Setup & Foundations _(~1 week)_
- [ ] Repository initialised with README, .gitignore, and branching strategy
- [ ] Local dev environment documented and reproducible
- [ ] CI pipeline: lint + test on every push

### Phase 1 — MVP Core _(~2 weeks)_
_Goal: end-to-end happy path working locally_
{chr(10).join(f"- [ ] Implement: {f}" for f in features) if features else "- [ ] Implement core features"}

### Phase 2 — MVP Polish _(~1 week)_
_Goal: edge cases handled, UI polished, feedback incorporated_
- [ ] Input validation and error messages
- [ ] Responsive / accessible UI
- [ ] Integration tests

### Phase 3 — Launch Prep _(~3 days)_
_Goal: production-ready, containerised, documented_
- [ ] Security review (OWASP checklist)
- [ ] Dockerfile + deployment runbook
- [ ] Performance baseline
- [ ] User-facing documentation

---

## 4. Definition of Done (v1)

- [ ] All Phase 1 & 2 acceptance criteria met
- [ ] Test suite passing with ≥ 80% coverage
- [ ] No critical security findings
- [ ] Deployed and accessible in target environment
- [ ] README updated with setup and usage instructions
"""
