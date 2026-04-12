import os
import re
import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from content_gen/.env
env_path = Path(__file__).parent.parent / "content_gen" / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="Edmate QC Viewer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

TABLES = [
    "chemistry_questions",
    "biology_questions",
    "physics_questions",
    "igcse_biology_questions",
    "igcse_chemistry_questions",
    "igcse_physics_questions",
]

def get_db():
    try:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor, connect_timeout=3)
    except Exception as e:
        print(f"DB connection error: {e}")
        return None


@app.get("/api/papers")
async def get_papers():
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    papers = []
    try:
        with conn.cursor() as cur:
            for table in TABLES:
                cur.execute(
                    f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')"
                )
                if not cur.fetchone()["exists"]:
                    continue
                # Extract paper code = question_identifier with trailing /Q<n> stripped
                cur.execute(
                    r"SELECT DISTINCT regexp_replace(question_identifier, '/Q?\d+$', '') AS code"
                    f" FROM {table} WHERE question_identifier IS NOT NULL"
                )
                for row in cur.fetchall():
                    code = row["code"]
                    if code:
                        papers.append({"code": code, "table": table})
    finally:
        conn.close()
    return sorted(papers, key=lambda x: x["code"])


@app.get("/api/questions")
async def get_questions(table: str, paper_code: str):
    if table not in TABLES:
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
                WHERE regexp_replace(question_identifier, '/Q?\d+$', '') = %s
                ORDER BY length(regexp_replace(question_identifier, '^.+/Q?', '')),
                         question_identifier
                """,
                (paper_code,),
            )
            return cur.fetchall()
    finally:
        conn.close()


@app.get("/api/flashcards")
async def get_flashcards(topic_id: str, subtopic_id: str = None, question_id: str = None):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor() as cur:
            # 1. Prioritize results for the specific question
            if question_id:
                cur.execute(
                    'SELECT id, "frontText", "backText" FROM flashcards'
                    ' WHERE "questionId" = %s AND "isActive" = true'
                    ' ORDER BY "id"',
                    (question_id,)
                )
                q_cards = cur.fetchall()
                if q_cards:
                    # Return cards with a metadata flag
                    for card in q_cards:
                        card['is_specific'] = True
                    return q_cards

            # 2. Fallback to topic-level results
            if subtopic_id:
                cur.execute(
                    'SELECT id, "frontText", "backText" FROM flashcards'
                    ' WHERE "topicId" = %s AND "subtopicId" = %s AND "isActive" = true'
                    ' AND "questionId" IS NULL'  # Prioritize generic ones for fallback
                    " ORDER BY \"createdAt\" LIMIT 20",
                    (topic_id, subtopic_id),
                )
            else:
                cur.execute(
                    'SELECT id, "frontText", "backText" FROM flashcards'
                    ' WHERE "topicId" = %s AND "isActive" = true'
                    ' AND "questionId" IS NULL'  # Prioritize generic ones for fallback
                    " ORDER BY \"createdAt\" LIMIT 20",
                    (topic_id,),
                )
            fallback_cards = cur.fetchall()
            for card in fallback_cards:
                card['is_specific'] = False
            return fallback_cards
    finally:
        conn.close()


@app.get("/api/stats")
async def get_stats():
    conn = get_db()
    if not conn:
        return {"error": "DB connection failed"}
    try:
        with conn.cursor() as cur:
            stats = {}
            for table in TABLES:
                cur.execute(
                    f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')"
                )
                if cur.fetchone()["exists"]:
                    cur.execute(f"SELECT count(*) FROM {table}")
                    stats[table] = cur.fetchone()["count"]
        return stats
    finally:
        conn.close()


# Serve static files (must be last)
app.mount("/", StaticFiles(directory="qc_viewer/static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
