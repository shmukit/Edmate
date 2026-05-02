"""
Test suite for CORS middleware correctness in the Edmate FastAPI app.

These tests guard against two specific bugs in app_factory.py:
  Bug 1 – CORSMiddleware was registered AFTER include_router() calls,
           which caused OPTIONS preflights to hit the router first and
           receive a 405 without CORS headers (browser reports CORS error).
  Bug 2 – allow_origins=["*"] does NOT reflect the request origin, which
           some browsers reject when non-safelisted headers (e.g. X-API-Key)
           are present in the preflight.

Run with:
    python -m pytest qc_viewer/services/tests/test_cors.py -v
"""

import pytest
from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PARTNER_ORIGIN = "http://localhost:5173"
CUSTOM_HEADERS_STR = "X-API-Key, Content-Type"


def _preflight_headers(
    method: str = "POST",
    request_headers: str = CUSTOM_HEADERS_STR,
    origin: str = PARTNER_ORIGIN,
) -> dict:
    """Build the standard set of preflight request headers."""
    return {
        "Origin": origin,
        "Access-Control-Request-Method": method,
        "Access-Control-Request-Headers": request_headers,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def client():
    """
    Create a TestClient from the real app factory.
    If heavy imports fail (e.g. DB not configured), the fixture is skipped
    gracefully so this file can still be collected in CI.
    """
    try:
        from qc_viewer.app_factory import create_app
        app = create_app()
        return TestClient(app, raise_server_exceptions=False)
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Could not create app (import error): {exc}")


# ---------------------------------------------------------------------------
# Bug 1 – Middleware ordering
# ---------------------------------------------------------------------------
class TestPreflightMiddlewareOrdering:
    """
    OPTIONS preflight requests must be handled by CORSMiddleware and return
    200, NOT 405 from the router.  This only works when add_middleware() is
    called before include_router().
    """

    def test_preflight_automate_draft_returns_200(self, client: TestClient):
        """POST /api/automate/draft preflight must return 200, not 405."""
        resp = client.options(
            "/api/automate/draft",
            headers=_preflight_headers("POST"),
        )
        assert resp.status_code == 200, (
            f"Expected 200 from CORS preflight but got {resp.status_code}. "
            "This usually means CORSMiddleware was registered after include_router()."
        )

    def test_preflight_v1_extract_returns_200(self, client: TestClient):
        """POST /api/v1/extract preflight (used by partner BYOK flow) must return 200."""
        resp = client.options(
            "/api/v1/extract",
            headers=_preflight_headers("POST", "X-Gemini-Key, Content-Type"),
        )
        assert resp.status_code == 200, (
            f"Preflight to /api/v1/extract returned {resp.status_code}."
        )

    def test_preflight_jobs_returns_200(self, client: TestClient):
        """/api/v1/jobs/:id preflight – the route shown as CORS error in the screenshot."""
        resp = client.options(
            "/api/v1/jobs/job_abc123",
            headers=_preflight_headers("GET", "X-API-Key"),
        )
        assert resp.status_code == 200, (
            f"Preflight to /api/v1/jobs/:id returned {resp.status_code}."
        )


# ---------------------------------------------------------------------------
# Bug 2 – Origin reflection (not wildcard)
# ---------------------------------------------------------------------------
class TestOriginReflection:
    """
    When custom headers are present, the server MUST reflect the exact request
    origin in Access-Control-Allow-Origin (not return a literal '*').
    """

    def test_preflight_reflects_partner_origin(self, client: TestClient):
        resp = client.options(
            "/api/automate/draft",
            headers=_preflight_headers("POST"),
        )
        assert resp.status_code == 200
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao == PARTNER_ORIGIN, (
            f"Expected origin '{PARTNER_ORIGIN}' to be reflected but got '{acao}'. "
            "Ensure allow_origin_regex=r'.*' is set instead of allow_origins=['*']."
        )

    def test_preflight_reflects_arbitrary_origin(self, client: TestClient):
        """Any third-party origin should also be reflected (open-source repo)."""
        custom_origin = "https://school.alopoth.com"
        resp = client.options(
            "/api/automate/drafts",
            headers=_preflight_headers("GET", "Content-Type", origin=custom_origin),
        )
        assert resp.status_code == 200
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao == custom_origin, (
            f"Expected '{custom_origin}' but got '{acao}'."
        )

    def test_wildcard_not_returned_for_preflight_with_custom_header(self, client: TestClient):
        """
        Browsers reject Access-Control-Allow-Origin: * when non-safelisted
        headers are in the preflight.  The server must never return '*'.
        """
        resp = client.options(
            "/api/automate/draft",
            headers=_preflight_headers("POST", "X-API-Key"),
        )
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao != "*", (
            "Server returned a wildcard origin. This causes browser CORS failures "
            "when non-safelisted request headers (X-API-Key, X-Gemini-Key…) are used."
        )


# ---------------------------------------------------------------------------
# Simple cross-origin requests (no preflight)
# ---------------------------------------------------------------------------
class TestSimpleCrossOriginRequests:
    """
    Simple requests (safelisted methods + headers) don't trigger a preflight
    but still need the ACAO header set correctly on the response.
    """

    def test_get_drafts_has_cors_header(self, client: TestClient):
        resp = client.get(
            "/api/automate/drafts",
            headers={"Origin": PARTNER_ORIGIN},
        )
        # Response may be 200 or 500 depending on env, but CORS header must exist
        assert "access-control-allow-origin" in resp.headers, (
            "Simple GET to /api/automate/drafts missing Access-Control-Allow-Origin header."
        )
        assert resp.headers["access-control-allow-origin"] == PARTNER_ORIGIN

    def test_get_config_has_cors_header(self, client: TestClient):
        resp = client.get(
            "/api/automate/config",
            headers={"Origin": PARTNER_ORIGIN},
        )
        assert resp.headers.get("access-control-allow-origin") == PARTNER_ORIGIN


# ---------------------------------------------------------------------------
# Custom BYOK headers are explicitly allowed
# ---------------------------------------------------------------------------
class TestByokHeadersAllowed:
    """
    The partner sends BYOK headers in the preflight.  The server must list
    them in Access-Control-Allow-Headers so the browser permits the actual
    request.
    """

    BYOK_HEADERS = [
        "X-API-Key",
        "X-LLM-Provider",
        "X-Model-ID",
        "X-Gemini-Key",
        "X-OpenAI-Key",
    ]

    @pytest.mark.parametrize("header_name", BYOK_HEADERS)
    def test_byok_header_allowed_in_preflight(self, client: TestClient, header_name: str):
        resp = client.options(
            "/api/automate/draft",
            headers=_preflight_headers("POST", header_name),
        )
        assert resp.status_code == 200
        allowed = resp.headers.get("access-control-allow-headers", "").lower()
        # Either explicitly listed or wildcard "*" (wildcard is fine for Allow-Headers)
        assert header_name.lower() in allowed or "*" in allowed, (
            f"Header '{header_name}' not present in Access-Control-Allow-Headers: '{allowed}'"
        )
