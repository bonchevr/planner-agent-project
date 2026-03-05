from pydantic import BaseModel, field_validator


class ProjectInput(BaseModel):
    project_name: str
    problem_statement: str
    core_features: str
    target_platform: str
    preferred_language: str = ""
    team_size: str = "solo"
    timeline: str = ""
    constraints: str = ""

    @field_validator("project_name", "problem_statement", "core_features", "target_platform")
    @classmethod
    def must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field is required.")
        return value.strip()

    @property
    def slug(self) -> str:
        import re
        slug = self.project_name.lower().strip()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        return slug.strip("-")
