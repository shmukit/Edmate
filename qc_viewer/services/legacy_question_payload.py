"""
Pure helpers: map pipeline ProcessedQuestion → legacy QC viewer JSON.

Used by automation_pipeline and tests; no I/O.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from content_gen.core.media_encoding import png_file_to_data_uri
from content_gen.core.schemas import ProcessedQuestion


def extract_correct_answer(explanation: str) -> str:
    match = re.search(r"Final Correct Answer\s*:\s*([A-D])", explanation or "", re.IGNORECASE)
    if match:
        return match.group(1).upper()
    match_fallback = re.search(
        r"(?:Correct Answer|Answer is)\s*[:\s]*([A-D])", explanation or "", re.IGNORECASE
    )
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
    lines = [ln.strip() for ln in explanation.splitlines() if ln.strip()]
    if not lines:
        return ""

    full_text = " ".join(lines)
    sentences = re.split(r"(?<=[.!?])\s+", full_text)
    if len(sentences) > 0:
        concept = " ".join(sentences[:3])
        if len(concept) > 350:
            return concept[:347] + "..."
        return concept

    return full_text[:297] + "..."


def resolve_diagram_data_uri(q: ProcessedQuestion) -> Optional[str]:
    """Return a data:image PNG URI for the first stem diagram, if any."""
    md = q.metadata or {}
    stem_images_b64 = md.get("stem_images_b64", [])
    if stem_images_b64:
        return stem_images_b64[0]
    stem_images = md.get("stem_images", [])
    if not stem_images:
        return None
    first_img = stem_images[0]
    if str(first_img).startswith("data:image"):
        return str(first_img)
    try:
        img_path = Path(first_img)
        if img_path.exists():
            return png_file_to_data_uri(img_path)
    except OSError:
        pass
    return None


def build_legacy_question_dict(q: ProcessedQuestion) -> Dict[str, Any]:
    """Single QC-viewer question record after extraction + generation."""
    diagram_b64 = resolve_diagram_data_uri(q)

    explanation_text = q.explanation_body or ""
    option_text = q.option_wise_explanation or ""
    option_keys = list((q.options or {}).keys()) or ["A", "B", "C", "D"]
    option_analysis = extract_option_analysis(option_text, option_keys)

    core_concept = (q.metadata or {}).get("core_concept_generated")
    if not core_concept:
        core_concept = extract_core_concept(explanation_text)

    quality_report = (q.metadata or {}).get("generation_quality", {})

    norm_correct_answer = (
        q.correct_options[0] if q.correct_options else extract_correct_answer(explanation_text)
    ).strip().upper()
    if len(norm_correct_answer) > 1:
        norm_correct_answer = norm_correct_answer[0]
    if norm_correct_answer not in "ABCD":
        norm_correct_answer = "N/A"

    final_option_analysis = {
        k: option_analysis.get(k, "Analysis missing for this option.") for k in ["A", "B", "C", "D"]
    }

    clean_core_concept = core_concept
    if (
        clean_core_concept
        and explanation_text
        and clean_core_concept.lower() in explanation_text.lower()
        and len(clean_core_concept) > len(explanation_text) * 0.8
    ):
        clean_core_concept = "Concept extracted from explanation."

    opts_map = q.options if isinstance(q.options, dict) else {}
    opt_vals = [str(opts_map.get(k, "") or "").strip() for k in ("A", "B", "C", "D")]
    non_empty_opts = sum(1 for v in opt_vals if v)
    extraction_warnings: List[str] = ["mcq_options_missing"] if non_empty_opts < 2 else []

    legacy_q: Dict[str, Any] = {
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
    if extraction_warnings:
        legacy_q["extraction_warnings"] = extraction_warnings
    return legacy_q
