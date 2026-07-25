from pydantic import SecretStr

from app.core.config import Settings


def test_gemini_assistant_configuration_uses_gemini_credentials() -> None:
    settings = Settings(
        ai_provider="gemini",
        gemini_api_key=SecretStr("test-gemini-key"),
        gemini_model="gemini-2.5-flash",
    )

    assert settings.assistant_configured is True
    assert settings.assistant_model == "gemini-2.5-flash"


def test_gemini_assistant_is_pending_without_its_key() -> None:
    settings = Settings(
        ai_provider="gemini",
        openai_api_key=SecretStr("unrelated-openai-key"),
    )

    assert settings.assistant_configured is False
