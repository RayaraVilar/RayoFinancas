from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.system import router as system_router
from app.core.config import get_settings
from app.core.database import close_database
from app.core.http_security import SecurityAndRateLimitMiddleware
from app.modules.analytics.api import router as analytics_router
from app.modules.assistant.api import router as assistant_router
from app.modules.banking.api import router as banking_router
from app.modules.business.api import router as business_router
from app.modules.debts.api import router as debts_router
from app.modules.future.api import router as future_router
from app.modules.goals.api import router as goals_router
from app.modules.identity.api import router as identity_router
from app.modules.insights.api import router as insights_router
from app.modules.ledger.api import router as ledger_router
from app.modules.payments.api import router as payments_router
from app.modules.planning.api import router as planning_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_database()


def create_app() -> FastAPI:
    settings = get_settings()
    docs_url = "/docs" if settings.expose_api_docs else None
    openapi_url = "/openapi.json" if settings.expose_api_docs else None

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url=docs_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    application.add_middleware(SecurityAndRateLimitMiddleware)
    application.include_router(system_router, prefix="/api/v1")
    application.include_router(identity_router, prefix="/api/v1")
    application.include_router(ledger_router, prefix="/api/v1")
    application.include_router(banking_router, prefix="/api/v1")
    application.include_router(analytics_router, prefix="/api/v1")
    application.include_router(assistant_router, prefix="/api/v1")
    application.include_router(planning_router, prefix="/api/v1")
    application.include_router(goals_router, prefix="/api/v1")
    application.include_router(debts_router, prefix="/api/v1")
    application.include_router(future_router, prefix="/api/v1")
    application.include_router(insights_router, prefix="/api/v1")
    application.include_router(payments_router, prefix="/api/v1")
    application.include_router(business_router, prefix="/api/v1")
    return application


app = create_app()
