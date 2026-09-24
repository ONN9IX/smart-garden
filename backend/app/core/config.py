"""Application configuration.

Purpose: one environment-backed source for DB, session and CORS settings.
Security: staging/production must provide a non-placeholder SECRET_KEY.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "staging", "production"] = "development"
    database_url: str
    secret_key: str
    auth_session_ttl_seconds: int = 3600
    cors_origins: str = "http://localhost:3000"

    @field_validator("database_url")
    @classmethod
    def require_postgresql(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use PostgreSQL with psycopg")
        return value

    @field_validator("auth_session_ttl_seconds")
    @classmethod
    def positive_ttl(cls, value: int) -> int:
        if value < 60:
            raise ValueError("AUTH_SESSION_TTL_SECONDS must be >= 60")
        return value

    @model_validator(mode="after")
    def validate_shared_environment(self):
        if self.app_env in {"staging", "production"} and (
            self.secret_key == "CHANGE_ME_LOCAL" or len(self.secret_key) < 32
        ):
            raise ValueError("Shared environments require a strong SECRET_KEY")
        if "*" in self.allowed_origins:
            raise ValueError("Wildcard CORS origin is incompatible with cookies")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def secure_cookie(self) -> bool:
        return self.app_env in {"staging", "production"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
