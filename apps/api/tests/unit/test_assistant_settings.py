from app.core.config import Settings


def test_assistant_uses_supported_gemini_model_without_global_key() -> None:
    settings = Settings(
        _env_file=None,
        ai_provider="gemini",
        gemini_model="gemini-2.5-flash",
    )

    assert settings.assistant_model == "gemini-2.5-flash"
    assert not hasattr(settings, "gemini_api_key")
