from typing import List, Optional, Literal
from pydantic import BaseModel, Field, UUID4
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
    schema_version: str = Field("1.0.0", alias="$schema_version")
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

    class Config:
        use_enum_values = True
        populate_by_name = True
