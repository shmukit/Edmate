from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Flashcard(BaseModel):
    """Standard model for a single flashcard."""
    front_text: str = Field(..., description="Front/Question side of the flashcard")
    back_text: str = Field(..., description="Back/Answer side of the flashcard")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class QuestionOption(BaseModel):
    """Standard model for a multiple-choice option."""
    label: str = Field(..., description="A, B, C, or D")
    text: str = Field(..., description="The option text (HTML/LaTeX)")
    explanation: Optional[str] = Field(None, description="Explanation for why this option is correct/incorrect")

class ProcessedQuestion(BaseModel):
    """Standardized output for a processing question."""
    question_number: int
    question_text: str
    options: Dict[str, str] = Field(default_factory=dict)
    correct_options: List[str] = Field(default_factory=list)
    
    # Generated content
    explanation_body: Optional[str] = None
    option_wise_explanation: Optional[str] = None
    flashcards: List[Flashcard] = Field(default_factory=list)
    
    # Metadata
    subject: str
    paper_code: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BatchProcessingReport(BaseModel):
    """Report for a batch run."""
    timestamp: datetime = Field(default_factory=datetime.now)
    total_processed: int
    successful: int
    failed: int
    errors: List[Dict[str, str]] = Field(default_factory=list)
    results: List[ProcessedQuestion] = Field(default_factory=list)

class ModelConfig(BaseModel):
    """Configuration for routing models to specific tasks."""
    extraction_model: str = "gemini/gemini-1.5-pro"
    generation_model: str = "anthropic/claude-3-haiku"
    validation_model: str = "openai/gpt-4o"
    max_budget: float = 10.0  # USD daily cap placeholder
    image_mode: str = "cdn"    # "cdn" or "base64"
