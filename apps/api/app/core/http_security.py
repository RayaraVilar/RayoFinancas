from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

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
        client = request.client.host if request.client else "unknown"
        route_class = "auth" if "/auth/" in request.url.path else "general"
        key = f"{client}:{route_class}"
        limit = 30 if route_class == "auth" else 180
        now = time.monotonic()
        async with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            if len(bucket) >= limit:
                response = Response(
                    content="Too many requests.",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="text/plain",
                    headers={"Retry-After": "60"},
                )
            else:
                bucket.append(now)
                response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
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
