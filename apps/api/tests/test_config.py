from app.core.config import Settings


def test_production_hides_interactive_api_docs() -> None:
    settings = Settings(
        environment="production",
        frontend_url="https://app.rayo.example",
        secret_key="production-secret-with-more-than-32-characters",
    )

    assert settings.expose_api_docs is False
    assert settings.secure_cookies is True


def test_development_exposes_interactive_api_docs() -> None:
    settings = Settings(environment="development")

    assert settings.expose_api_docs is True
    assert settings.secure_cookies is False
