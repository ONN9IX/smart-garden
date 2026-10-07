"""Application configuration.

Purpose: one environment-backed source for DB, session and CORS settings.
Security: staging/production must provide a non-placeholder SECRET_KEY.
"""

from functools import lru_cache
from ipaddress import ip_address
from typing import Literal
from unicodedata import category
from urllib.parse import urlsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SHARED_ENVIRONMENTS = {"staging", "production"}
UNSAFE_SECRET_MARKERS = (
    "change_me",
    "changeme",
    "example",
    "placeholder",
    "replace-me",
    "replace_me",
)


def is_unsafe_shared_secret(value: str) -> bool:
    """Reject predictable values without exposing the submitted secret."""

    normalized = value.strip().lower()
    return (
        len(value) < 32
        or len(set(value)) < 4
        or any(marker in normalized for marker in UNSAFE_SECRET_MARKERS)
    )


def is_unsafe_shared_origin(origin: str) -> bool:
    """Identify malformed, localhost, loopback and development bind origins."""

    if any(character.isspace() or category(character) == "Cc" for character in origin):
        return True

    try:
        parsed = urlsplit(origin)
        _ = parsed.port
    except ValueError:
        return True

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return True

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return True

    try:
        address = ip_address(hostname)
    except ValueError:
        return False
    return address.is_loopback or address.is_unspecified


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "staging", "production"] = "development"
    database_url: str
    secret_key: str
    auth_session_ttl_seconds: int = 3600
    cors_origins: str = "http://localhost:3000"
    email_delivery: Literal["disabled", "smtp"] = "disabled"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_tls: bool = True
    public_app_base_url: str | None = None
    activation_ttl_seconds: int = 86400
    reset_ttl_seconds: int = 3600

    @field_validator("database_url")
    @classmethod
    def require_postgresql(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use PostgreSQL with psycopg")
        return value

    @field_validator("auth_session_ttl_seconds", "activation_ttl_seconds", "reset_ttl_seconds")
    @classmethod
    def positive_ttl(cls, value: int) -> int:
        if value < 60:
            raise ValueError("AUTH_SESSION_TTL_SECONDS must be >= 60")
        return value

    @model_validator(mode="after")
    def validate_shared_environment(self):
        if any("*" in origin for origin in self.allowed_origins):
            raise ValueError("Wildcard CORS origin is incompatible with cookies")
        if self.app_env in SHARED_ENVIRONMENTS:
            if is_unsafe_shared_secret(self.secret_key):
                raise ValueError("Shared environments require a strong SECRET_KEY")
            if not self.allowed_origins:
                raise ValueError("Shared environments require explicit CORS_ORIGINS")
            if any(is_unsafe_shared_origin(origin) for origin in self.allowed_origins):
                raise ValueError(
                    "Shared environments require explicit non-development CORS origins"
                )
            if self.email_delivery == "smtp" and not all(
                (self.smtp_host, self.smtp_username, self.smtp_password, self.smtp_from, self.public_app_base_url)
            ):
                raise ValueError("Enabled SMTP delivery requires complete configuration")
        if self.smtp_port < 1 or self.smtp_port > 65535:
            raise ValueError("SMTP_PORT must be valid")
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
