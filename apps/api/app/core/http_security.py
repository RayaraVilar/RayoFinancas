from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import get_settings

logger = logging.getLogger("rayo.http")


class SecurityAndRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        started = time.monotonic()
        request_id = request.headers.get("x-request-id", "")[:64] or str(uuid4())
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        client = forwarded or (request.client.host if request.client else "unknown")
        if request.url.path == "/api/v1/auth/demo":
            route_class, limit = "demo", 5
        elif "/assistant/" in request.url.path:
            route_class, limit = "assistant", 12
        elif "/auth/" in request.url.path:
            route_class, limit = "auth", 30
        else:
            route_class, limit = "general", 180
        key = f"{client}:{route_class}"
        now = time.monotonic()
        async with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            allowed = len(bucket) < limit
            if allowed:
                bucket.append(now)
        if not allowed:
            response = Response(
                content="Too many requests.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="text/plain",
                headers={"Retry-After": "60"},
            )
        else:
            response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        )
        if get_settings().environment in {"staging", "production"}:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        response.headers["Cache-Control"] = (
            "no-store" if request.url.path.startswith("/api/v1") else "private"
        )
        logger.info(
            "request_complete method=%s path=%s status=%s duration_ms=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            round((time.monotonic() - started) * 1000, 1),
            request_id,
        )
        return response
