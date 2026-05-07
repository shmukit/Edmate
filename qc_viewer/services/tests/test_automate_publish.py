"""Regression: publish endpoint must reject non-allowlisted table names."""

from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client():
    from qc_viewer.app_factory import create_app

    return TestClient(create_app(), raise_server_exceptions=False)


def test_publish_rejects_injection_like_table_name(client: TestClient):
    with patch("qc_viewer.routers.automation.DatabaseService") as MockSvc:
        inst = MagicMock()
        MockSvc.return_value = inst
        res = client.post(
            "/api/automate/publish",
            json={
                "draft_id": "draft_x",
                "table_name": "chemistry_questions; DROP TABLE users;--",
                "question_data": {"question_identifier": "x", "title": "t"},
            },
        )
    assert res.status_code == 400
    assert "Invalid" in (res.json().get("detail") or "")
    inst.inject_question.assert_not_called()


def test_publish_accepts_allowlisted_table(client: TestClient):
    from qc_viewer.config import get_allowed_table_ids

    allowed = list(get_allowed_table_ids())
    assert allowed, "test needs at least one workspace table from config or legacy defaults"
    table_name = allowed[0]
    with patch("qc_viewer.routers.automation.DatabaseService") as MockSvc:
        inst = MagicMock()
        inst.inject_question.return_value = True
        MockSvc.return_value = inst
        res = client.post(
            "/api/automate/publish",
            json={
                "draft_id": "draft_x",
                "table_name": table_name,
                "question_data": {"question_identifier": "x", "title": "t"},
            },
        )
    assert res.status_code == 200, res.text
    inst.inject_question.assert_called_once()
    args, _ = inst.inject_question.call_args
    assert args[0] == table_name


def test_publish_accepts_questions_table(client: TestClient):
    with patch("qc_viewer.routers.automation.DatabaseService") as MockSvc:
        inst = MagicMock()
        inst.inject_question.return_value = True
        MockSvc.return_value = inst
        res = client.post(
            "/api/automate/publish",
            json={
                "draft_id": "draft_x",
                "table_name": "questions",
                "question_data": {"question_identifier": "x", "title": "t"},
            },
        )
    assert res.status_code == 200
    inst.inject_question.assert_called_once()
    args, _ = inst.inject_question.call_args
    assert args[0] == "questions"
