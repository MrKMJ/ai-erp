from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import set_request_id

logger = logging.getLogger("erp.http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, logs one line per request, sets timing + id headers."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        set_request_id(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled error %s %s", request.method, request.url.path)
            set_request_id(None)
            return JSONResponse({"detail": "Internal server error"}, status_code=500)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = rid
        response.headers["x-response-time-ms"] = f"{elapsed_ms:.1f}"
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        set_request_id(None)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-process sliding-window limiter keyed by client IP.

    Good enough for a single instance; put a shared limiter (Redis) in front when
    you run multiple replicas.
    """

    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _limit_for(self, path: str) -> int:
        if path.startswith("/api/v1/auth"):
            return settings.auth_rate_limit_per_minute
        return settings.rate_limit_per_minute

    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled or request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path in ("/health", "/health/live", "/"):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        key = f"{client}:{'auth' if request.url.path.startswith('/api/v1/auth') else 'api'}"
        limit = self._limit_for(request.url.path)
        now = time.time()
        window = self._hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            retry = 60 - (now - window[0])
            return JSONResponse(
                {"detail": "Rate limit exceeded, slow down"},
                status_code=429,
                headers={"Retry-After": str(int(retry) + 1)},
            )
        window.append(now)
        return await call_next(request)
