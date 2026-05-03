from typing import Any, Optional, cast

from fastapi import APIRouter, HTTPException

from qc_viewer.config import get_allowed_table_ids
from qc_viewer.services.db_service import get_db


router = APIRouter()


@router.get("/api/papers")
async def get_papers():
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    papers = []
    try:
        with conn.cursor() as cur:
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
    finally:
        conn.close()
    return sorted(papers, key=lambda x: x["code"])


@router.get("/api/questions")
async def get_questions(table: str, paper_code: str):
    if table not in get_allowed_table_ids():
        raise HTTPException(status_code=400, detail="Invalid table name")
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor() as cur:
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
    finally:
        conn.close()


@router.post("/api/verify")
async def verify_question(table: str, question_id: str, is_verified: bool):
    if table not in get_allowed_table_ids():
        raise HTTPException(status_code=400, detail="Invalid table name")
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {table} SET is_verified = %s, updated_at = NOW() WHERE id = %s",
                (is_verified, question_id),
            )
            conn.commit()
            return {"status": "success"}
    finally:
        conn.close()


@router.get("/api/flashcards")
async def get_flashcards(
    topic_id: Optional[str] = None,
    subtopic_id: Optional[str] = None,
    question_id: Optional[str] = None,
):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor() as cur:
            if question_id and question_id != "undefined":
                cur.execute('SELECT * FROM flashcards WHERE "questionId" = %s', (question_id,))
                res = cur.fetchall()
                if res:
                    return res

            if subtopic_id and subtopic_id != "undefined" and subtopic_id != "null":
                cur.execute('SELECT * FROM flashcards WHERE "subtopicId" = %s', (subtopic_id,))
                res = cur.fetchall()
                if res:
                    return res

            if topic_id and topic_id != "undefined" and topic_id != "null":
                cur.execute('SELECT * FROM flashcards WHERE "topicId" = %s', (topic_id,))
                return cur.fetchall()

            return []
    finally:
        conn.close()


@router.get("/api/question/details")
async def get_question_details(table: str, question_identifier: str):
    if table not in get_allowed_table_ids():
        raise HTTPException(status_code=400, detail="Invalid table name")
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor() as cur:
            query = "SELECT id, title, options, is_verified FROM " + table + " WHERE question_identifier = %s"
            cur.execute(query, (question_identifier,))
            return cur.fetchone()
    finally:
        conn.close()
