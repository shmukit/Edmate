import asyncio
import json
import shutil
import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse

from content_gen.core.model_router import ModelRoutingEngine
from content_gen.scripts.prompts import CONTENT_GENERATION_PROMPT_VERSION
from content_gen.scripts.processing.database_service import DatabaseService
from qc_viewer.config import DRAFTS_ROOT, is_publish_table_allowed
from qc_viewer.services.automation_pipeline import CANCELLATION_EVENTS, run_automation_pipeline
from pydantic import BaseModel
from qc_viewer.services import draft_export
from qc_viewer.services.draft_store import (
    ANONYMOUS_USER,
    DraftNotFound,
    delete_draft_data,
    ensure_drafts_root,
    get_draft_dir,
    is_draft_owned_by,
    list_draft_metadata,
    load_metadata_if_exists,
    read_json,
    resolve_metadata_path,
    sort_key_from_timestamp,
    write_json,
)


def _get_user_id(request: Request) -> str:
    """Extract user_id from request state (set by auth middleware)."""
    return getattr(request.state, "user_id", ANONYMOUS_USER)


def _require_draft_path(draft_id: str, user_id: Optional[str] = None) -> Path:
    try:
        return resolve_metadata_path(draft_id, user_id)
    except DraftNotFound:
        raise HTTPException(status_code=404, detail="Draft not found")


