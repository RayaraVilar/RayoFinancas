from __future__ import annotations

import httpx

from app.core.secret_storage import decrypt_user_secret, encrypt_user_secret
from app.modules.assistant.providers import GeminiAssistantProvider


def test_user_secret_is_encrypted_and_round_trips() -> None:
    api_key = "test-user-owned-key-123456789"
    application_secret = "application-secret-with-at-least-32-characters"

    encrypted = encrypt_user_secret(api_key, application_secret)

    assert api_key not in encrypted
    assert decrypt_user_secret(encrypted, application_secret) == api_key


async def test_gemini_provider_uses_header_and_parses_text() -> None:
    seen_request: httpx.Request | None = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": "Resposta baseada nos dados."}]}}
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = GeminiAssistantProvider(
        api_key="user-owned-secret-key",
        model="gemini-2.5-flash",
        client=client,
    )
    try:
        answer = await provider.generate(instructions="Safe prompt", prompt="Question")
    finally:
        await client.aclose()

    assert answer == "Resposta baseada nos dados."
    assert seen_request is not None
    assert seen_request.headers["x-goog-api-key"] == "user-owned-secret-key"
    assert "user-owned-secret-key" not in str(seen_request.url)
