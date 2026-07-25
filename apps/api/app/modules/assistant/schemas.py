from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class AssistantToolDescriptor(BaseModel):
    name: str
    purpose: str
    mode: Literal["READ", "SIMULATE"]
    requires_financial_profile: bool = True


class AssistantCapabilityResponse(BaseModel):
    configured: bool
    status: Literal["READY", "PENDING_CREDENTIAL"]
    model: str
    numeric_source: str = "DETERMINISTIC_BACKEND_TOOLS"
    payment_execution_available: bool = False
    tools: list[AssistantToolDescriptor]
    guarantees: list[str]


class AssistantMessageRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1200)


class AssistantMessageResponse(BaseModel):
    answer: str
    provider: Literal["gemini", "openai"]
    model: str
    as_of: date
    generated_at: datetime
    facts_used: list[str]
    disclaimer: str


class AssistantSettingsResponse(BaseModel):
    configured: bool
    provider: Literal["gemini"]
    model: str
    key_hint: str | None
    storage: Literal["ENCRYPTED_PER_USER"]


class AssistantCredentialUpsert(BaseModel):
    api_key: str = Field(min_length=20, max_length=512)
