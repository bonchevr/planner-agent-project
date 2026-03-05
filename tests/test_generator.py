import pytest
from app.models.project import ProjectInput
from app.generator import GameplanGenerator, StackRecommender


@pytest.fixture
def web_project() -> ProjectInput:
    return ProjectInput(
        project_name="My Web App",
        problem_statement="Users need a better way to track tasks.",
        core_features="Task list\nDue dates\nEmail reminders",
        target_platform="Web app (frontend + backend)",
        preferred_language="Python",
        team_size="solo",
        timeline="6 weeks",
        constraints="",
    )


# ── StackRecommender ────────────────────────────────────────────────────

class TestStackRecommender:
    def test_web_platform_returns_fastapi(self, web_project):
        stack = StackRecommender.recommend(web_project)
        assert "FastAPI" in stack.get("Framework", "")

    def test_cli_platform_returns_typer(self):
        project = ProjectInput(
            project_name="My CLI",
            problem_statement="Automate deploys.",
            core_features="Deploy\nRollback",
            target_platform="CLI tool",
        )
        stack = StackRecommender.recommend(project)
        assert "Typer" in stack.get("Framework", "")

    def test_preferred_language_overrides_stack(self, web_project):
        web_project.preferred_language = "Go"
        stack = StackRecommender.recommend(web_project)
        assert stack["Language"] == "Go"

    def test_unknown_platform_falls_back_to_web(self):
        project = ProjectInput(
            project_name="X",
            problem_statement="Y",
            core_features="Z",
            target_platform="something-unknown",
        )
        stack = StackRecommender.recommend(project)
        assert "FastAPI" in stack.get("Framework", "")


# ── GameplanGenerator ───────────────────────────────────────────────────

class TestGameplanGenerator:
    def test_output_contains_project_name(self, web_project):
        stack = StackRecommender.recommend(web_project)
        md = GameplanGenerator.generate(web_project, stack)
        assert "My Web App" in md

    def test_output_contains_features(self, web_project):
        stack = StackRecommender.recommend(web_project)
        md = GameplanGenerator.generate(web_project, stack)
        assert "Task list" in md
        assert "Due dates" in md

    def test_output_contains_phases(self, web_project):
        stack = StackRecommender.recommend(web_project)
        md = GameplanGenerator.generate(web_project, stack)
        for phase in ("Phase 0", "Phase 1", "Phase 2", "Phase 3"):
            assert phase in md

    def test_output_contains_stack_table(self, web_project):
        stack = StackRecommender.recommend(web_project)
        md = GameplanGenerator.generate(web_project, stack)
        for layer in stack:
            assert layer in md


# ── ProjectInput validation ─────────────────────────────────────────────

class TestProjectInput:
    def test_slug_is_lowercase_hyphenated(self):
        p = ProjectInput(
            project_name="My Cool Project",
            problem_statement="x",
            core_features="y",
            target_platform="web",
        )
        assert p.slug == "my-cool-project"

    def test_empty_required_field_raises(self):
        with pytest.raises(Exception):
            ProjectInput(
                project_name="",
                problem_statement="x",
                core_features="y",
                target_platform="web",
            )
