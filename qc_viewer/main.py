import os
from typing import Any, Optional, cast
import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Form, Header
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv
import shutil
import json
import uuid
import base64
import re
import asyncio
from datetime import datetime

# Import local services
from content_gen.core.model_router import ModelRoutingEngine
from content_gen.scripts.pipeline.pipeline_orchestrator import PipelineOrchestrator
from content_gen.scripts.processing.database_service import DatabaseService
from content_gen.core.pedagogy_engine import PedagogyEngine
from .router_v1 import router as api_v1_router

# Load environment variables from content_gen/.env
env_path = Path(__file__).parent.parent / "content_gen" / ".env"
load_dotenv(dotenv_path=env_path)

# Global for tracking cancellation of background tasks
CANCELLATION_EVENTS: dict[str, asyncio.Event] = {}

app = FastAPI(title="Edmate Lab_QA Service")

app.include_router(api_v1_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Clean URL Navigation (Prioritized)
@app.get("/")
async def serve_root():
    static_path = Path(__file__).resolve().parent / "static" / "index.html"
    if not static_path.exists():
         raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(static_path)

@app.get("/automate")
async def serve_hub():
    static_path = Path(__file__).resolve().parent / "static" / "automate.html"
    if not static_path.exists():
         raise HTTPException(status_code=404, detail="automate.html not found")
    return FileResponse(static_path)

@app.get("/analytics")
async def serve_analytics():
    static_path = Path(__file__).resolve().parent / "static" / "analytics.html"
    if not static_path.exists():
         raise HTTPException(status_code=404, detail="analytics.html not found")
    return FileResponse(static_path)

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
                table_exists_row = cast(Optional[dict[str, Any]], cur.fetchone())
                if not table_exists_row or not table_exists_row["exists"]:
                    continue
                # Extract paper code = question_identifier with trailing /Q<n> stripped
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
async def get_flashcards(topic_id: Optional[str] = None, subtopic_id: Optional[str] = None, question_id: Optional[str] = None):
    conn = get_db()
    if not conn:
        raise HTTPException(
            status_code=500, detail="Database connection failed")
    try:
        with conn.cursor() as cur:
            # 1. Try Question-specific cards first
            if question_id and question_id != 'undefined':
                cur.execute('SELECT * FROM flashcards WHERE "questionId" = %s', (question_id,))
                res = cur.fetchall()
                if res:
                    return res

            # 2. Try Subtopic cards
            if subtopic_id and subtopic_id != 'undefined' and subtopic_id != 'null':
                cur.execute('SELECT * FROM flashcards WHERE "subtopicId" = %s', (subtopic_id,))
                res = cur.fetchall()
                if res: return res
                
            # 3. Try Topic cards
            if topic_id and topic_id != 'undefined' and topic_id != 'null':
                cur.execute('SELECT * FROM flashcards WHERE "topicId" = %s', (topic_id,))
                return cur.fetchall()

            # 4. Fallback (Empty instead of random bulk)
            return []
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
    file: UploadFile = File(...),
    curriculum: str = Form("Cambridge O/Level"),
    ls_profile: str = Form("default"),
    hia_mode: str = Form("Low"),
    min_question_number: Optional[int] = Form(None),
    max_question_number: Optional[int] = Form(None),
    question_detection_mode: Optional[str] = Form(None),
    x_llm_provider: Optional[str] = Header(None, alias="X-LLM-Provider"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_model_id: Optional[str] = Header(None, alias="X-Model-ID"),
):
    """
    Receives a PDF and kicks off the background automation pipeline.
    Supports BYOK via X-API-Key / X-LLM-Provider / X-Model-ID headers.
    Falls back to .env keys if headers are not provided (self-hosted mode).
    Returns a draft ID so the frontend can poll for progress.
    """
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    drafts_root = Path(__file__).parent / "drafts"
    drafts_root.mkdir(parents=True, exist_ok=True)
    
    static_dir = drafts_root / draft_id
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
            "filename": file.filename,
            "curriculum": curriculum,
            "ls_profile": ls_profile,
            "hia_mode": hia_mode,
            "extraction_overrides": {
                "min_question_number": min_question_number,
                "max_question_number": max_question_number,
                "question_detection_mode": question_detection_mode,
            },
            "llm_provider": x_llm_provider or "env-default",
            "status": "PROCESSING",
            "progress": 10,
            "timestamp": datetime.now().isoformat()
        }, f)

    # Initialize cancellation event
    CANCELLATION_EVENTS[draft_id] = asyncio.Event()

    background_tasks.add_task(
        run_automation_pipeline,
        draft_id, subject, paper_code, file_path,
        curriculum, ls_profile, hia_mode,
        x_llm_provider, x_api_key, x_model_id,
        min_question_number, max_question_number, question_detection_mode
    )

    return {"id": draft_id, "filename": file.filename, "status": "PROCESSING"}


