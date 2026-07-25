from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class HealthSubscore(BaseModel):
    code: str
    label: str
    weight: int
    score: Decimal | None
    explanation: str


class HealthScoreResponse(BaseModel):
    algorithm_version: str
    score: Decimal | None
    confidence_percent: Decimal
    sufficient_data: bool
    disclaimer: str
    subscores: list[HealthSubscore]


class ProjectionPoint(BaseModel):
    months: int
    projected_on: date
    net_worth: Decimal
    assumption: str


class FutureResponse(BaseModel):
    algorithm_version: str
    as_of: date
    assets: Decimal
    liabilities: Decimal
    net_worth: Decimal
    assumed_monthly_savings: Decimal
    projections: list[ProjectionPoint]
    health_score: HealthScoreResponse
    calculation_notes: list[str]
