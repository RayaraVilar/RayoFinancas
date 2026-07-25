from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.identity.models import AccountType, FinancialProfileType


class AuthStatusResponse(BaseModel):
    google_configured: bool
    implementation_status: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    email: str
    avatar_url: str | None
    onboarding_completed_at: datetime | None


class FinancialProfileCreate(BaseModel):
    type: FinancialProfileType
    name: str = Field(min_length=2, max_length=100)
    document_last4: str | None = Field(default=None, pattern=r"^\d{4}$")

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return " ".join(value.split())


class FinancialProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: FinancialProfileType
    name: str
    document_last4: str | None
    currency: str
    timezone: str


class AccountCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    institution_name: str | None = Field(default=None, max_length=120)
    type: AccountType
    current_balance: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("-99999999999999999.99"),
        le=Decimal("99999999999999999.99"),
        decimal_places=2,
    )

    @field_validator("name", "institution_name")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    financial_profile_id: UUID
    name: str
    institution_name: str | None
    type: AccountType
    current_balance: Decimal
    currency: str


class ConsentCreate(BaseModel):
    consent_type: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")
    version: str = Field(min_length=1, max_length=32)
    financial_profile_id: UUID | None = None


class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    consent_type: str
    version: str
    financial_profile_id: UUID | None
    granted_at: datetime


class OnboardingStateResponse(BaseModel):
    profile_count: int
    account_count: int
    privacy_consent_granted: bool
    completed: bool