async def run_automation_pipeline(
    draft_id: str, subject: str, paper_code: str, file_path: Path,
    curriculum: str = "Cambridge O/Level",
    ls_profile: str = "default",
    hia_mode: str = "Low",
    llm_provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model_id: Optional[str] = None,
    min_question_number: Optional[int] = None,
    max_question_number: Optional[int] = None,
    question_detection_mode: Optional[str] = None,
):
    """Heavy lifting background task. Supports BYOK and PedagogyEngine."""
    meta_path = file_path.parent / "metadata.json"

    def _update_progress(progress: int, message: str):
        # Check for cancellation before updating
        if draft_id in CANCELLATION_EVENTS and CANCELLATION_EVENTS[draft_id].is_set():
            raise asyncio.CancelledError(f"Task {draft_id} was cancelled by user.")

        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
            meta.update({
                "progress": progress,
                "status_message": message,
                "last_updated_at": datetime.now().isoformat()
            })
            with open(meta_path, "w") as f:
                json.dump(meta, f)
        except Exception as e:
            print(f"Error updating progress: {e}")

    def _extract_correct_answer(explanation: str) -> str:
        match = re.search(r'Final Correct Answer\s*:\s*([A-D])', explanation or "", re.IGNORECASE)
        return match.group(1).upper() if match else "N/A"

    def _extract_option_analysis(option_text: str, option_keys: list[str]) -> dict[str, str]:
        result = {k: "" for k in option_keys}
        if not option_text:
            return result
        pattern = re.compile(
            r'Option\s*([A-D])\s*:\s*(.*?)(?=Option\s*[A-D]\s*:|$)',
            re.IGNORECASE | re.DOTALL
        )
        for match in pattern.finditer(option_text):
            label = match.group(1).upper()
            if label in result:
                result[label] = re.sub(r'\s+', ' ', match.group(2)).strip()
        return result

    def _extract_core_concept(explanation: str) -> str:
        if not explanation:
            return ""
        core_match = re.search(
            r'Core Concept\s*:?\s*(.*?)(?=\n\s*(?:Step\s*1|Analyze Step 1|Final Correct Answer|Option\s+[A-D]:)|$)',
            explanation,
            re.IGNORECASE | re.DOTALL
        )
        if core_match:
            return re.sub(r'\s+', ' ', core_match.group(1)).strip(" -*\n\t")
        first_line = next((ln.strip() for ln in explanation.splitlines() if ln.strip()), "")
        return first_line

    try:
        # Build pedagogical system prompt from selected profile
        pedagogy = PedagogyEngine(ls_profile=ls_profile, hia_mode=hia_mode, curriculum=curriculum)
        system_prompt = pedagogy.compile_system_prompt()

        # Initialize the modular PipelineOrchestrator
        router = ModelRoutingEngine()
        valid_modes = {"strict", "balanced", "open"}
        requested_mode = (question_detection_mode or "").strip().lower()
        if requested_mode in valid_modes:
            router.config.question_detection_mode = requested_mode
        if min_question_number is not None:
            router.config.min_question_number = min_question_number
        if max_question_number is not None:
            router.config.max_question_number = max_question_number
        
        # Inject BYOK overrides if provided
        if api_key:
            os.environ["LITELLM_API_KEY"] = api_key # Fallback if provider isn't explicit
            
        orchestrator = PipelineOrchestrator(router=router)
        draft_dir = str(file_path.parent)
        
        # Phase 1: Extraction
        _update_progress(15, "Starting AI-powered extraction pipeline...")
        
        questions_payload = []
        extracted = orchestrator.extractor.extract_content(
            file_path, 
            Path(draft_dir), 
            progress_callback=_update_progress
        )
        print(f"DEBUG: Extracted {len(extracted)} questions from PDF.")

        # Phase 2: Generation
        _update_progress(60, "Applying Learning Science & Pedagogy Analysis...")
        
        generated = orchestrator.generator.generate_for_questions(
            extracted, 
            subject=subject,
            progress_callback=_update_progress
        )
        print(f"DEBUG: Generated content for {len(generated)} questions.")
        
        total_questions = len(generated)
        for i, q in enumerate(generated):
            # Update progress for each question
            processed_count = i + 1
            progress_val = 90 + int((processed_count / total_questions) * 9) # Final polish phase
            
            _update_progress(progress_val, f"Finalizing question {processed_count} of {total_questions}...")

            # Handle diagram extraction/encoding
            diagram_b64 = None
            stem_images = q.metadata.get("stem_images", [])
            stem_images_b64 = q.metadata.get("stem_images_b64", [])
            if stem_images_b64:
                diagram_b64 = stem_images_b64[0]
            if stem_images and len(stem_images) > 0:
                first_img = stem_images[0]
                if diagram_b64:
                    pass
                elif str(first_img).startswith("data:image"):
                    diagram_b64 = first_img
                else:
                    try:
                        img_path = Path(first_img)
                        if img_path.exists():
                            with open(img_path, "rb") as img_f:
                                diagram_b64 = f"data:image/png;base64,{base64.b64encode(img_f.read()).decode('utf-8')}"
                    except Exception as img_e:
                        print(f"Failed to encode diagram: {img_e}")

            explanation_text = q.explanation_body or ""
            option_text = q.option_wise_explanation or ""
            option_analysis = _extract_option_analysis(option_text, list((q.options or {}).keys()))
            correct_answer = q.correct_options[0] if q.correct_options else _extract_correct_answer(explanation_text)
            core_concept = _extract_core_concept(explanation_text)
            quality_report = (q.metadata or {}).get("generation_quality", {})

            # Map to the exact schema review.js expects
            legacy_q = {
                "question_number": q.question_number,
                "text": q.question_text,
                "options": q.options,
                "correct_answer": correct_answer,
                "status": "Draft",
                "diagram_base64": diagram_b64,
                "generated_content": {
                    "core_concept": core_concept,
                    "detailed_explanation": explanation_text,
                    "option_analysis": option_analysis,
                    "flashcards": [{"question": f.front_text, "answer": f.back_text} for f in q.flashcards]
                },
                "quality_report": quality_report
            }
            questions_payload.append(legacy_q)

        # Load existing meta to preserve filename
        with open(meta_path, "r") as f:
            final_meta = json.load(f)

        final_meta.update({
            "questions": questions_payload,
            "status": "PROCESSED",
            "progress": 100,
            "processed_count": total_questions,
            "total_count": total_questions,
            "status_message": "Generation complete!",
            "id": draft_id,
            "subject": subject,
            "paper_code": paper_code,
            "pedagogy_profile": pedagogy.get_profile_summary(),
            "timestamp": datetime.now().isoformat()
        })

        with open(meta_path, "w") as f:
            json.dump(final_meta, f)

    except asyncio.CancelledError:
        print(f"Task {draft_id} cancelled.")
        _update_progress(0, "Processing stopped by user.")
        with open(meta_path, "r") as f:
            meta = json.load(f)
        meta["status"] = "FAILED" # Or "CANCELLED"
        meta["status_message"] = "Stopped by user"
        with open(meta_path, "w") as f:
            json.dump(meta, f)
    except Exception as e:
        print(f"Background Processing Error: {e}")
        try:
            with open(meta_path, "r") as f:
                fail_meta = json.load(f)
            fail_meta.update({
                "status": "FAILED",
                "error": str(e),
                "progress": 0,
                "status_message": f"Error: {str(e)}"
            })
            with open(meta_path, "w") as f:
                json.dump(fail_meta, f)
        except Exception as inner_e:
            print(f"Failed to update metadata with error: {inner_e}")


