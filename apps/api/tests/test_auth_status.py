from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


async def test_auth_status_is_honest_when_google_credentials_are_missing(
    client: AsyncClient,
) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        google_client_id=None,
        google_client_secret=None,
    )

    response = await client.get("/api/v1/auth/status")

    assert response.status_code == 200
    assert response.json() == {
        "google_configured": False,
        "implementation_status": "IMPLEMENTED_PENDING_CREDENTIAL",
    }


async def test_google_start_returns_503_without_credentials(client: AsyncClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        google_client_id=None,
        google_client_secret=None,
    )

    response = await client.get("/api/v1/auth/google/start")

    assert response.status_code == 503
    assert response.json() == {"detail": "Google OAuth is pending credentials."}
