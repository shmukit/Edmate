import asyncio
import base64
import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from content_gen.core.model_router import ModelRoutingEngine
from content_gen.core.pedagogy_engine import PedagogyEngine
from content_gen.scripts.pipeline.pipeline_orchestrator import PipelineOrchestrator


CANCELLATION_EVENTS: dict[str, asyncio.Event] = {}
METADATA_LOCK = threading.Lock()


def extract_correct_answer(explanation: str) -> str:
    match = re.search(r"Final Correct Answer\s*:\s*([A-D])", explanation or "", re.IGNORECASE)
    return match.group(1).upper() if match else "N/A"


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
        r"Core Concept\s*:?\s*(.*?)(?=\n\s*(?:Step\s*1|Analyze Step 1|Final Correct Answer|Option\s+[A-D]:)|$)",
        explanation,
        re.IGNORECASE | re.DOTALL,
    )
    if core_match:
        return re.sub(r"\s+", " ", core_match.group(1)).strip(" -*\n\t")
    first_line = next((ln.strip() for ln in explanation.splitlines() if ln.strip()), "")
    return first_line


async def run_automation_pipeline(
    draft_id: str,
    subject: str,
    paper_code: str,
    file_path: Path,
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
        if draft_id in CANCELLATION_EVENTS and CANCELLATION_EVENTS[draft_id].is_set():
            raise asyncio.CancelledError(f"Task {draft_id} was cancelled by user.")

        try:
            with METADATA_LOCK:
                with open(meta_path, "r") as f:
                    meta = json.load(f)
                meta.update(
                    {
                        "progress": progress,
                        "status_message": message,
                        "last_updated_at": datetime.now().isoformat(),
                    }
                )
                with open(meta_path, "w") as f:
                    json.dump(meta, f)
        except Exception as e:
            print(f"Error updating progress: {e}")

    try:
        pedagogy = PedagogyEngine(ls_profile=ls_profile, hia_mode=hia_mode, curriculum=curriculum)
        _ = pedagogy.compile_system_prompt()

        router = ModelRoutingEngine()
        valid_modes = {"strict", "balanced", "open"}
        requested_mode = (question_detection_mode or "").strip().lower()
        if requested_mode in valid_modes:
            router.config.question_detection_mode = requested_mode
        if min_question_number is not None:
            router.config.min_question_number = min_question_number
        if max_question_number is not None:
            router.config.max_question_number = max_question_number

        if api_key:
            os.environ["LITELLM_API_KEY"] = api_key

        orchestrator = PipelineOrchestrator(router=router)
        draft_dir = str(file_path.parent)

        _update_progress(15, "Starting AI-powered extraction pipeline...")

        questions_payload = []
        extracted = orchestrator.extractor.extract_content(
            file_path,
            Path(draft_dir),
            progress_callback=_update_progress,
        )
        print(f"DEBUG: Extracted {len(extracted)} questions from PDF.")

        _update_progress(60, "Applying Learning Science & Pedagogy Analysis...")

        generated = orchestrator.generator.generate_for_questions(
            extracted,
            subject=subject,
            progress_callback=_update_progress,
        )
        print(f"DEBUG: Generated content for {len(generated)} questions.")

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
            correct_answer = q.correct_options[0] if q.correct_options else extract_correct_answer(explanation_text)
            core_concept = extract_core_concept(explanation_text)
            quality_report = (q.metadata or {}).get("generation_quality", {})

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
                    "flashcards": [{"question": f.front_text, "answer": f.back_text} for f in q.flashcards],
                },
                "quality_report": quality_report,
            }
            questions_payload.append(legacy_q)

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
                "timestamp": datetime.now().isoformat(),
            }
        )

        with open(meta_path, "w") as f:
            json.dump(final_meta, f)

    except asyncio.CancelledError:
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
