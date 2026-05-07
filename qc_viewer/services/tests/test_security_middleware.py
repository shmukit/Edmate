"""Regression tests for optional API key and rate limiting middleware."""

import os

import pytest
from fastapi.testclient import TestClient

from qc_viewer.app_factory import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("EDMATE_REQUIRE_API_KEY", raising=False)
    monkeypatch.delenv("EDMATE_API_KEY", raising=False)
    monkeypatch.setenv("EDMATE_RATE_LIMIT_PER_MINUTE", "0")
    with TestClient(create_app()) as c:
        yield c


def test_automate_route_ok_without_key_when_not_required(client):
    r = client.get("/api/automate/config")
    assert r.status_code == 200


def test_api_key_required_401(monkeypatch):
    monkeypatch.setenv("EDMATE_REQUIRE_API_KEY", "1")
    monkeypatch.setenv("EDMATE_API_KEY", "secret-test-key")
    monkeypatch.setenv("EDMATE_RATE_LIMIT_PER_MINUTE", "0")
    with TestClient(create_app()) as c:
        r = c.get("/api/automate/config")
        assert r.status_code == 401
        r2 = c.get("/api/automate/config", headers={"X-API-Key": "secret-test-key"})
        assert r2.status_code == 200


def test_api_key_bearer_accepted(monkeypatch):
    monkeypatch.setenv("EDMATE_REQUIRE_API_KEY", "1")
    monkeypatch.setenv("EDMATE_API_KEY", "tok")
    monkeypatch.setenv("EDMATE_RATE_LIMIT_PER_MINUTE", "0")
    with TestClient(create_app()) as c:
        r = c.get("/api/automate/config", headers={"Authorization": "Bearer tok"})
        assert r.status_code == 200


def test_rate_limit_429(monkeypatch):
    from qc_viewer.middleware import security as sec

    sec._rate_buckets.clear()
    monkeypatch.delenv("EDMATE_REQUIRE_API_KEY", raising=False)
    monkeypatch.setenv("EDMATE_RATE_LIMIT_PER_MINUTE", "2")
    with TestClient(create_app()) as c:
        assert c.get("/api/automate/config").status_code == 200
        assert c.get("/api/automate/config").status_code == 200
        r = c.get("/api/automate/config")
        assert r.status_code == 429


def test_require_key_without_secret_returns_503(monkeypatch):
    monkeypatch.setenv("EDMATE_REQUIRE_API_KEY", "1")
    monkeypatch.delenv("EDMATE_API_KEY", raising=False)
    monkeypatch.setenv("EDMATE_RATE_LIMIT_PER_MINUTE", "0")
    with TestClient(create_app()) as c:
        r = c.get("/api/automate/config")
        assert r.status_code == 503
