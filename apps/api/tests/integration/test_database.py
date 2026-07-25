from __future__ import annotations

import os

import pytest

from app.core.database import database_is_ready

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("RAYO_RUN_INTEGRATION") != "1",
    reason="Set RAYO_RUN_INTEGRATION=1 to test PostgreSQL.",
)
async def test_database_accepts_connections() -> None:
    assert await database_is_ready() is True
