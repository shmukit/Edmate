"""
Optional API key gate and simple in-process rate limits for sensitive routes.

Environment (see docs/architecture.md):
  EDMATE_REQUIRE_API_KEY — set to 1/true to require a shared secret on protected paths.
  EDMATE_API_KEY — shared secret; client sends X-API-Key or Authorization: Bearer <token>.
  EDMATE_RATE_LIMIT_PER_MINUTE — max requests per client IP per rolling minute (0 = disabled).
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_PROTECTED_PREFIXES: tuple[str, ...] = ("/api/automate", "/api/v1")

_rate_lock = threading.Lock()
_rate_buckets: Dict[str, Deque[float]] = defaultdict(deque)


def _truthy(val: str | None) -> bool:
    return (val or "").strip().lower() in ("1", "true", "yes", "on")


def _client_id(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _rate_limit_allows(client_id: str, limit_per_minute: int) -> bool:
    if limit_per_minute <= 0:
        return True
    now = time.monotonic()
    window = 60.0
    with _rate_lock:
        dq = _rate_buckets[client_id]
        while dq and dq[0] < now - window:
            dq.popleft()
        if len(dq) >= limit_per_minute:
            return False
        dq.append(now)
        return True


class EdmateApiSecurityMiddleware(BaseHTTPMiddleware):
    """Require API key (optional) and apply per-IP rate limits on automate + v1 API."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if not any(path.startswith(prefix) for prefix in _PROTECTED_PREFIXES):
            return await call_next(request)

        if _truthy(os.environ.get("EDMATE_REQUIRE_API_KEY")):
            secret = (os.environ.get("EDMATE_API_KEY") or "").strip()
            if not secret:
                return JSONResponse(
                    status_code=503,
                    content={"detail": "EDMATE_REQUIRE_API_KEY is set but EDMATE_API_KEY is empty"},
                )
            token = (request.headers.get("x-api-key") or "").strip()
            auth = request.headers.get("authorization") or ""
            if auth.lower().startswith("bearer "):
                token = token or auth[7:].strip()
            if token != secret:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        try:
            rlim = int((os.environ.get("EDMATE_RATE_LIMIT_PER_MINUTE") or "0").strip())
        except ValueError:
            rlim = 0
        if rlim > 0:
            cid = _client_id(request)
            if not _rate_limit_allows(cid, rlim):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded; try again shortly"},
                )

        return await call_next(request)
