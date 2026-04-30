import asyncio
import json
import shutil
import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from content_gen.core.model_router import ModelRoutingEngine
from content_gen.scripts.processing.database_service import DatabaseService
from qc_viewer.config import DRAFTS_ROOT
from qc_viewer.services.automation_pipeline import CANCELLATION_EVENTS, run_automation_pipeline
from pydantic import BaseModel
from qc_viewer.services.draft_store import (
    delete_draft_data,
    ensure_drafts_root,
    get_draft_dir,
    load_metadata_if_exists,
    read_json,
    resolve_metadata_path,
    sort_key_from_timestamp,
    write_json,
)


class PublishRequest(BaseModel):
    draft_id: str
    table_name: str
    question_data: dict


class RefineRequest(BaseModel):
    feedback: str
    original_q: dict


router = APIRouter()


@router.post("/api/automate/draft")
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
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    ensure_drafts_root()

    static_dir = get_draft_dir(draft_id)
    static_dir.mkdir(parents=True, exist_ok=True)

    file_path = static_dir / "source.pdf"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    write_json(
        static_dir / "metadata.json",
        {
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
            "timestamp": datetime.now().isoformat(),
        },
    )

    CANCELLATION_EVENTS[draft_id] = threading.Event()

    background_tasks.add_task(
        run_automation_pipeline,
        draft_id,
        subject,
        paper_code,
        file_path,
        curriculum,
        ls_profile,
        hia_mode,
        x_llm_provider,
        x_api_key,
        x_model_id,
        min_question_number,
        max_question_number,
        question_detection_mode,
    )

    return {"id": draft_id, "filename": file.filename, "status": "PROCESSING"}


@router.get("/api/automate/drafts")
async def list_drafts():
    drafts = []
    if not DRAFTS_ROOT.exists():
        return []

    for d in DRAFTS_ROOT.iterdir():
        if d.is_dir() and (d / "metadata.json").exists():
            try:
                drafts.append(read_json(d / "metadata.json"))
            except Exception:
                continue
        elif d.suffix == ".json" and d.name != "metadata.json":
            try:
                data = read_json(d)
                if "id" in data:
                    drafts.append(data)
            except Exception:
                continue

    return sorted(drafts, key=sort_key_from_timestamp, reverse=True)


@router.get("/api/automate/draft/{draft_id}")
async def get_draft_results(draft_id: str):
    return read_json(resolve_metadata_path(draft_id))


@router.get("/api/automate/draft/{draft_id}/stream")
async def stream_draft_progress(draft_id: str, request: Request):
    try:
        meta_path = resolve_metadata_path(draft_id)
    except HTTPException:
        meta_path = DRAFTS_ROOT / draft_id / "metadata.json"
        if not meta_path.exists():
            meta_path = DRAFTS_ROOT / f"{draft_id}.json"

    async def event_generator():
        last_meta_str = ""
        while True:
            if await request.is_disconnected():
                print(f"SSE client disconnected: {draft_id}")
                break

            try:
                if not meta_path.exists():
                    yield f"data: {json.dumps({'status': 'INITIALIZING', 'progress': 5})}\n\n"
                    await asyncio.sleep(1)
                    continue

                current_meta = read_json(meta_path)
                current_meta_str = json.dumps(current_meta)
                if current_meta_str != last_meta_str:
                    yield f"data: {current_meta_str}\n\n"
                    last_meta_str = current_meta_str

                if current_meta.get("status") in ["PROCESSED", "FAILED", "PUBLISHED"]:
                    break

                await asyncio.sleep(0.5)
            except GeneratorExit:
                break
            except Exception as e:
                print(f"Streaming error for {draft_id}: {e}")
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/api/automate/draft/{draft_id}/stop")
async def stop_draft_processing(draft_id: str):
    if draft_id in CANCELLATION_EVENTS:
        CANCELLATION_EVENTS[draft_id].set()
        return {"status": "stopping"}

    meta = load_metadata_if_exists(draft_id)
    if meta and meta.get("status") == "PROCESSING":
        meta["status"] = "FAILED"
        meta["status_message"] = "Stopped by user"
        write_json(resolve_metadata_path(draft_id), meta)
        return {"status": "stopped"}

    return {"status": "not_running"}


@router.patch("/api/automate/draft/{draft_id}")
async def update_draft(draft_id: str, updates: dict):
    meta_path = resolve_metadata_path(draft_id)
    try:
        data = read_json(meta_path)
        data.update(updates)
        data["last_updated_at"] = datetime.now().isoformat()
        write_json(meta_path, data)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/automate/draft/{draft_id}")
async def delete_draft(draft_id: str):
    if delete_draft_data(draft_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Draft not found")


@router.post("/api/automate/publish")
async def publish_draft(request: PublishRequest):
    if not request.table_name or not request.question_data:
        raise HTTPException(status_code=400, detail="Missing table_name or question_data")

    db = DatabaseService()
    try:
        success = db.inject_question(request.table_name, request.question_data)
        return {"status": "success" if success else "failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/automate/metrics")
async def get_metrics():
    drafts_root = Path(__file__).resolve().parent.parent / "static" / "drafts"
    total_cost = 0.0
    total_tokens = 0

    if drafts_root.exists():
        for d in drafts_root.iterdir():
            if d.is_dir() and (d / "metadata.json").exists():
                try:
                    data = read_json(d / "metadata.json")
                    total_cost += data.get("total_cost", 0)
                    total_tokens += data.get("total_tokens", 0)
                except Exception:
                    continue

    return {
        "total_cost": total_cost,
        "total_tokens": total_tokens,
        "active_drafts": 5,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/api/automate/config")
async def get_config():
    import yaml
    from qc_viewer.config import PROJECT_ROOT

    config_path = PROJECT_ROOT / "edmate_config.yaml"
    workspace_data = {}
    
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                data = yaml.safe_load(f)
                workspace_data = data.get("workspace", {})
        except Exception as e:
            print(f"Error loading edmate_config.yaml: {e}")

    return {
        "budget": {
            "max_daily_usd": 10.0,
            "current_usage_usd": 1.25,
        },
        "workspace": workspace_data,
        "model": "gpt-4o",
        "vision_enabled": True,
    }


@router.post("/api/automate/refine")
async def refine_explanation(request: RefineRequest):
    if not request.feedback or not request.original_q:
        raise HTTPException(status_code=400, detail="Missing feedback or original_q")

    routing_engine = ModelRoutingEngine()
    prompt = (
        "Original Question and Explanation:\n"
        f"{json.dumps(request.original_q, indent=2)}\n\n"
        "User Feedback:\n"
        f"{request.feedback}\n\n"
        "Please refine the explanation to address the feedback. Keep the tone educational and clear."
    )

    try:
        # For refinement, we want a more capable model
        routing_engine.config.generation_model = "openai/gpt-4o"
        refined = routing_engine.generate_content(prompt, task_type="generation")
        return {
            "explanation": refined,
            "model": routing_engine.config.generation_model,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
