"""
Provider-agnostic authentication middleware for qc_viewer.

Environment:
  EDMATE_AUTH_REQUIRED — set to 1/true to enforce token-based auth.
    When false (default / self-hosted), every request is treated as a 'pro'
    user with id 'anonymous'.  When true and no valid token is presented the
    request proceeds as 'anonymous' on the 'anonymous' (limited) plan.

The actual identity backend is injected via :func:`set_auth_provider`.
"""

from __future__ import annotations

import logging
import os
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public data structures
# ---------------------------------------------------------------------------


@dataclass
class UserInfo:
    """Minimal identity payload returned by an :class:`AuthProvider`."""

    user_id: str
    email: Optional[str] = None
    display_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Auth provider interface + dummy implementation
# ---------------------------------------------------------------------------


class AuthProvider(ABC):
    """Abstract authentication / user-lookup backend."""

    @abstractmethod
    async def verify_token(self, token: str) -> Optional[UserInfo]:
        """Return a :class:`UserInfo` if *token* is valid, else ``None``."""
        ...

    @abstractmethod
    async def get_user_plan(self, user_id: str) -> str:
        """Return the billing plan name (e.g. ``'free'``, ``'pro'``) for *user_id*."""
        ...


    @abstractmethod
    def save_user_byok(self, user_id: str, provider: str, api_key: str, model_id: Optional[str] = None) -> bool:
        """Save a BYOK configuration for a user. Returns True if successful."""
        ...


class DummyAuthProvider(AuthProvider):
    """Placeholder that rejects every token.

    Wire in a real provider (Firebase, Supabase, …) before enabling
    ``EDMATE_AUTH_REQUIRED``.
    """

    async def verify_token(self, token: str) -> Optional[UserInfo]:
        return None

    async def get_user_plan(self, user_id: str) -> str:
        return "anonymous"

    def save_user_byok(self, user_id: str, provider: str, api_key: str, model_id: Optional[str] = None) -> bool:
        return True


# ---------------------------------------------------------------------------
# Module-level singleton (same pattern as job_repository.py)
# ---------------------------------------------------------------------------

_auth_provider: Optional[AuthProvider] = None
_provider_lock = threading.Lock()


def get_auth_provider() -> AuthProvider:
    """Singleton auth provider (swap via :func:`set_auth_provider` in tests)."""
    global _auth_provider
    with _provider_lock:
        if _auth_provider is None:
            _auth_provider = DummyAuthProvider()
        return _auth_provider


def set_auth_provider(provider: Optional[AuthProvider]) -> None:
    """Test hook: pass ``None`` to reset to :class:`DummyAuthProvider` on next get."""
    global _auth_provider
    with _provider_lock:
        _auth_provider = provider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PUBLIC_EXACT: frozenset[str] = frozenset((
    "/",
    "/index.html",
    "/how_it_works.html",
    "/api/health",
))

_PUBLIC_PREFIXES: tuple[str, ...] = (
    "/css/",
    "/js/",
    "/favicon",
    "/docs/",
)


def _truthy(val: str | None) -> bool:
    return (val or "").strip().lower() in ("1", "true", "yes", "on")


def _is_public(path: str) -> bool:
    """Return ``True`` if *path* should bypass authentication entirely."""
    if path in _PUBLIC_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


def _extract_bearer_token(request: Request) -> Optional[str]:
    """Pull the token from ``Authorization: Bearer <token>``, or ``None``."""
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        return token if token else None
    return None


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class EdmateAuthMiddleware(BaseHTTPMiddleware):
    """Populate ``request.state.user_id`` and ``request.state.plan``.

    Three operating modes:

    1. **Self-hosted** (``EDMATE_AUTH_REQUIRED=false``, the default):
       Every request is treated as ``user_id='anonymous'``,
       ``plan='pro'`` — full, unrestricted access.

    2. **Cloud, unauthenticated** (``EDMATE_AUTH_REQUIRED=true``, no token):
       ``user_id='anonymous'``, ``plan='anonymous'`` — limited access.

    3. **Cloud, authenticated** (``EDMATE_AUTH_REQUIRED=true``, valid token):
       ``user_id`` and ``plan`` are resolved via the configured
       :class:`AuthProvider`.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Let CORS preflight and public assets through untouched.
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if _is_public(path):
            return await call_next(request)

        # --- Mode 1: self-hosted (auth not required) ---
        if not _truthy(os.environ.get("EDMATE_AUTH_REQUIRED")):
            request.state.user_id = "anonymous"
            request.state.plan = "pro"
            return await call_next(request)

        # --- Auth is required (cloud mode) ---
        token = _extract_bearer_token(request)

        if token is None:
            # Mode 2: no credentials supplied → limited anonymous access.
            request.state.user_id = "anonymous"
            request.state.plan = "anonymous"
            return await call_next(request)

        # Mode 3: token present → verify with the configured provider.
        provider = get_auth_provider()
        user = await provider.verify_token(token)

        if user is None:
            # Invalid / expired token → treat as anonymous.
            request.state.user_id = "anonymous"
            request.state.plan = "anonymous"
            return await call_next(request)

        request.state.user_id = user.user_id
        request.state.plan = await provider.get_user_plan(user.user_id)
        return await call_next(request)