def _require_ownership(draft_id: str, user_id: str) -> None:
    """Raise 404 if the user does not own this draft."""
    if not is_draft_owned_by(draft_id, user_id):
        raise HTTPException(status_code=404, detail="Draft not found")


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
    request: Request,
    background_tasks: BackgroundTasks,
    subject: str = Form(...),
    paper_code: str = Form(...),
    file: UploadFile = File(...),
    curriculum: Optional[str] = Form(None),
    ls_profile: str = Form("default"),
    hia_mode: str = Form("Low"),
    min_question_number: Optional[int] = Form(None),
    max_question_number: Optional[int] = Form(None),
    question_detection_mode: Optional[str] = Form(None),
    x_llm_provider: Optional[str] = Header(None, alias="X-LLM-Provider"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_model_id: Optional[str] = Header(None, alias="X-Model-ID"),
):
    from qc_viewer.config import get_workspace_defaults

    user_id = _get_user_id(request)
    default_curriculum, _default_subject = get_workspace_defaults()
    curriculum_resolved = (curriculum or "").strip() or default_curriculum

    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    ensure_drafts_root()

    static_dir = get_draft_dir(draft_id, user_id)
    static_dir.mkdir(parents=True, exist_ok=True)

    file_path = static_dir / "source.pdf"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    write_json(
        static_dir / "metadata.json",
        {
            "id": draft_id,
            "owner_id": user_id,
            "pipeline_job_id": draft_id,
            "prompt_version": CONTENT_GENERATION_PROMPT_VERSION,
            "subject": subject,
            "paper_code": paper_code,
            "filename": file.filename,
            "curriculum": curriculum_resolved,
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
        curriculum_resolved,
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
async def list_drafts(request: Request):
    user_id = _get_user_id(request)
    drafts = list_draft_metadata(user_id)
    return sorted(drafts, key=sort_key_from_timestamp, reverse=True)


@router.get("/api/automate/draft/{draft_id}")
async def get_draft_results(request: Request, draft_id: str):
    user_id = _get_user_id(request)
    _require_ownership(draft_id, user_id)
    return read_json(_require_draft_path(draft_id, user_id))


@router.get("/api/automate/draft/{draft_id}/export")
async def export_draft(request: Request, draft_id: str, format: str = "json"):
    user_id = _get_user_id(request)
    _require_ownership(draft_id, user_id)
    fmt = format.lower()
    if fmt not in draft_export.SUPPORTED_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
    meta = read_json(_require_draft_path(draft_id, user_id))
    body = draft_export.render(meta, fmt)
    filename = draft_export.safe_filename(meta, fmt)
    return Response(
        content=body,
        media_type=draft_export.MEDIA_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/automate/draft/{draft_id}/stream")
async def stream_draft_progress(draft_id: str, request: Request):
    user_id = _get_user_id(request)
    try:
        meta_path = resolve_metadata_path(draft_id, user_id)
    except DraftNotFound:
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
async def stop_draft_processing(request: Request, draft_id: str):
    user_id = _get_user_id(request)
    _require_ownership(draft_id, user_id)
    if draft_id in CANCELLATION_EVENTS:
        CANCELLATION_EVENTS[draft_id].set()
        return {"status": "stopping"}

    meta = load_metadata_if_exists(draft_id, user_id)
    if meta and meta.get("status") == "PROCESSING":
        meta["status"] = "FAILED"
        meta["status_message"] = "Stopped by user"
        write_json(_require_draft_path(draft_id, user_id), meta)
        return {"status": "stopped"}

    return {"status": "not_running"}


@router.patch("/api/automate/draft/{draft_id}")
async def update_draft(request: Request, draft_id: str, updates: dict):
    user_id = _get_user_id(request)
    _require_ownership(draft_id, user_id)
    meta_path = _require_draft_path(draft_id, user_id)
    try:
        data = read_json(meta_path)
        data.update(updates)
        data["last_updated_at"] = datetime.now().isoformat()
        write_json(meta_path, data)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/automate/draft/{draft_id}")
async def delete_draft(request: Request, draft_id: str):
    user_id = _get_user_id(request)
    _require_ownership(draft_id, user_id)
    if delete_draft_data(draft_id, user_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Draft not found")


@router.post("/api/automate/publish")
async def publish_draft(request: PublishRequest):
    if not request.table_name or not request.question_data:
        raise HTTPException(status_code=400, detail="Missing table_name or question_data")
    if not is_publish_table_allowed(request.table_name):
        raise HTTPException(status_code=400, detail="Invalid table_name")

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

    active_drafts = 0
    if drafts_root.exists():
        for d in drafts_root.iterdir():
            if d.is_dir() and (d / "metadata.json").exists():
                try:
                    st = read_json(d / "metadata.json")
                    if st.get("status") == "PROCESSING":
                        active_drafts += 1
                except Exception:
                    continue

    return {
        "total_cost": total_cost,
        "total_tokens": total_tokens,
        "active_drafts": active_drafts,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/api/automate/config")
async def get_config():
    from pathlib import Path

    from content_gen.core.config_loader import ConfigLoader
    from qc_viewer.config import PROJECT_ROOT

    config_path = PROJECT_ROOT / "edmate_config.yaml"
    workspace_data: dict = {}
    budget_data: dict = {}
    extraction_settings: dict = {}
    model_routing: dict = {}
    kit_present = False

    try:
        ec = ConfigLoader.load_config(config_path if config_path.exists() else None)
        if hasattr(ec, "model_dump"):
            merged = ec.model_dump(mode="json")
        else:
            merged = json.loads(ec.json())  # type: ignore[attr-defined]
        workspace_data = merged.get("workspace") or {}
        budget_data = merged.get("budget") or {}
        extraction_settings = merged.get("extraction_settings") or {}
        model_routing = merged.get("model_routing") or {}
    except Exception as e:
        print(f"Error loading validated edmate_config: {e}")

    kit_path = Path(PROJECT_ROOT) / "content_gen" / "tools" / "PDF-Extract-Kit"
    kit_present = kit_path.is_dir() and (kit_path / "pdf_extract_kit").is_dir()

    engine = (extraction_settings.get("engine") or "vision").lower()
    extraction_hints: dict[str, str] = {}
    if engine == "pdf_extract_kit":
        extraction_hints["summary"] = (
            "Layout-aware extraction (diagrams supported when the kit is installed)."
        )
        if not kit_present:
            extraction_hints["warning"] = (
                "PDF-Extract-Kit directory not found under content_gen/tools/. "
                "Run scripts/setup_pdf_extract_kit.sh or set extraction_settings.engine to vision or pymupdf."
            )
    elif engine in ("vision", "multimodal"):
        extraction_hints["summary"] = (
            "Vision-based extraction (diagrams via LLM vision; uses API credits per page)."
        )
    elif engine == "pymupdf":
        extraction_hints["summary"] = (
            "Text-only extraction. Diagrams and raster figures are not captured."
        )

    return {
        "budget": {
            "max_daily_usd": float(budget_data.get("max_daily_usd", 10.0)),
            "current_usage_usd": 0.0,
        },
        "workspace": workspace_data,
        "model_routing": model_routing,
        "extraction_settings": extraction_settings,
        "kit_present": kit_present,
        "extraction_hints": extraction_hints,
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
        routing_engine.config.model_routing.generation = "openai/gpt-4o"
        refined = routing_engine.generate_content(prompt, task_type="generation")
        refined_question = dict(request.original_q)
        original_generated = refined_question.get("generated_content")
        generated_content = (
            dict(original_generated)
            if isinstance(original_generated, dict)
            else {}
        )
        generated_content["detailed_explanation"] = refined
        refined_question["generated_content"] = generated_content
        return {
            "explanation": refined,
            "refined_question": refined_question,
            "model": routing_engine.config.model_routing.generation,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
