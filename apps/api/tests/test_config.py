import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_hides_interactive_api_docs() -> None:
    settings = Settings(
        environment="production",
        frontend_url="https://app.rayo.example",
        public_api_url="https://api.rayo.example",
        secret_key="production-secret-with-more-than-32-characters",
    )

    assert settings.expose_api_docs is False
    assert settings.secure_cookies is True


def test_development_exposes_interactive_api_docs() -> None:
    settings = Settings(environment="development")

    assert settings.expose_api_docs is True
    assert settings.secure_cookies is False


def test_render_postgres_url_uses_asyncpg_driver() -> None:
    settings = Settings(database_url="postgresql://user:password@db.example/rayo")

    assert settings.database_url == "postgresql+asyncpg://user:password@db.example/rayo"


def test_production_rejects_disabled_payment_kill_switch() -> None:
    with pytest.raises(ValidationError, match="KILL_SWITCH"):
        Settings(
            environment="production",
            frontend_url="https://app.rayo.example",
            public_api_url="https://api.rayo.example",
            secret_key="production-secret-with-more-than-32-characters",
            payment_kill_switch=False,
        )
