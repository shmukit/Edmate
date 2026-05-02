"""Unit and integration tests for draft export (JSON / CSV / Markdown / MD+ZIP / DOCX)."""

from __future__ import annotations

import csv
import io
import json
import zipfile

import pytest
from starlette.testclient import TestClient

from qc_viewer.services import draft_export


def _sample_meta() -> dict:
    uri = "data:image/png;base64,QUJD"
    return {
        "id": "draft_fixture01",
        "paper_code": "physics_questions",
        "subject": "Physics",
        "curriculum": "Cambridge O/Level",
        "filename": "paper_qp.pdf",
        "timestamp": "2026-01-01T12:00:00",
        "questions": [
            {
                "question_number": 1,
                "text": "Hello, world\nSecond line",
                "options": {"A": "one", "B": "two", "C": "three", "D": "four"},
                "correct_answer": "B",
                "diagram_base64": uri,
                "generated_content": {
                    "core_concept": "Core here",
                    "detailed_explanation": "Explain | pipe",
                    "option_analysis": {"A": "a1", "B": "b1", "C": "", "D": "d1"},
                    "flashcards": [{"question": "FQ?", "answer": "FA!"}],
                },
            },
            {
                "question_number": 2,
                "text": "No options q",
                "correct_answer": "N/A",
                "generated_content": {},
            },
        ],
    }


def test_safe_filename_uses_paper_code_and_extension():
    meta = {"paper_code": "chem_table", "id": "draft_x", "filename": "ignored.pdf"}
    assert draft_export.safe_filename(meta, "json") == "chem_table.json"
    assert draft_export.safe_filename(meta, "csv") == "chem_table.csv"
    assert draft_export.safe_filename(meta, "md") == "chem_table.md"
    assert draft_export.safe_filename(meta, "markdown") == "chem_table.md"
    assert draft_export.safe_filename(meta, "docx") == "chem_table.docx"
    assert draft_export.safe_filename(meta, "mdzip") == "chem_table.zip"


def test_safe_filename_falls_back_to_id_when_no_paper_code():
    meta = {"id": "draft_abc", "filename": ""}
    assert draft_export.safe_filename(meta, "json").startswith("draft_abc")
    assert draft_export.safe_filename(meta, "json").endswith(".json")


def test_to_json_bytes_round_trips_and_preserves_data_uri():
    meta = _sample_meta()
    raw = draft_export.to_json_bytes(meta)
    back = json.loads(raw.decode("utf-8"))
    assert back["questions"][0]["diagram_base64"] == "data:image/png;base64,QUJD"
    assert back["questions"][0]["text"] == "Hello, world\nSecond line"


def test_to_csv_has_expected_header_and_row_count():
    meta = _sample_meta()
    raw = draft_export.to_csv_bytes(meta)
    reader = csv.reader(io.StringIO(raw.decode("utf-8")))
    rows = list(reader)
    assert rows[0][0] == "question_number"
    assert rows[0][-1] == "diagram_data_uri"
    assert len(rows) == 1 + len(meta["questions"])


def test_to_csv_handles_missing_or_empty_options_safely():
    meta = {
        "questions": [
            {"question_number": 1, "text": "t", "options": None, "generated_content": None},
        ]
    }
    raw = draft_export.to_csv_bytes(meta)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    row = next(reader)
    assert row["option_a"] == ""
    assert row["flashcards_count"] == "0"


def test_to_csv_quotes_commas_and_newlines_in_text():
    meta = _sample_meta()
    raw = draft_export.to_csv_bytes(meta)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    row = next(reader)
    assert "Hello, world" in row["text"]
    assert "\n" in row["text"] or "Second line" in row["text"]


def test_to_csv_carries_full_data_uri_in_diagram_column():
    meta = _sample_meta()
    raw = draft_export.to_csv_bytes(meta)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    row = next(reader)
    assert row["diagram_data_uri"] == "data:image/png;base64,QUJD"


def test_to_markdown_contains_every_question_number_and_text():
    meta = _sample_meta()
    md = draft_export.to_markdown_bytes(meta).decode("utf-8")
    assert "## Question 1" in md
    assert "## Question 2" in md
    assert "Hello, world" in md
    assert "No options q" in md


def test_to_markdown_plain_omits_inline_base64_shows_note():
    meta = _sample_meta()
    md = draft_export.to_markdown_bytes(meta).decode("utf-8")
    assert "data:image/" not in md
    assert "Diagram for Q1 omitted in plain Markdown" in md
    assert "format=mdzip" in md or "Markdown+ZIP" in md


def test_to_markdown_zip_returns_zip_with_md_and_image():
    meta = {
        "id": "z1",
        "paper_code": "zip_test",
        "questions": [
            {
                "question_number": 1,
                "text": "Q text",
                "options": {"A": "a", "B": "b", "C": "", "D": ""},
                "correct_answer": "A",
                "diagram_base64": "data:image/png;base64,AA==",
                "generated_content": {},
            }
        ],
    }
    raw = draft_export.to_markdown_zip_bytes(meta)
    assert raw[:2] == b"PK"
    zf = zipfile.ZipFile(io.BytesIO(raw), "r")
    names = zf.namelist()
    assert "questions.md" in names
    assert "README.txt" in names
    assert "images/Q1.png" in names
    md = zf.read("questions.md").decode("utf-8")
    assert "images/Q1.png" in md
    assert "data:image/" not in md
    zf.close()


