"""
Plan-based quota enforcement for upload and export routes.

Reads ``request.state.plan`` (set by the auth middleware) and enforces
per-plan limits on uploads and exports.

Environment:
  EDMATE_AUTH_REQUIRED — when falsy (or unset), all quota checks are skipped
                         so that self-hosted deployments are unrestricted.

v1 note: upload counters are kept in-process memory and reset each calendar
month.  A DB-backed implementation will replace this later.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# ── plan definitions ────────────────────────────────────────────────────────

PLAN_LIMITS: Dict[str, Dict] = {
    "anonymous": {
        "max_uploads_per_month": 999,
        "max_file_size_mb": 50,
        "can_export": False,
        "history_ttl_days": 1,
    },
    "free": {
        "max_uploads_per_month": 999,
        "max_file_size_mb": 50,
        "can_export": False,
        "history_ttl_days": 1,
    },
    "basic": {
        "max_uploads_per_month": 30,
        "max_file_size_mb": 10,
        "can_export": True,
        "history_ttl_days": 30,
    },
    "pro": {
        "max_uploads_per_month": 999999,
        "max_file_size_mb": 25,
        "can_export": True,
        "history_ttl_days": -1,
    },
}

# ── in-memory upload counters (v1) ──────────────────────────────────────────

_counter_lock = threading.Lock()
# key: (user_id, "YYYY-MM") → count
_upload_counts: Dict[Tuple[str, str], int] = {}


def _truthy(val: str | None) -> bool:
    return (val or "").strip().lower() in ("1", "true", "yes", "on")


def _current_month_key() -> str:
    """Return the current year-month string, e.g. ``'2026-06'``."""
    return time.strftime("%Y-%m", time.gmtime())


def _get_and_increment_uploads(user_id: str) -> int:
    """Atomically read the current month's upload count, increment, and return
    the *previous* value (i.e. the count before this request)."""
    month = _current_month_key()
    key = (user_id, month)
    with _counter_lock:
        current = _upload_counts.get(key, 0)
        _upload_counts[key] = current + 1
        return current


def _rollback_upload(user_id: str) -> None:
    """Undo the increment when the request is going to be rejected."""
    month = _current_month_key()
    key = (user_id, month)
    with _counter_lock:
        val = _upload_counts.get(key, 0)
        if val > 0:
            _upload_counts[key] = val - 1


def _quota_error(detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=402,
        content={"detail": detail, "upgrade_required": True},
    )


# ── middleware ──────────────────────────────────────────────────────────────


class EdmateQuotaMiddleware(BaseHTTPMiddleware):
    """Enforce plan-based quotas on upload and export routes."""

    async def dispatch(self, request: Request, call_next):
        # Skip everything for preflight requests.
        if request.method == "OPTIONS":
            return await call_next(request)

        # Self-hosted mode: no quotas.
        if not _truthy(os.environ.get("EDMATE_AUTH_REQUIRED")):
            return await call_next(request)

        path = request.url.path

        # ── upload route ────────────────────────────────────────────────
        if request.method == "POST" and path == "/api/automate/draft":
            return await self._check_upload(request, call_next)

        # ── export route ────────────────────────────────────────────────
        if request.method == "GET" and path.startswith("/api/automate/draft/") and path.endswith("/export"):
            return await self._check_export(request, call_next)

        return await call_next(request)

    # ── private helpers ─────────────────────────────────────────────────

    async def _check_upload(self, request: Request, call_next):
        plan_name = getattr(request.state, "plan", "anonymous")
        limits = PLAN_LIMITS.get(plan_name, PLAN_LIMITS["anonymous"])
        user_id = getattr(request.state, "user_id", None) or "anon"

        # File size check via content-length header.
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                size_mb = int(content_length) / (1024 * 1024)
            except (ValueError, TypeError):
                size_mb = 0.0
            max_mb = limits["max_file_size_mb"]
            if size_mb > max_mb:
                return _quota_error(
                    f"File size exceeds the {max_mb} MB limit for the "
                    f"'{plan_name}' plan. Please upgrade your plan.",
                )

        # Monthly upload count.
        used = _get_and_increment_uploads(user_id)
        max_uploads = limits["max_uploads_per_month"]
        if used >= max_uploads:
            _rollback_upload(user_id)
            return _quota_error(
                f"Monthly upload limit ({max_uploads}) reached for the "
                f"'{plan_name}' plan. Please upgrade your plan.",
            )

        return await call_next(request)

    async def _check_export(self, request: Request, call_next):
        plan_name = getattr(request.state, "plan", "anonymous")
        limits = PLAN_LIMITS.get(plan_name, PLAN_LIMITS["anonymous"])

        if not limits["can_export"]:
            return _quota_error(
                f"Export is not available on the '{plan_name}' plan. "
                f"Please upgrade to a plan that supports exports.",
            )

        return await call_next(request)
