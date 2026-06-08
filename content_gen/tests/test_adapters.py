import pytest
from unittest.mock import MagicMock, patch
import uuid
from content_gen.adapters.postgres_adapter import PostgresStorageAdapter
from content_gen.core.config_schema import EdmateConfig, WorkspaceConfig
from content_gen.core.schemas import ProcessedQuestion, Flashcard


def test_storage_adapter_save_question():
    """Verifies that the storage adapter correctly maps Pydantic to SQL."""
    # Mock the DB connection and cursor
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    # Initialize adapter with mocked connection
    empty_ws = EdmateConfig(workspace=WorkspaceConfig())
    with patch("content_gen.adapters.postgres_adapter.connect_real_dict", return_value=mock_conn):
        adapter = PostgresStorageAdapter(
            "postgres://user:pass@host:5432/db", edmate_config=empty_ws
        )
        # Overwrite the cur manually to be sure
        adapter.cur = mock_cur
        adapter.conn = mock_conn

    q = ProcessedQuestion(
        question_number=1,
        question_text="What is H2O?",
        options={"A": "Water", "B": "Salt"},
        correct_options=["A"],
        subject="Chemistry",
        explanation_body="It is water.",
        metadata={"subject_id": "123", "topic_id": "456", "difficulty": "Hard"}
    )

    q_id = adapter.save_question(q)
    assert uuid.UUID(q_id)

    # Verify that execute was called with correct SQL and params
    # We check the call args for the execute method
    call_args = mock_cur.execute.call_args[0]
    sql_query = call_args[0]
    params = call_args[1]

    assert "INSERT INTO chemistry_questions" in sql_query
    assert "What is H2O?" in params
    assert "Hard" in params  # Verified metadata mapping
    mock_conn.commit.assert_called()


def test_storage_adapter_save_flashcards():
    """Verifies that flashcards are saved correctly."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()

    empty_ws = EdmateConfig(workspace=WorkspaceConfig())
    with patch("content_gen.adapters.postgres_adapter.connect_real_dict", return_value=mock_conn):
        adapter = PostgresStorageAdapter(
            "postgres://user:pass@host:5432/db", edmate_config=empty_ws
        )
        adapter.cur = mock_cur
        adapter.conn = mock_conn

    fcs = [
        Flashcard(front_text="H", back_text="Hydrogen"),
        Flashcard(front_text="O", back_text="Oxygen")
    ]

    count = adapter.save_flashcards(
        fcs, {"subject_id": "sub123", "topic_id": "top456"})
    assert count == 2
    assert mock_cur.execute.call_count == 2
    mock_conn.commit.assert_called()
