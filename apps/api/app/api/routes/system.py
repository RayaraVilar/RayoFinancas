from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.database import database_is_ready

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database: Literal["up", "down"]


async def check_database() -> bool:
    return await database_is_ready()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report process liveness without checking external dependencies."""
    return HealthResponse(status="ok", service="rayo-api", version="0.1.0")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
async def readiness(
    database_ready: Annotated[bool, Depends(check_database)],
) -> ReadinessResponse | JSONResponse:
    """Report whether dependencies required to serve traffic are available."""
    if not database_ready:
        payload = ReadinessResponse(status="not_ready", database="down")
        return JSONResponse(status_code=503, content=payload.model_dump())

    return ReadinessResponse(status="ready", database="up")