@app.get("/api/automate/drafts")
async def list_drafts():
    """Returns all current drafts with sorted timestamps"""
    drafts = []
    drafts_root = Path(__file__).parent / "drafts"
    if not drafts_root.exists():
        return []

    for d in drafts_root.iterdir():
        # New directory-based structure
        if d.is_dir() and (d / "metadata.json").exists():
            try:
                with open(d / "metadata.json", "r") as f:
                    drafts.append(json.load(f))
            except Exception:
                continue
        # Old flat JSON structure (compatibility)
        elif d.suffix == ".json" and d.name != "metadata.json":
            try:
                with open(d, "r") as f:
                    data = json.load(f)
                    if "id" in data:
                        drafts.append(data)
            except Exception:
                continue

    # Convert timestamps for sorting (handles both floats and ISO strings)
    def get_time(x):
        ts = x.get("timestamp") or x.get("created_at") or ""
        if not ts: return 0.0
        try:
             # Try float first (old format)
             return float(ts)
        except (ValueError, TypeError):
             # Try ISO string
             try:
                 from datetime import datetime
                 return datetime.fromisoformat(ts).timestamp()
             except:
                 return 0.0

    return sorted(drafts, key=get_time, reverse=True)


@app.get("/api/automate/draft/{draft_id}")
async def get_draft_results(draft_id: str):
    # Try new structure first
    meta_path = Path(__file__).parent / "drafts" / draft_id / "metadata.json"
    
    # Try legacy structure second
    if not meta_path.exists():
        legacy_path = Path(__file__).parent / "drafts" / f"{draft_id}.json"
        if legacy_path.exists():
            meta_path = legacy_path

    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Draft not found")

    with open(meta_path, "r") as f:
        return json.load(f)


