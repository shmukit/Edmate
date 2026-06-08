"""
Public / export-oriented Lab_QA question shape (nested metadata, option list, etc.).

The live pipeline uses :mod:`content_gen.core.schemas` (:class:`ProcessedQuestion`).
Map between the two with :mod:`content_gen.core.question_mapping`.
"""

from typing import List, Optional, Literal
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, UUID4
from enum import Enum

class DifficultyLevel(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

class QuestionType(str, Enum):
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"
    TRUE_FALSE = "true_false"
    STRUCTURED = "structured"

class BloomTaxonomy(str, Enum):
    REMEMBER = "Remember"
    UNDERSTAND = "Understand"
    APPLY = "Apply"
    ANALYZE = "Analyze"
    EVALUATE = "Evaluate"
    CREATE = "Create"

class ExamContext(BaseModel):
    board: Optional[str] = None
    year: Optional[str] = None
    session: Optional[str] = None
    variant: Optional[str] = None

class Metadata(BaseModel):
    curriculum: str = Field(..., description="Curriculum label for your deployment (any string)")
    subject: str
    topic: str
    subtopic: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    exam_context: Optional[ExamContext] = None

class Option(BaseModel):
    id: str = Field(..., description="e.g., 'A', 'B', 'C', 'D'")
    text: str
    is_correct: bool
    explanation: str

class Explanations(BaseModel):
    core_concept: str
    detailed_logic: str
    final_answer_display: str
    bloom_taxonomy: Optional[BloomTaxonomy] = None

class Flashcard(BaseModel):
    front: str
    back: str
    type: Literal["concept", "recall", "problem_solving"] = "concept"

class MediaItem(BaseModel):
    id: str
    type: Literal["image", "video", "table"]
    content_ref: str
    alt_text: Optional[str] = None

class EdmateQuestion(BaseModel):
    """The standard v1.0.0 Edmate Lab_QA Question Schema"""

    model_config = ConfigDict(use_enum_values=True, populate_by_name=True)

    # Python attribute is schema_version; JSON may use "$schema_version" (Lab_QA export).
    schema_version: str = Field(
        default="1.0.0",
        validation_alias=AliasChoices("schema_version", "$schema_version"),
        serialization_alias="$schema_version",
    )
    id: Optional[UUID4] = None
    metadata: Metadata
    content: dict = Field(..., description="Type-specific content based on QuestionType")
    # Note: Using dict for content to allow flexible types, can be further specialized

    # Common fields that can be promoted to direct child for convenience
    question_text: str
    options: Optional[List[Option]] = None
    explanations: Explanations
    flashcards: List[Flashcard] = []
    media: List[MediaItem] = []
