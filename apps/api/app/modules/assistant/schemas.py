from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


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
