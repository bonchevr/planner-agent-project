from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./data/planner.db"
    secret_key: str = "change-me-before-deploying"
    base_url: str = "http://localhost:8000"

    # SMTP — set via environment variables / fly secrets
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""   # e.g. "Planner Agent <noreply@yourdomain.com>"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("database_url")
    @classmethod
    def normalise_postgres_scheme(cls, v: str) -> str:
        # `fly postgres attach` exports DATABASE_URL with the "postgres://" scheme.
        # SQLAlchemy 2.x requires "postgresql://".
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v


settings = Settings()
