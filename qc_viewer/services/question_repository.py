"""
PostgreSQL access for QC question/flashcard routes.

Routers validate HTTP; this module performs allowlisted table SQL only.
"""

from __future__ import annotations

from typing import Any, List, Optional, cast

from qc_viewer.config import get_allowed_table_ids


class QuestionRepository:
    """Read/write questions and related flashcards using allowlisted table names."""

    def list_papers(self, cur) -> List[dict[str, Any]]:
        papers: list[dict[str, Any]] = []
        for table in get_allowed_table_ids():
            cur.execute(
                f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')"
            )
            table_exists_row = cast(Optional[dict[str, Any]], cur.fetchone())
            if not table_exists_row or not table_exists_row["exists"]:
                continue
            cur.execute(
                r"SELECT DISTINCT regexp_replace(question_identifier, '/Q?\d+$', '') AS code"
                f" FROM {table} WHERE question_identifier IS NOT NULL"
            )
            for row in cast(list[dict[str, Any]], cur.fetchall()):
                code = row["code"]
                if code:
                    papers.append({"code": code, "table": table})
        return sorted(papers, key=lambda x: x["code"])

    def fetch_questions_for_paper(self, cur, table: str, paper_code: str) -> list:
        self.assert_table_allowed(table)
        cur.execute(
            r"""
            SELECT id, question_identifier,
                   regexp_replace(question_identifier, '^.+/Q?', '') AS question_number,
                   title, options,
                   correct_options, option_explanations,
                   summary_explanation, detailed_explanation,
                   is_verified, other_contents AS diagrams,
                   topic_id, subtopic_id
            FROM """
            + table
            + r"""
            WHERE question_identifier LIKE %s
            ORDER BY question_identifier;
            """,
            (paper_code + "%",),
        )
        return cur.fetchall()

    def set_question_verified(self, cur, table: str, question_id: str, is_verified: bool) -> None:
        self.assert_table_allowed(table)
        cur.execute(
            f"UPDATE {table} SET is_verified = %s, updated_at = NOW() WHERE id = %s",
            (is_verified, question_id),
        )

    def fetch_flashcards(
        self,
        cur,
        topic_id: Optional[str] = None,
        subtopic_id: Optional[str] = None,
        question_id: Optional[str] = None,
    ) -> list:
        if question_id and question_id != "undefined":
            cur.execute('SELECT * FROM flashcards WHERE "questionId" = %s', (question_id,))
            res = cur.fetchall()
            if res:
                return res

        if subtopic_id and subtopic_id not in ("undefined", "null"):
            cur.execute('SELECT * FROM flashcards WHERE "subtopicId" = %s', (subtopic_id,))
            res = cur.fetchall()
            if res:
                return res

        if topic_id and topic_id not in ("undefined", "null"):
            cur.execute('SELECT * FROM flashcards WHERE "topicId" = %s', (topic_id,))
            return cur.fetchall()

        return []

    def fetch_question_details_row(self, cur, table: str, question_identifier: str):
        self.assert_table_allowed(table)
        cur.execute(
            "SELECT id, title, options, is_verified FROM " + table + " WHERE question_identifier = %s",
            (question_identifier,),
        )
        return cur.fetchone()

    def assert_table_allowed(self, table: str) -> None:
        if table not in get_allowed_table_ids():
            raise ValueError("Invalid table name")
