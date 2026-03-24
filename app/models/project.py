import json
import re
from datetime import UTC, datetime
from typing import Optional

from pydantic import BaseModel, field_validator
from sqlmodel import Field, Relationship, SQLModel


# ── User ─────────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, min_length=3, max_length=40)
    email: Optional[str] = Field(default=None, unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)

    gameplans: list["GameplanRecord"] = Relationship(back_populates="owner")


# ── ProjectInput (form validation) ───────────────────────────────────────

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


# ── Project status enum values ────────────────────────────────────────────

PROJECT_STATUSES = ["planning", "in_progress", "on_hold", "completed", "cancelled"]


# ── GameplanRecord ────────────────────────────────────────────────────────

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Status & progress tracking
    status: str = Field(default="planning", index=True)
    progress: int = Field(default=0)  # 0–100
    tags: str = Field(default="")     # comma-separated free-text tags
    notes: str = Field(default="")    # personal notes / journal

    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    owner: Optional[User] = Relationship(back_populates="gameplans")

    # Opt-in public sharing — None means not shared, UUID4 string means shared.
    share_token: Optional[str] = Field(default=None, unique=True, index=True)

    def stack(self) -> dict[str, str]:
        return json.loads(self.stack_json)

    def tags_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def status_label(self) -> str:
        return self.status.replace("_", " ").title()

    @property
    def status_class(self) -> str:
        return f"status-{self.status}"

