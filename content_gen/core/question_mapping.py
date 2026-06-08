"""
Boundary mappers between pipeline models and public / export DTOs.

**Canonical pipeline model:** :class:`content_gen.core.schemas.ProcessedQuestion`
  — produced by PDF extraction + :class:`content_gen.scripts.processing.content_generator.ContentGenerator`.
  Field names are oriented to processing (``question_text``, ``options`` as ``dict[str, str]``,
  ``Flashcard`` with ``front_text`` / ``back_text``).

**Export / API sketch:** :class:`content_gen.core.schema.EdmateQuestion`
  — structured Lab_QA JSON with nested ``Metadata``, ``Option`` list, ``Explanations``, etc.
  Use when emitting versioned JSON for external consumers.

Do not merge the two modules into one model in a single step; map at the edges only.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from content_gen.core.schema import (
    EdmateQuestion,
    Explanations,
    Flashcard as ExportFlashcard,
    Metadata,
    Option,
)
from content_gen.core.schemas import Flashcard as PipelineFlashcard, ProcessedQuestion


def processed_question_to_edmate_question(
    q: ProcessedQuestion,
    *,
    curriculum: str = "General",
    topic: str = "General",
) -> EdmateQuestion:
    """
    Best-effort map from pipeline output to :class:`EdmateQuestion`.

    Unknown fields use safe defaults so the object validates.
    """
    opts_in = q.options or {}
    letters = ("A", "B", "C", "D")
    correct = {str(c).upper() for c in (q.correct_options or []) if c}
    options_list: List[Option] = []
    for label in letters:
        text = str(opts_in.get(label, "") or "").strip()
        options_list.append(
            Option(
                id=label,
                text=text or "(empty)",
                is_correct=label in correct,
                explanation="",
            )
        )

    core = (q.metadata or {}).get("core_concept_generated") or ""
    body = (q.explanation_body or "").strip()
    final_letter = next(iter(correct), "") if correct else ""

    fc_out: List[ExportFlashcard] = []
    for fc in q.flashcards or []:
        if isinstance(fc, PipelineFlashcard):
            fc_out.append(ExportFlashcard(front=fc.front_text, back=fc.back_text))
        else:
            fc_out.append(ExportFlashcard(front=str(fc), back=""))

    return EdmateQuestion(
        id=uuid.uuid4(),
        metadata=Metadata(curriculum=curriculum, subject=q.subject, topic=topic),
        content={"type": "mcq"},
        question_text=q.question_text,
        options=options_list,
        explanations=Explanations(
            core_concept=str(core) or topic,
            detailed_logic=q.option_wise_explanation or body,
            final_answer_display=final_letter or "",
        ),
        flashcards=fc_out,
        media=[],
    )
