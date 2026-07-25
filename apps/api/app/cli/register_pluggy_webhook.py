from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.config import get_settings


def _webhook_rows(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("results", "webhooks", "data"):
            items = payload.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
    return []


async def register_webhook() -> str:
    settings = get_settings()
    if not settings.pluggy_configured:
        raise RuntimeError("Pluggy credentials and webhook secret must be configured.")
    if not settings.public_api_url.startswith("https://"):
        raise RuntimeError("Webhook registration requires an HTTPS RAYO_PUBLIC_API_URL.")

    webhook_url = f"{settings.public_api_url.rstrip('/')}/api/v1/webhooks/pluggy"
    secret = settings.pluggy_webhook_secret
    headers = {
        "X-Rayo-Webhook-Secret": secret.get_secret_value() if secret else "",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        auth_response = await client.post(
            f"{settings.pluggy_api_url.rstrip('/')}/auth",
            json={
                "clientId": settings.pluggy_client_id,
                "clientSecret": (
                    settings.pluggy_client_secret.get_secret_value()
                    if settings.pluggy_client_secret
                    else ""
                ),
            },
        )
        auth_response.raise_for_status()
        api_key = auth_response.json().get("apiKey")
        if not isinstance(api_key, str) or not api_key:
            raise RuntimeError("Pluggy authentication response did not contain an API key.")
        api_headers = {"X-API-KEY": api_key}
        list_response = await client.get(
            f"{settings.pluggy_api_url.rstrip('/')}/webhooks",
            headers=api_headers,
        )
        list_response.raise_for_status()
        rows = _webhook_rows(list_response.json()) if list_response.status_code != 204 else []
        existing = next(
            (
                item
                for item in rows
                if item.get("url") == webhook_url and item.get("event") == "all"
            ),
            None,
        )
        payload = {
            "url": webhook_url,
            "event": "all",
            "headers": headers,
        }
        if existing and isinstance(existing.get("id"), str):
            response = await client.patch(
                f"{settings.pluggy_api_url.rstrip('/')}/webhooks/{existing['id']}",
                headers=api_headers,
                json={**payload, "enabled": True},
            )
            action = "updated"
        else:
            response = await client.post(
                f"{settings.pluggy_api_url.rstrip('/')}/webhooks",
                headers=api_headers,
                json=payload,
            )
            action = "created"
        response.raise_for_status()
    return f"Pluggy webhook {action}: {webhook_url}"


def main() -> None:
    print(asyncio.run(register_webhook()))


if __name__ == "__main__":
    main()
