from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.insights.models import InsightState


class InsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_code: str
    rule_version: str
    priority: int
    severity: str
    title: str
    message: str
    evidence: dict[str, object]
    cta_label: str | None
    cta_path: str | None
    state: InsightState
    cooldown_until: datetime
    created_at: datetime


class InsightStateUpdate(BaseModel):
    state: InsightState


class InsightFeedbackCreate(BaseModel):
    helpful: bool
    reason_code: str | None = Field(default=None, max_length=40)
