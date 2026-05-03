import asyncio
import base64
import json
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from content_gen.core.model_router import ModelRoutingEngine
from content_gen.core.config_schema import DetectionMode
from content_gen.core.pedagogy_engine import PedagogyEngine
from content_gen.scripts.pipeline.pipeline_orchestrator import PipelineOrchestrator


CANCELLATION_EVENTS: dict[str, threading.Event] = {}
METADATA_LOCK = threading.Lock()


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
    router: ModelRoutingEngine,
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
        router.config.model_routing.extraction = normalized
        router.config.model_routing.generation = normalized
        router.config.model_routing.validation = normalized
        return {
            "provider": requested_provider,
            "requested_model_id": requested_model_id,
            "resolved_model": normalized,
        }

    if requested_provider and has_api_key:
        defaults = _provider_default_models(requested_provider)
        if defaults:
            router.config.model_routing.extraction = defaults["extraction"]
            router.config.model_routing.generation = defaults["generation"]
            router.config.model_routing.validation = defaults["validation"]
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


def extract_correct_answer(explanation: str) -> str:
    match = re.search(r"Final Correct Answer\s*:\s*([A-D])", explanation or "", re.IGNORECASE)
    if match:
        return match.group(1).upper()
    # Fallback to looking for single letters at the end
    match_fallback = re.search(r"(?:Correct Answer|Answer is)\s*[:\s]*([A-D])", explanation or "", re.IGNORECASE)
    if match_fallback:
        return match_fallback.group(1).upper()
    return "N/A"


def extract_option_analysis(option_text: str, option_keys: list[str]) -> dict[str, str]:
    result = {k: "" for k in option_keys}
    if not option_text:
        return result
    pattern = re.compile(
        r"Option\s*([A-D])\s*:\s*(.*?)(?=Option\s*[A-D]\s*:|$)",
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(option_text):
        label = match.group(1).upper()
        if label in result:
            result[label] = re.sub(r"\s+", " ", match.group(2)).strip()
    return result


def extract_core_concept(explanation: str) -> str:
    if not explanation:
        return ""
    core_match = re.search(
        r"^\s*Core Concept\s*:?\s*(.*?)(?=\n\s*(?:Step\s*1|Analyze Step 1|Final Correct Answer|Option\s+[A-D]:)|$)",
        explanation,
        re.IGNORECASE | re.DOTALL | re.MULTILINE,
    )
    if core_match:
        content = re.sub(r"\s+", " ", core_match.group(1)).strip(" -*\n\t")
        if content:
            return content
    # Smarter fallback: first few sentences or first 300 chars (approx 5-6 lines)
    lines = [ln.strip() for ln in explanation.splitlines() if ln.strip()]
    if not lines:
        return ""
    
    # Try to get the first 2-3 sentences if possible
    full_text = " ".join(lines)
    sentences = re.split(r'(?<=[.!?])\s+', full_text)
    if len(sentences) > 0:
        concept = " ".join(sentences[:3])
        if len(concept) > 350:
            return concept[:347] + "..."
        return concept
        
    return full_text[:297] + "..."


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
            with METADATA_LOCK:
                with open(meta_path, "r") as f:
                    meta = json.load(f)
                
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
                
                with open(meta_path, "w") as f:
                    json.dump(meta, f)
        except Exception as e:
            print(f"Error updating progress: {e}")

    try:
        router = ModelRoutingEngine()
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
            router, llm_provider, model_id, has_api_key=(api_key is not None)
        )

        if api_key:
            os.environ["LITELLM_API_KEY"] = api_key

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
                                diagram_b64 = (
                                    f"data:image/png;base64,{base64.b64encode(img_f.read()).decode('utf-8')}"
                                )
                    except Exception as img_e:
                        print(f"Failed to encode diagram: {img_e}")

            explanation_text = q.explanation_body or ""
            option_text = q.option_wise_explanation or ""
            option_analysis = extract_option_analysis(option_text, list((q.options or {}).keys()))
            
            # Prioritize dedicated Core Concept from LLM
            core_concept = (q.metadata or {}).get("core_concept_generated")
            if not core_concept:
                core_concept = extract_core_concept(explanation_text)
                
            quality_report = (q.metadata or {}).get("generation_quality", {})

            # Normalize Correct Answer
            norm_correct_answer = (q.correct_options[0] if q.correct_options else extract_correct_answer(explanation_text)).strip().upper()
            if len(norm_correct_answer) > 1:
                norm_correct_answer = norm_correct_answer[0]
            if norm_correct_answer not in "ABCD":
                norm_correct_answer = "N/A"

            # Normalize Option Analysis keys
            final_option_analysis = {k: option_analysis.get(k, "Analysis missing for this option.") for k in ["A", "B", "C", "D"]}

            # Ensure Core Concept is not a duplicate of Detailed Explanation
            clean_core_concept = core_concept
            if clean_core_concept.lower() in explanation_text.lower() and len(clean_core_concept) > len(explanation_text) * 0.8:
                clean_core_concept = "Concept extracted from explanation."

            legacy_q = {
                "question_number": q.question_number,
                "text": q.question_text,
                "options": q.options,
                "correct_answer": norm_correct_answer,
                "status": "Draft",
                "diagram_base64": diagram_b64,
                "generated_content": {
                    "core_concept": clean_core_concept,
                    "detailed_explanation": explanation_text,
                    "option_analysis": final_option_analysis,
                    "flashcards": [{"question": f.front_text, "answer": f.back_text} for f in q.flashcards],
                },
                "quality_report": quality_report,
                "contract_warnings": [k for k, v in quality_report.items() if v is False],
            }
            questions_payload.append(legacy_q)

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

        with open(meta_path, "r") as f:
            final_meta = json.load(f)

        final_meta.update(
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

        with open(meta_path, "w") as f:
            json.dump(final_meta, f)

    except InterruptedError:
        print(f"Task {draft_id} cancelled.")
        _update_progress(0, "Processing stopped by user.")
        with open(meta_path, "r") as f:
            meta = json.load(f)
        meta["status"] = "FAILED"
        meta["status_message"] = "Stopped by user"
        with open(meta_path, "w") as f:
            json.dump(meta, f)
    except Exception as e:
        print(f"Background Processing Error: {e}")
        try:
            with open(meta_path, "r") as f:
                fail_meta = json.load(f)
            fail_meta.update(
                {
                    "status": "FAILED",
                    "error": str(e),
                    "progress": 0,
                    "status_message": f"Error: {str(e)}",
                }
            )
            with open(meta_path, "w") as f:
                json.dump(fail_meta, f)
        except Exception as inner_e:
            print(f"Failed to update metadata with error: {inner_e}")
