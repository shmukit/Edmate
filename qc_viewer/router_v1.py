from fastapi import APIRouter, HTTPException, UploadFile, File, Header, BackgroundTasks
from typing import Optional, List
import uuid
import json
import shutil
from pathlib import Path
from datetime import datetime

from content_gen.scripts.processing.automation_engine import AutomationEngine
from content_gen.core.schema import EdmateQuestion

router = APIRouter(prefix="/api/v1", tags=["Service API v1"])

# In-memory job store for the experimental run (use DB/Cache for production)
JOBS = {}

@router.post("/extract")
async def extract_content(
    background_tasks: BackgroundTasks,
    curriculum: str = "Cambridge O/Level",
    subject: str = "Chemistry",
    file: UploadFile = File(...),
    x_openai_key: Optional[str] = Header(None),
    x_gemini_key: Optional[str] = Header(None)
):
    """
    Experimental Service API: Extract Q&A from a document.
    Supports BYOK (Bring Your Own Key) via headers.
    """
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    
    # Setup temporary job directory
    tmp_root = Path(__file__).parent / "jobs"
    tmp_root.mkdir(exist_ok=True)
    job_dir = tmp_root / job_id
    job_dir.mkdir()
    
    file_path = job_dir / f"input_{file.filename}"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    JOBS[job_id] = {
        "status": "PROCESSING",
        "id": job_id,
        "subject": subject,
        "curriculum": curriculum,
        "created_at": datetime.now().isoformat()
    }
    
    # Run the processing in background
    background_tasks.add_task(
        process_service_job, 
        job_id, 
        str(file_path), 
        subject, 
        curriculum, 
        x_openai_key, 
        x_gemini_key
    )
    
    return {"job_id": job_id, "status": "PROCESSING"}

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return JOBS[job_id]

async def process_service_job(
    job_id: str, 
    file_path: str, 
    subject: str, 
    curriculum: str,
    openai_key: Optional[str],
    gemini_key: Optional[str]
):
    try:
        # Determine provider and key
        # For this experimental run, we prioritize Gemini as the default engine
        provider = "gemini"
        api_key = gemini_key

        if openai_key and not gemini_key:
            provider = "openai"
            api_key = openai_key

        # Initialize engine with BYOK
        engine = AutomationEngine(provider_or_subject=provider)
        if api_key:
            # Manually override api_key if provided by the user
            # We will refactor AutomationEngine to accept this properly in the next step
            engine.api_key = api_key
            if provider == "openai":
                from openai import OpenAI
                engine.client = OpenAI(api_key=api_key)
            else:
                from google import genai
                engine.client = genai.Client(api_key=api_key)

        # Execute processing
        config = {
            "curriculum": curriculum,
            "subject": subject
        }
        
        raw_results = engine.process_pdf(file_path, config=config)
        
        # Validate results against the Standard Schema
        validated_questions = []
        for q in raw_results.get("questions", []):
            try:
                # Map raw engine output to the standard schema
                # This bridge logic is key for Milestone B
                std_q = map_to_standard_schema(q, subject, curriculum)
                validated_questions.append(std_q)
            except Exception as e:
                print(f"Validation error for question: {e}")
                continue

        JOBS[job_id].update({
            "status": "COMPLETED",
            "questions": validated_questions,
            "completed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Job {job_id} failed: {e}")
        JOBS[job_id].update({
            "status": "FAILED",
            "error": str(e)
        })

def map_to_standard_schema(raw_q: dict, subject: str, curriculum: str) -> dict:
    """
    Bridge logic to convert heterogeneous engine output to Edmate Lab_QA v1.0.0 Schema.
    """
    gen_content = raw_q.get("generated_content", {})
    
    return {
        "$schema_version": "1.0.0",
        "metadata": {
            "curriculum": curriculum,
            "subject": subject,
            "topic": raw_q.get("topic_id", "General"),
            "difficulty": raw_q.get("difficulty_level", "Medium")
        },
        "question_text": raw_q.get("text", ""),
        "options": [
            {
                "id": k, 
                "text": v, 
                "is_correct": k == raw_q.get("correct_answer"), 
                "explanation": gen_content.get("option_analysis", {}).get(k, "")
            } 
            for k, v in raw_q.get("options", {}).items()
        ],
        "explanations": {
            "core_concept": gen_content.get("core_concept", ""),
            "detailed_logic": gen_content.get("detailed_explanation", ""),
            "final_answer_display": f"**Final Correct Answer: {raw_q.get('correct_answer', 'N/A')}**"
        },
        "flashcards": gen_content.get("flashcards", [])
    }
