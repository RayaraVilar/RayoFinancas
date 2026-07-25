from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RAYO_",
        extra="ignore",
    )

    app_name: str = "Rayo Finanças API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = Field(
        default="postgresql+asyncpg://rayo:change-me-locally@localhost:5432/rayo",
        min_length=1,
    )
    log_level: str = "INFO"
    secret_key: SecretStr = Field(
        default=SecretStr("local-development-secret-change-before-shared-use"),
    )
    frontend_url: str = "http://localhost:3000"
    public_api_url: str = "http://localhost:8000"
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    pluggy_enabled: bool = False
    pluggy_client_id: str | None = None
    pluggy_client_secret: SecretStr | None = None
    pluggy_webhook_secret: SecretStr | None = None
    pluggy_api_url: str = "https://api.pluggy.ai"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.6-sol"
    redis_url: str = "redis://localhost:6379/0"
    payment_initiation_enabled: bool = False
    payment_kill_switch: bool = True
    payment_provider: str | None = None
    session_cookie_name: str = "rayo_session"
    csrf_cookie_name: str = "rayo_csrf"
    session_ttl_days: int = Field(default=30, ge=1, le=90)
    oauth_flow_ttl_seconds: int = Field(default=600, ge=120, le=900)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_postgres_driver(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @model_validator(mode="after")
    def reject_insecure_production_settings(self) -> Settings:
        if self.environment in {"staging", "production"}:
            if len(self.secret_key.get_secret_value()) < 32:
                raise ValueError("RAYO_SECRET_KEY must contain at least 32 characters.")
            if not self.frontend_url.startswith("https://"):
                raise ValueError("RAYO_FRONTEND_URL must use HTTPS in production.")
            if not self.public_api_url.startswith("https://"):
                raise ValueError("RAYO_PUBLIC_API_URL must use HTTPS outside local environments.")
            if self.google_oauth_configured and not self.google_redirect_uri.startswith("https://"):
                raise ValueError(
                    "RAYO_GOOGLE_REDIRECT_URI must use HTTPS outside local environments."
                )
        if self.environment == "production":
            if self.payment_initiation_enabled:
                raise ValueError(
                    "Payment initiation cannot be enabled by environment alone in production."
                )
            if not self.payment_kill_switch:
                raise ValueError("RAYO_PAYMENT_KILL_SWITCH must remain enabled in production.")
            if self.pluggy_enabled and not self.pluggy_configured:
                raise ValueError("Pluggy cannot be partially configured in production.")
        return self

    @property
    def expose_api_docs(self) -> bool:
        return self.environment != "production"

    @property
    def secure_cookies(self) -> bool:
        return self.environment not in {"development", "test"}

    @property
    def google_oauth_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def pluggy_configured(self) -> bool:
        return bool(
            self.pluggy_enabled
            and self.pluggy_client_id
            and self.pluggy_client_secret
            and self.pluggy_webhook_secret
        )

    @property
    def assistant_configured(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
