import asyncio
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol

from content_gen.core.model_router import ModelRoutingEngine


class _MutableModelRouting(Protocol):
    """Assignable routing slots (real :class:`ModelRouting` or test doubles)."""

    extraction: str
    generation: str
    validation: str
from content_gen.core.config_schema import DetectionMode
from content_gen.core.pedagogy_engine import PedagogyEngine
from content_gen.scripts.pipeline.pipeline_orchestrator import PipelineOrchestrator
from qc_viewer.services.draft_store import read_modify_write_json
from qc_viewer.services.legacy_question_payload import build_legacy_question_dict


CANCELLATION_EVENTS: dict[str, threading.Event] = {}


def _normalize_model_id(model_id: str, provider: Optional[str]) -> str:
    """Normalize model identifiers into litellm's provider/model format when possible."""
    model = (model_id or "").strip()
    if not model:
        return model
    if "/" in model:
        return model
    if provider:
        return f"{provider.strip().lower()}/{model}"
    return model


def _provider_default_models(provider: str) -> dict[str, str]:
    p = provider.strip().lower()
    if p == "gemini":
        # Keep defaults fast/cheap for interactive pipeline runs.
        return {
            "extraction": "vertex_ai/gemini-2.5-flash",
            "generation": "vertex_ai/gemini-2.5-flash",
            "validation": "vertex_ai/gemini-2.5-flash",
        }
    if p == "openai":
        return {
            "extraction": "openai/gpt-4o-mini",
            "generation": "openai/gpt-4o-mini",
            "validation": "openai/gpt-4o-mini",
        }
    if p == "anthropic":
        return {
            "extraction": "anthropic/claude-3-5-haiku-latest",
            "generation": "anthropic/claude-3-5-haiku-latest",
            "validation": "anthropic/claude-3-5-haiku-latest",
        }
    return {}


def _apply_runtime_model_overrides(
    model_routing: _MutableModelRouting,
    llm_provider: Optional[str],
    model_id: Optional[str],
    has_api_key: bool = False,
) -> dict[str, Optional[str]]:
    """
    Apply per-request model override precedence:
      1) explicit model id
      2) provider default model family
      3) existing config from edmate_config.yaml
    """
    requested_provider = (llm_provider or "").strip().lower() or None
    requested_model_id = (model_id or "").strip() or None

    if requested_model_id:
        normalized = _normalize_model_id(requested_model_id, requested_provider)
        model_routing.extraction = normalized
        model_routing.generation = normalized
        model_routing.validation = normalized
        return {
            "provider": requested_provider,
            "requested_model_id": requested_model_id,
            "resolved_model": normalized,
        }

    if requested_provider and has_api_key:
        defaults = _provider_default_models(requested_provider)
        if defaults:
            model_routing.extraction = defaults["extraction"]
            model_routing.generation = defaults["generation"]
            model_routing.validation = defaults["validation"]
            return {
                "provider": requested_provider,
                "requested_model_id": None,
                "resolved_model": defaults["generation"],
            }

    return {
        "provider": requested_provider,
        "requested_model_id": requested_model_id,
        "resolved_model": None,
    }


