from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes.system import check_database
from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


async def test_health_reports_process_is_alive(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "rayo-api",
        "version": "0.1.0",
    }


async def test_readiness_reports_healthy_database(client: AsyncClient) -> None:
    async def database_is_up() -> bool:
        return True

    app.dependency_overrides[check_database] = database_is_up

    response = await client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "up"}


async def test_readiness_returns_503_when_database_is_down(client: AsyncClient) -> None:
    async def database_is_down() -> bool:
        return False

    app.dependency_overrides[check_database] = database_is_down

    response = await client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "down"}
