from fastapi import APIRouter, HTTPException, UploadFile, File, Header, BackgroundTasks
from typing import Optional, List
import uuid
import json
import shutil
from pathlib import Path
from datetime import datetime

from content_gen.scripts.pipeline.pipeline_orchestrator import PipelineOrchestrator
from content_gen.core.model_router import ModelRoutingEngine
from content_gen.core.schemas import ProcessedQuestion
from qc_viewer.services.job_repository import get_job_repository

router = APIRouter(prefix="/api/v1", tags=["Service API v1"])

@router.post("/extract")
async def extract_content(
    background_tasks: BackgroundTasks,
    curriculum: str = "General",
    subject: str = "Chemistry",
    file: UploadFile = File(...),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
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
        
    get_job_repository().put(
        job_id,
        {
            "status": "PROCESSING",
            "id": job_id,
            "subject": subject,
            "curriculum": curriculum,
            "created_at": datetime.now().isoformat(),
        },
    )
    
    # Run the processing in background
    background_tasks.add_task(
        process_service_job, 
        job_id, 
        str(file_path), 
        subject, 
        curriculum, 
        x_api_key,
        x_openai_key, 
        x_gemini_key
    )
    
    return {"job_id": job_id, "status": "PROCESSING"}

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    row = get_job_repository().get(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return row

async def process_service_job(
    job_id: str, 
    file_path: str, 
    subject: str, 
    curriculum: str,
    api_key: Optional[str],
    openai_key: Optional[str],
    gemini_key: Optional[str]
):
    try:
        # Determine BYOK with neutral header first, then legacy provider headers.
        if not api_key:
            api_key = gemini_key or openai_key

        router = ModelRoutingEngine(api_key=api_key)
        orchestrator = PipelineOrchestrator(router=router)

        # Execute processing
        draft_dir = str(Path(file_path).parent)
        
        extracted = orchestrator.extractor.extract_content(Path(file_path), Path(draft_dir))
        generated_questions = orchestrator.generator.generate_for_questions(extracted, subject=subject)
        
        # Bridge the gap: Map the modular ProcessedQuestion model back to the legacy UI dictionary format
        validated_questions = []
        for q in generated_questions:
            legacy_q = {
                "question_number": q.question_number,
                "question_text": q.question_text,
                "options": q.options,
                "correct_answer": q.correct_options[0] if q.correct_options else "N/A",
                "explanations": {
                    "core_concept": q.explanation_body or "",
                    "detailed_logic": q.option_wise_explanation or ""
                },
                "flashcards": [f"{f.front_text}: {f.back_text}" for f in q.flashcards]
            }
            validated_questions.append(legacy_q)

        get_job_repository().merge(
            job_id,
            {
                "status": "COMPLETED",
                "questions": validated_questions,
                "completed_at": datetime.now().isoformat(),
            },
        )

    except Exception as e:
        print(f"Job {job_id} failed: {e}")
        get_job_repository().merge(
            job_id,
            {
                "status": "FAILED",
                "error": str(e),
            },
        )