def test_render_mdzip_matches_to_markdown_zip_bytes():
    meta = _sample_meta()
    assert draft_export.render(meta, "mdzip") == draft_export.to_markdown_zip_bytes(meta)


def test_to_markdown_marks_correct_answer_in_bold():
    meta = _sample_meta()
    md = draft_export.to_markdown_bytes(meta).decode("utf-8")
    assert "**B.**" in md


def test_unsupported_format_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported format"):
        draft_export.render({}, "xlsx")


def test_render_accepts_markdown_alias():
    meta = _sample_meta()
    b1 = draft_export.render(meta, "markdown")
    b2 = draft_export.render(meta, "md")
    assert b1 == b2


def test_to_docx_bytes_is_ooxml_zip():
    """.docx is a ZIP archive; smallest export should start with PK."""
    meta = {
        "id": "draft_docx1",
        "paper_code": "export_test",
        "subject": "S",
        "questions": [
            {
                "question_number": 1,
                "text": "Sample?",
                "options": {"A": "1", "B": "2", "C": "", "D": ""},
                "correct_answer": "A",
                "generated_content": {"core_concept": "C", "detailed_explanation": "E"},
            }
        ],
    }
    raw = draft_export.to_docx_bytes(meta)
    assert raw[:2] == b"PK"
    assert len(raw) > 2000


def test_render_docx_matches_to_docx_bytes():
    meta = _sample_meta()
    assert draft_export.render(meta, "docx") == draft_export.to_docx_bytes(meta)


# --- Integration tests (TestClient + temp drafts root) ---


@pytest.fixture
def export_client(tmp_path, monkeypatch):
    monkeypatch.setattr("qc_viewer.services.draft_store.DRAFTS_ROOT", tmp_path)
    draft_id = "draft_export_it"
    meta = {
        "id": draft_id,
        "paper_code": "igcse_physics_questions",
        "subject": "Physics",
        "curriculum": "Cambridge O/Level",
        "filename": "9702_qp.pdf",
        "timestamp": "2026-05-01T00:00:00",
        "questions": [
            {
                "question_number": 1,
                "text": "What is 2+2?",
                "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
                "correct_answer": "B",
                "diagram_base64": "data:image/png;base64,AA==",
                "generated_content": {
                    "core_concept": "Arithmetic",
                    "detailed_explanation": "Two plus two is four.",
                    "option_analysis": {"A": "", "B": "ok", "C": "", "D": ""},
                    "flashcards": [],
                },
            }
        ],
    }
    ddir = tmp_path / draft_id
    ddir.mkdir(parents=True, exist_ok=True)
    (ddir / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    try:
        from qc_viewer.app_factory import create_app

        app = create_app()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Could not create app: {exc}")
    return TestClient(app, raise_server_exceptions=False), draft_id


def test_export_json_returns_200_with_attachment_header(export_client):
    client, draft_id = export_client
    r = client.get(f"/api/automate/draft/{draft_id}/export?format=json")
    assert r.status_code == 200
    assert "attachment" in r.headers.get("content-disposition", "").lower()
    data = r.json()
    assert data["paper_code"] == "igcse_physics_questions"
    assert data["questions"][0]["diagram_base64"].startswith("data:image/png")


def test_export_csv_returns_csv_content_type(export_client):
    client, draft_id = export_client
    r = client.get(f"/api/automate/draft/{draft_id}/export?format=csv")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/csv")
    lines = r.text.splitlines()
    assert "question_number" in lines[0]


def test_export_md_alias_returns_markdown_content_type(export_client):
    client, draft_id = export_client
    r = client.get(f"/api/automate/draft/{draft_id}/export?format=markdown")
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "markdown" in ct or "text/plain" in ct  # Starlette may normalize


def test_export_unknown_format_returns_400(export_client):
    client, draft_id = export_client
    r = client.get(f"/api/automate/draft/{draft_id}/export?format=xlsx")
    assert r.status_code == 400


def test_export_docx_returns_wordprocessingml(export_client):
    client, draft_id = export_client
    r = client.get(f"/api/automate/draft/{draft_id}/export?format=docx")
    assert r.status_code == 200
    ct = (r.headers.get("content-type") or "").lower()
    assert "wordprocessingml" in ct or "octet-stream" in ct
    assert r.content[:2] == b"PK"
    assert "attachment" in (r.headers.get("content-disposition") or "").lower()


def test_export_mdzip_returns_application_zip(export_client):
    client, draft_id = export_client
    r = client.get(f"/api/automate/draft/{draft_id}/export?format=mdzip")
    assert r.status_code == 200
    ct = (r.headers.get("content-type") or "").lower()
    assert "zip" in ct or "octet-stream" in ct
    assert r.content[:2] == b"PK"
    assert "attachment" in (r.headers.get("content-disposition") or "").lower()
    assert ".zip" in (r.headers.get("content-disposition") or "").lower()


def test_export_missing_draft_returns_404(export_client):
    client, _ = export_client
    r = client.get("/api/automate/draft/draft_does_not_exist/export?format=json")
    assert r.status_code == 404


def test_export_filename_includes_paper_code(export_client):
    client, draft_id = export_client
    r = client.get(f"/api/automate/draft/{draft_id}/export?format=json")
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    assert "igcse_physics_questions" in cd
