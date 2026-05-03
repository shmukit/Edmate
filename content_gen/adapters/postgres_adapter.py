import re
import psycopg2
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from .base import BaseStorageAdapter
from ..core.schemas import ProcessedQuestion, Flashcard
from ..core.config_loader import ConfigLoader
from ..core.config_schema import EdmateConfig


class PostgresStorageAdapter(BaseStorageAdapter):
    """
    Concrete implementation of Edmate storage for the private 
    PostgreSQL schema used in the Edmate ecosystem.
    """

    _IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    def __init__(self, connection_string: str, edmate_config: Optional[EdmateConfig] = None):
        self.conn_str = connection_string
        self.conn = psycopg2.connect(connection_string)
        self.cur = self.conn.cursor()
        self._workspace = (edmate_config or ConfigLoader.load_config()).workspace

    @staticmethod
    def initialize_schema(connection_string: str, edmate_config: Optional[EdmateConfig] = None):
        """
        Creates the necessary database tables for Edmate if they do not exist.
        Table names come from edmate_config workspace.target_tables when set;
        otherwise a legacy Cambridge-style multi-table set is created for backward compatibility.
        """
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()
        try:
            # Shared tables
            cur.execute("""
                CREATE TABLE IF NOT EXISTS flashcards (
                    id UUID PRIMARY KEY,
                    "subjectId" TEXT,
                    "topicId" TEXT,
                    "subtopicId" TEXT,
                    "frontText" TEXT,
                    "backText" TEXT,
                    "isActive" BOOLEAN DEFAULT true,
                    "createdAt" TIMESTAMP DEFAULT NOW()
                );
            """)

            cfg = edmate_config or ConfigLoader.load_config()
            tables = [
                t.id for t in cfg.workspace.target_tables
                if PostgresStorageAdapter._IDENTIFIER_RE.match(t.id)
            ]
            if not tables:
                tables = [
                    "chemistry_questions", "biology_questions", "physics_questions",
                    "igcse_biology_questions", "igcse_chemistry_questions", "igcse_physics_questions",
                ]
            for table in tables:
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        id UUID PRIMARY KEY,
                        title TEXT,
                        type TEXT DEFAULT 'MCQ',
                        difficulty_level TEXT,
                        source TEXT DEFAULT 'PastPaper',
                        subject_id TEXT,
                        topic_id TEXT,
                        subtopic_id TEXT,
                        options TEXT[],
                        correct_options TEXT[],
                        option_explanations TEXT[],
                        detailed_explanation TEXT,
                        summary_explanation TEXT,
                        question_identifier TEXT UNIQUE,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        is_active BOOLEAN DEFAULT true,
                        is_verified BOOLEAN DEFAULT false
                    );
                """)
            conn.commit()
            print("✅ Database schema initialized successfully.")
        finally:
            cur.close()
            conn.close()

    def _allowed_table_ids(self) -> List[str]:
        return [
            t.id for t in self._workspace.target_tables
            if self._IDENTIFIER_RE.match(t.id)
        ]

    def _get_table_name(self, question: ProcessedQuestion) -> str:
        allowed = self._allowed_table_ids()
        tid = question.metadata.get("target_table_id")
        if isinstance(tid, str) and tid in allowed:
            return tid
        if allowed:
            return allowed[0]
        # Legacy routing when workspace.target_tables is empty
        subject = question.subject
        grade = question.metadata.get("grade", "A-Level")
        mapping = {
            ("Biology", "A-Level"): "biology_questions",
            ("Chemistry", "A-Level"): "chemistry_questions",
            ("Physics", "A-Level"): "physics_questions",
            ("Biology", "IGCSE"): "igcse_biology_questions",
            ("Chemistry", "IGCSE"): "igcse_chemistry_questions",
            ("Physics", "IGCSE"): "igcse_physics_questions",
        }
        return mapping.get((subject, grade), "questions")

    def save_question(self, question: ProcessedQuestion) -> str:
        table = self._get_table_name(question)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        q_id = str(uuid.uuid4())

        # Mapping Pydantic model to legacy SQL columns
        self.cur.execute(
            f"""
            INSERT INTO {table} (
                id, title, type, difficulty_level, source,
                subject_id, topic_id,
                options, correct_options, option_explanations,
                detailed_explanation, summary_explanation,
                question_identifier, created_at, updated_at,
                is_active, is_verified
            )
            VALUES (%s,%s,%s,%s,%s, %s,%s, %s,%s,%s, %s,%s, %s, %s,%s, %s,%s)
            RETURNING id;
            """,
            (
                q_id,
                question.question_text,
                "MCQ",
                question.metadata.get("difficulty", "Medium"),
                "PastPaper",
                question.metadata.get("subject_id"),
                question.metadata.get("topic_id"),
                list(question.options.values()),
                question.correct_options,
                [question.option_wise_explanation],  # Simplifying for legacy
                question.explanation_body,
                question.explanation_body[:500] if question.explanation_body else None,
                question.paper_code or f"GEN_{q_id}",
                now, now, True, True
            )
        )
        self.conn.commit()
        return q_id

    def save_flashcards(self, flashcards: List[Flashcard], context: Dict[str, Any]) -> int:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        count = 0
        for fc in flashcards:
            self.cur.execute(
                """
                INSERT INTO flashcards (id, "subjectId", "topicId", "frontText", "backText", "isActive", "createdAt")
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    context.get("subject_id"),
                    context.get("topic_id"),
                    fc.front_text,
                    fc.back_text,
                    True,
                    now
                )
            )
            count += 1
        self.conn.commit()
        return count

    def get_question(self, question_id: str) -> Optional[ProcessedQuestion]:
        # Implementation for retrieval if needed
        return None

    def resolve_metadata(self, hint: str, type: str) -> Optional[str]:
        # Logical mapping for subject/topic IDs
        return hint  # Simplified for this modular placeholder