@app.get("/api/automate/draft/{draft_id}/stream")
async def stream_draft_progress(draft_id: str):
    """
    Server-Sent Events (SSE) endpoint to stream draft progress updates.
    """
    meta_path = Path(__file__).parent / "drafts" / draft_id / "metadata.json"
    
    if not meta_path.exists():
        # Legacy fallback
        meta_path = Path(__file__).parent / "drafts" / f"{draft_id}.json"

    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Draft not found")

    async def event_generator():
        last_meta = None
        while True:
            try:
                if not meta_path.exists():
                    break
                    
                with open(meta_path, "r") as f:
                    current_meta = json.load(f)
                
                # Only stream if metadata has changed meaningfully
                current_summary = {
                    "progress": current_meta.get("progress"),
                    "status": current_meta.get("status"),
                    "status_message": current_meta.get("status_message"),
                    "processed_count": current_meta.get("processed_count")
                }
                
                if current_summary != last_meta:
                    last_meta = current_summary
                    yield f"data: {json.dumps(current_meta)}\n\n"
                
                if current_meta.get("status") in ["PROCESSED", "FAILED"]:
                    break
                    
                await asyncio.sleep(0.5) # Poll the file every 500ms
            except Exception as e:
                print(f"Streaming error: {e}")
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/automate/draft/{draft_id}/stop")
async def stop_draft_processing(draft_id: str):
    """Signals a background task to stop."""
    if draft_id in CANCELLATION_EVENTS:
        CANCELLATION_EVENTS[draft_id].set()
        return {"status": "stopping"}
    
    # Check if it's already failed or processed
    meta_path = Path(__file__).parent / "drafts" / draft_id / "metadata.json"
    if meta_path.exists():
        with open(meta_path, "r") as f:
            meta = json.load(f)
        if meta.get("status") == "PROCESSING":
             meta["status"] = "FAILED"
             meta["status_message"] = "Stopped by user"
             with open(meta_path, "w") as f:
                 json.dump(meta, f)
             return {"status": "stopped"}
             
    return {"status": "not_running"}


