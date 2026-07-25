from __future__ import annotations

from typing import Any, Protocol

import httpx


class AssistantProviderError(RuntimeError):
    """Safe provider error that never includes credentials or raw provider payloads."""


class AssistantProvider(Protocol):
    async def generate(self, *, instructions: str, prompt: str) -> str: ...


def _required_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssistantProviderError("O provedor não devolveu uma resposta utilizável.")
    return value.strip()


class GeminiAssistantProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client

    async def generate(self, *, instructions: str, prompt: str) -> str:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=httpx.Timeout(20.0))
        try:
            response = await client.post(
                (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{self._model}:generateContent"
                ),
                headers={"x-goog-api-key": self._api_key},
                json={
                    "systemInstruction": {"parts": [{"text": instructions}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 700,
                    },
                },
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            candidates = payload.get("candidates")
            if not isinstance(candidates, list) or not candidates:
                raise AssistantProviderError("O Gemini não devolveu uma resposta utilizável.")
            content = candidates[0].get("content", {})
            parts = content.get("parts", []) if isinstance(content, dict) else []
            text = "\n".join(
                part["text"]
                for part in parts
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            )
            return _required_text(text)
        except httpx.HTTPError as exc:
            raise AssistantProviderError(
                "O assistente está temporariamente indisponível."
            ) from exc
        finally:
            if owns_client:
                await client.aclose()


def assistant_provider(*, api_key: str, model: str) -> AssistantProvider:
    return GeminiAssistantProvider(api_key=api_key, model=model)
