import json
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator
from sqlmodel import Field, SQLModel


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
        slug = self.project_name.lower().strip()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        return slug.strip("-")


class GameplanRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(index=True)
    project_name: str
    problem_statement: str
    core_features: str
    target_platform: str
    preferred_language: str = ""
    team_size: str = "solo"
    timeline: str = ""
    constraints: str = ""
    gameplan_md: str
    stack_json: str  # JSON-encoded dict[str, str]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def stack(self) -> dict[str, str]:
        return json.loads(self.stack_json)

