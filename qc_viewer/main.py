import os
import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv
import shutil
import json
import uuid
from datetime import datetime

# Import local services
from content_gen.scripts.processing.automation_engine import AutomationEngine
from content_gen.scripts.processing.database_service import DatabaseService

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
        raise HTTPException(
            status_code=500, detail="Database connection failed")
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
        raise HTTPException(
            status_code=500, detail="Database connection failed")
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


@app.post("/api/verify")
async def verify_question(table: str, question_id: str, is_verified: bool):
    if table not in TABLES:
        raise HTTPException(status_code=400, detail="Invalid table name")
    conn = get_db()
    if not conn:
        raise HTTPException(
            status_code=500, detail="Database connection failed")
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


@app.get("/api/flashcards")
async def get_flashcards(topic_id: str = None, subtopic_id: str = None):
    conn = get_db()
    if not conn:
        raise HTTPException(
            status_code=500, detail="Database connection failed")
    try:
        with conn.cursor() as cur:
            if subtopic_id:
                cur.execute(
                    'SELECT * FROM flashcards WHERE "subtopicId" = %s', (subtopic_id,))
            elif topic_id:
                cur.execute(
                    'SELECT * FROM flashcards WHERE "topicId" = %s', (topic_id,))
            else:
                cur.execute("SELECT * FROM flashcards LIMIT 100")
            return cur.fetchall()
    finally:
        conn.close()


@app.get("/api/question/details")
async def get_question_details(table: str, question_identifier: str):
    if table not in TABLES:
        raise HTTPException(status_code=400, detail="Invalid table name")
    conn = get_db()
    if not conn:
        raise HTTPException(
            status_code=500, detail="Database connection failed")
    try:
        with conn.cursor() as cur:
            # Fix F541: Removed 'f' prefix from simple string addition
            query = "SELECT id, title, options, is_verified FROM " + table + " WHERE question_identifier = %s"
            cur.execute(query, (question_identifier,))
            return cur.fetchone()
    finally:
        conn.close()


@app.post("/api/automate/draft")
async def receive_draft(
    background_tasks: BackgroundTasks,
    subject: str = Form(...),
    paper_code: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Receives a PDF and kicks off the background automation pipeline.
    Returns a draft ID so the frontend can poll for progress.
    """
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    static_dir = Path(__file__).parent / "static" / "drafts" / draft_id
    static_dir.mkdir(parents=True, exist_ok=True)

    file_path = static_dir / "source.pdf"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Initial metadata
    with open(static_dir / "metadata.json", "w") as f:
        json.dump({
            "id": draft_id,
            "subject": subject,
            "paper_code": paper_code,
            "status": "EXTRACTING",
            "timestamp": datetime.now().isoformat()
        }, f)

    background_tasks.add_task(run_automation_pipeline,
                              draft_id, subject, paper_code, file_path)

    return {"draft_id": draft_id}


async def run_automation_pipeline(draft_id: str, subject: str, paper_code: str, file_path: Path):
    """Heavy lifting background task"""
    meta_path = file_path.parent / "metadata.json"
    try:
        engine = AutomationEngine(subject)
        results = engine.process_pdf(str(file_path), str(file_path.parent))

        results.update({
            "status": "REVIEW_READY",
            "id": draft_id,
            "subject": subject,
            "paper_code": paper_code,
            "timestamp": datetime.now().isoformat()
        })

        with open(meta_path, "w") as f:
            json.dump(results, f)

    except Exception as e:
        print(f"Background Processing Error: {e}")
        try:
            with open(meta_path, "r") as f:
                data = json.load(f)
            data.update({"status": "FAILED", "error": str(e)})
            with open(meta_path, "w") as f:
                json.dump(data, f)
        except Exception:
            pass


@app.get("/api/automate/drafts")
async def list_drafts():
    """Returns all current drafts with sorted timestamps"""
    draft_ids = []
    drafts_root = Path(__file__).parent / "static" / "drafts"
    if not drafts_root.exists():
        return []

    for d in drafts_root.iterdir():
        if d.is_dir() and (d / "metadata.json").exists():
            with open(d / "metadata.json", "r") as f:
                drafts_root.append(json.load(f))

    return sorted(drafts_root, key=lambda x: x.get("timestamp", ""), reverse=True)


@app.get("/api/automate/draft/{draft_id}")
async def get_draft_results(draft_id: str):
    meta_path = Path(__file__).parent / "static" / \
        "drafts" / draft_id / "metadata.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Draft not found")

    with open(meta_path, "r") as f:
        return json.load(f)


@app.post("/api/automate/publish")
async def publish_draft(draft_id: str, table_name: str, question_data: dict):
    if not table_name or not question_data:
        raise HTTPException(
            status_code=400, detail="Missing table_name or question_data")

    db = DatabaseService()
    try:
        success = db.inject_question(table_name, question_data)
        return {"status": "success" if success else "failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/automate/refine")
async def refine_explanation(feedback: str, original_q: str):
    if not feedback or not original_q:
        raise HTTPException(
            status_code=400, detail="Missing feedback or original_q")

    engine = AutomationEngine("Chemistry")  # Default or dynamic
    try:
        refined = engine.refine_explanation(original_q, feedback)
        return {
            "explanation": refined,
            "model": engine.model_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.mount("/static", StaticFiles(directory=Path(__file__).parent /
          "static", html=True), name="static_root")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