@app.patch("/api/automate/draft/{draft_id}")
async def update_draft(draft_id: str, updates: dict):
    # Try new structure first
    meta_path = Path(__file__).parent / "drafts" / draft_id / "metadata.json"
    
    # Try legacy structure second
    if not meta_path.exists():
        legacy_path = Path(__file__).parent / "drafts" / f"{draft_id}.json"
        if legacy_path.exists():
            meta_path = legacy_path

    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Draft not found")

    try:
        with open(meta_path, "r") as f:
            data = json.load(f)
        
        # Merge updates
        data.update(updates)
        data["last_updated_at"] = datetime.now().isoformat()

        with open(meta_path, "w") as f:
            json.dump(data, f)
        
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/automate/draft/{draft_id}")
async def delete_draft(draft_id: str):
    # Modern directory-based structure
    draft_dir = Path(__file__).parent / "drafts" / draft_id
    if draft_dir.is_dir():
        shutil.rmtree(draft_dir)
        return {"status": "deleted"}

    # Legacy flat JSON structure
    legacy_json = Path(__file__).parent / "drafts" / f"{draft_id}.json"
    legacy_pdf = Path(__file__).parent / "drafts" / f"{draft_id}.pdf"
    
    if legacy_json.exists():
        legacy_json.unlink()
        if legacy_pdf.exists():
            legacy_pdf.unlink()
        return {"status": "deleted"}

    raise HTTPException(status_code=404, detail="Draft not found")


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


@app.get("/api/automate/metrics")
async def get_metrics():
    """Returns aggregate metrics for the automation pipeline"""
    # In a real app, this would query a metrics table. 
    # For now, we'll calculate from existing drafts.
    drafts_root = Path(__file__).parent / "static" / "drafts"
    total_cost = 0.0
    total_tokens = 0
    
    if drafts_root.exists():
        for d in drafts_root.iterdir():
            if d.is_dir() and (d / "metadata.json").exists():
                try:
                    with open(d / "metadata.json", "r") as f:
                        data = json.load(f)
                        total_cost += data.get("total_cost", 0)
                        total_tokens += data.get("total_tokens", 0)
                except Exception:
                    continue
                    
    return {
        "total_cost": total_cost,
        "total_tokens": total_tokens,
        "active_drafts": 5, # Placeholder
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/automate/config")
async def get_config():
    """Returns pipeline configuration and budget limits"""
    return {
        "budget": {
            "max_daily_usd": 10.0,
            "current_usage_usd": 1.25
        },
        "model": "gpt-4o",
        "vision_enabled": True
    }


@app.post("/api/automate/refine")
async def refine_explanation(feedback: str, original_q: str):
    if not feedback or not original_q:
        raise HTTPException(
            status_code=400, detail="Missing feedback or original_q")

    router = ModelRoutingEngine()
    prompt = f"Original Question and Explanation:\n{original_q}\n\nUser Feedback:\n{feedback}\n\nPlease refine the explanation to address the feedback. Keep the tone educational and clear."

    try:
        refined = router.generate_content(prompt, task_type="generation")
        return {
            "explanation": refined,
            "model": router.config.generation_model,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Static Fallback Mount 
# This allows relative paths like css/viewer.css to work from clean URLs
docs_path = Path(__file__).resolve().parent.parent / "docs" / "pedagogy"
if docs_path.exists():
    app.mount("/docs", StaticFiles(directory=str(docs_path)), name="docs")

app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
