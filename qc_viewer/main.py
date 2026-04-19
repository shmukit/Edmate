import os
import re
import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Optional
import shutil
import json
import uuid

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


# ───── AUTOMATION ENDPOINTS ─────

# Setup robust paths
BASE_DIR = Path(__file__).parent
DRAFTS_DIR = (BASE_DIR / "drafts").resolve()
DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

print(f"🚀 Edmate Automation Hub Initialized")
print(f"📂 Drafts Directory: {DRAFTS_DIR}")

# Mount static files once at root for everything else
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import FileResponse
    favicon_path = BASE_DIR / "static" / "favicon.svg"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/svg+xml")
    return None

@app.get("/api/debug/paths")
async def debug_paths():
    import os
    return {
        "DRAFTS_DIR": str(DRAFTS_DIR),
        "exists": DRAFTS_DIR.exists(),
        "files": os.listdir(DRAFTS_DIR) if DRAFTS_DIR.exists() else []
    }

@app.post("/api/automate/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Uploads a PDF and creates a draft record"""
    draft_id = str(uuid.uuid4())
    save_path = DRAFTS_DIR / f"{draft_id}.pdf"
    
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Create initial draft entry
    draft_meta = {
        "id": draft_id,
        "filename": file.filename,
        "status": "UPLOADED",
        "created_at": str(shutil.os.path.getctime(save_path))
    }
    
    with open(DRAFTS_DIR / f"{draft_id}.json", "w") as f:
        json.dump(draft_meta, f)
        
    return draft_meta

@app.post("/api/automate/process/{draft_id}")
async def process_draft(draft_id: str, background_tasks: BackgroundTasks, config: dict = None):
    """Triggers Modular AI extraction for a specific draft"""
    pdf_path = DRAFTS_DIR / f"{draft_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Draft PDF not found")
        
    if config is None:
        config = {
            "provider": "gemini",
            "model_id": "gemini-2.0-flash",
            "modalities": ["core_concept", "detailed_explanation", "option_analysis", "flashcards"],
            "language": "English",
            "curriculum": "Cambridge O/Level"
        }
        
    # Update status to PROCESSING immediately
    meta_path = DRAFTS_DIR / f"{draft_id}.json"
    with open(meta_path, "r") as f:
        meta = json.load(f)
    
    meta.update({"status": "PROCESSING", "progress": 0})
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    # Launch background task
    background_tasks.add_task(run_extraction_task, draft_id, str(pdf_path), config)
    
    return meta

def run_extraction_task(draft_id: str, pdf_path: str, config: dict):
    """Background task for PDF processing with progress updates"""
    meta_path = DRAFTS_DIR / f"{draft_id}.json"
    
    def progress_callback(percent: float):
        try:
            with open(meta_path, "r") as f:
                data = json.load(f)
            data["progress"] = round(percent, 2)
            with open(meta_path, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Callback error: {e}")

    try:
        engine = AutomationEngine(
            provider=config.get("provider", "gemini"),
            model_id=config.get("model_id")
        )
        questions = engine.process_pdf(pdf_path, config, progress_callback=progress_callback)
        
        with open(meta_path, "r") as f:
            results = json.load(f)

        results.update({
            "status": "PROCESSED",
            "questions": questions,
            "config": config,
            "progress": 100,
            "processed_at": str(uuid.uuid4())
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
        except:
            pass

@app.get("/api/automate/drafts")
async def list_drafts():
    """Returns all current drafts with sorted timestamps"""
    drafts = []
    for f in DRAFTS_DIR.glob("*.json"):
        try:
            with open(f, "r") as json_file:
                drafts.append(json.load(json_file))
        except Exception as e:
            print(f"Error reading draft {f}: {e}")
    # Sort by created_at descending
    return sorted(drafts, key=lambda x: float(x.get("created_at", 0)), reverse=True)

@app.get("/api/automate/drafts/{draft_id}")
async def get_draft(draft_id: str):
    """Returns a specific draft including questions"""
    meta_path = DRAFTS_DIR / f"{draft_id}.json"
    if not meta_path.exists():
        print(f"Draft 404: {meta_path} does not exist")
        raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
    with open(meta_path, "r") as f:
        return json.load(f)

@app.delete("/api/automate/drafts/{draft_id}")
async def delete_draft(draft_id: str):
    """Deletes a draft PDF and JSON record"""
    pdf_path = DRAFTS_DIR / f"{draft_id}.pdf"
    json_path = DRAFTS_DIR / f"{draft_id}.json"
    
    if pdf_path.exists(): pdf_path.unlink()
    if json_path.exists(): json_path.unlink()
    
    return {"status": "success", "message": f"Draft {draft_id} deleted"}

@app.patch("/api/automate/drafts/{draft_id}")
async def update_draft(draft_id: str, updates: dict):
    """Updates draft metadata or question data (e.g., status, admin edits)"""
    meta_path = DRAFTS_DIR / f"{draft_id}.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Draft not found")
        
    with open(meta_path, "r") as f:
        data = json.load(f)
    
    # Merge updates
    for key, value in updates.items():
        if key == "questions" and isinstance(value, list):
            data["questions"] = value
        else:
            data[key] = value
            
    data["last_reviewed_at"] = str(shutil.os.path.getmtime(meta_path))
    
    with open(meta_path, "w") as f:
        json.dump(data, f)
        
    return data

@app.post("/api/automate/inject")
async def inject_question(payload: dict):
    """Injects a verified question into the specified subject table"""
    table_name = payload.get("table_name")
    q_data = payload.get("question_data")
    
    if not table_name or not q_data:
        raise HTTPException(status_code=400, detail="Missing table_name or question_data")
        
    db = DatabaseService()
    try:
        db.inject_question(table_name, q_data)
        return {"status": "success", "message": f"Question injected into {table_name}"}
    except Exception as e:
        print(f"Injection API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/automate/refine")
async def refine_question(payload: dict):
    """AI endpoint to refine a specific question based on admin feedback"""
    feedback = payload.get("feedback")
    original_q = payload.get("original_q")
    
    if not feedback or not original_q:
        raise HTTPException(status_code=400, detail="Missing feedback or original_q")
    
    try:
        engine = AutomationEngine(provider="gemini")
        prompt = f"""
        You are an educational editor. Refine the following question content based on the user feedback.
        USER FEEDBACK: {feedback}
        ORIGINAL CONTENT:
        {json.dumps(original_q)}
        Maintain the same JSON structure. Return ONLY the refined JSON object for this ONE question.
        """
        # Call the engine's internal call_llm if available or direct client
        # For simplicity and correctness with current main.py structure:
        response = engine.client.models.generate_content(
            model=engine.model_id,
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        refined_q = json.loads(response.text)
        return {"status": "success", "refined_question": refined_q}
    except Exception as e:
        print(f"Refinement Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount logic at the end to catch all main UI requests
app.mount("/", StaticFiles(directory=BASE_DIR / "static", html=True), name="static_root")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
