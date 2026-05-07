from typing import Optional

from fastapi import APIRouter, HTTPException

from qc_viewer.services.db_service import get_db
from qc_viewer.services.question_repository import QuestionRepository

router = APIRouter()
_question_repo = QuestionRepository()


@router.get("/api/papers")
async def get_papers():
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor() as cur:
            return _question_repo.list_papers(cur)
    finally:
        conn.close()


@router.get("/api/questions")
async def get_questions(table: str, paper_code: str):
    try:
        _question_repo.assert_table_allowed(table)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid table name")
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor() as cur:
            return _question_repo.fetch_questions_for_paper(cur, table, paper_code)
    finally:
        conn.close()


@router.post("/api/verify")
async def verify_question(table: str, question_id: str, is_verified: bool):
    try:
        _question_repo.assert_table_allowed(table)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid table name")
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor() as cur:
            _question_repo.set_question_verified(cur, table, question_id, is_verified)
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
            return _question_repo.fetch_flashcards(cur, topic_id, subtopic_id, question_id)
    finally:
        conn.close()


@router.get("/api/question/details")
async def get_question_details(table: str, question_identifier: str):
    try:
        _question_repo.assert_table_allowed(table)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid table name")
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor() as cur:
            return _question_repo.fetch_question_details_row(cur, table, question_identifier)
    finally:
        conn.close()
