from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.modules.analytics.schemas import DashboardAnalyticsResponse
from app.modules.analytics.service import calculate_dashboard_analytics
from app.modules.identity.dependencies import (
    CurrentScope,
    DatabaseSession,
    SelectedFinancialContext,
)

router = APIRouter()


@router.get(
    "/analytics/dashboard",
    response_model=DashboardAnalyticsResponse,
    tags=["analytics"],
)
async def get_dashboard_analytics(
    db: DatabaseSession,
    scope: CurrentScope,
    context: SelectedFinancialContext,
    as_of: Annotated[date, Query(default_factory=date.today)],
) -> DashboardAnalyticsResponse:
    return await calculate_dashboard_analytics(
        db,
        scope.user.id,
        context.profile.id if context.profile else None,
        as_of,
    )