def run_automation_pipeline(
    draft_id: str,
    subject: str,
    paper_code: str,
    file_path: Path,
    curriculum: Optional[str] = None,
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

    def _update_progress(progress: int, message: str, processed_count: Optional[int] = None, total_count: Optional[int] = None):
        if draft_id in CANCELLATION_EVENTS and CANCELLATION_EVENTS[draft_id].is_set():
            raise InterruptedError(f"Task {draft_id} was cancelled by user.")

        try:
            def _mut(meta: dict) -> None:
                update_data = {
                    "progress": progress,
                    "status_message": message,
                    "last_updated_at": datetime.now().isoformat(),
                }
                if processed_count is not None:
                    update_data["processed_count"] = processed_count
                if total_count is not None:
                    update_data["total_count"] = total_count
                meta.update(update_data)

            read_modify_write_json(meta_path, _mut)
        except Exception as e:
            print(f"Error updating progress: {e}")

    try:
        router = ModelRoutingEngine(api_key=api_key)
        if curriculum is None or not str(curriculum).strip():
            curriculum = (
                (router.config.workspace.default_curriculum or "").strip() or "General"
            )

        pedagogy = PedagogyEngine(ls_profile=ls_profile, hia_mode=hia_mode, curriculum=curriculum)
        pedagogy_system_prompt = pedagogy.compile_system_prompt()

        valid_modes = {"strict", "balanced", "open"}
        requested_mode = (question_detection_mode or "").strip().lower()
        if requested_mode in valid_modes:
            router.config.extraction_settings.question_detection_mode = DetectionMode(
                requested_mode
            )
        if min_question_number is not None:
            router.config.extraction_settings.min_question_number = min_question_number
        if max_question_number is not None:
            router.config.extraction_settings.max_question_number = max_question_number

        resolved_model_override = _apply_runtime_model_overrides(
            router.config.model_routing,
            llm_provider,
            model_id,
            has_api_key=(api_key is not None),
        )

        orchestrator = PipelineOrchestrator(router=router)
        draft_dir = str(file_path.parent)

        _update_progress(15, "Starting AI-powered extraction pipeline...")

        t_pipeline_start = time.time()
        
        t_extraction_start = time.time()
        questions_payload = []
        extracted = orchestrator.extractor.extract_content(
            file_path,
            Path(draft_dir),
            progress_callback=_update_progress,
        )
        t_extraction_end = time.time()
        print(f"DEBUG: Extracted {len(extracted)} questions from PDF in {t_extraction_end - t_extraction_start:.2f}s.")

        _update_progress(60, "Applying Learning Science & Pedagogy Analysis...", processed_count=0, total_count=len(extracted))

        t_generation_start = time.time()
        generated = orchestrator.generator.generate_for_questions(
            extracted,
            subject=subject,
            curriculum=curriculum,
            progress_callback=_update_progress,
            pedagogy_system_prompt=pedagogy_system_prompt,
        )
        t_generation_end = time.time()
        print(f"DEBUG: Generated content for {len(generated)} questions in {t_generation_end - t_generation_start:.2f}s.")

        t_normalization_start = time.time()
        total_questions = len(generated)
        for i, q in enumerate(generated):
            processed_count = i + 1
            progress_val = 90 + int((processed_count / total_questions) * 9)
            _update_progress(progress_val, f"Finalizing question {processed_count} of {total_questions}...")
            questions_payload.append(build_legacy_question_dict(q))

        t_normalization_end = time.time()
        t_pipeline_end = time.time()
        
        telemetry = {
            "total_time_sec": round(t_pipeline_end - t_pipeline_start, 2),
            "nodes": {
                "extraction_sec": round(t_extraction_end - t_extraction_start, 2),
                "generation_sec": round(t_generation_end - t_generation_start, 2),
                "normalization_sec": round(t_normalization_end - t_normalization_start, 2),
            }
        }

        def _finalize(meta: dict) -> None:
            meta.update(
                {
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
                    "resolved_model_override": resolved_model_override,
                    "completed_at": datetime.now().isoformat(),
                    "telemetry": telemetry,
                }
            )

        read_modify_write_json(meta_path, _finalize)

    except InterruptedError:
        print(f"Task {draft_id} cancelled.")
        try:
            read_modify_write_json(
                meta_path,
                lambda m: m.update(
                    {
                        "progress": 0,
                        "status_message": "Processing stopped by user.",
                        "status": "FAILED",
                    }
                ),
            )
        except Exception as inner_e:
            print(f"Failed to update metadata after cancel: {inner_e}")
    except Exception as e:
        error_str = str(e)
        print(f"Background Processing Error: {error_str}")
        try:

            def _fail(meta: dict) -> None:
                meta.update(
                    {
                        "status": "FAILED",
                        "error": error_str,
                        "progress": 0,
                        "status_message": f"Error: {error_str}",
                    }
                )

            read_modify_write_json(meta_path, _fail)
        except Exception as inner_e:
            print(f"Failed to update metadata with error: {inner_e}")
