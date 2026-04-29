import json
import shutil
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from qc_viewer.main import app


def test_receive_draft_persists_guardrail_overrides():
    client = TestClient(app)
    response = client.post(
        "/api/automate/draft",
        data={
            "subject": "Physics",
            "paper_code": "questions",
            "curriculum": "National Curriculum",
            "ls_profile": "default",
            "hia_mode": "Low",
            "min_question_number": "2",
            "max_question_number": "120",
            "question_detection_mode": "open",
        },
        files={"file": ("sample.pdf", b"%PDF-1.4 test", "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    draft_id = payload["id"]
    meta_path = Path("qc_viewer/drafts") / draft_id / "metadata.json"
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        overrides = metadata.get("extraction_overrides", {})
        assert overrides.get("min_question_number") == 2
        assert overrides.get("max_question_number") == 120
        assert overrides.get("question_detection_mode") == "open"
    finally:
        draft_dir = meta_path.parent
        if draft_dir.exists():
            shutil.rmtree(draft_dir)
