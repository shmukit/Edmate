from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

class ImageMode(str, Enum):
    CDN = "cdn"
    BASE64 = "base64"

class ExtractionEngine(str, Enum):
    PDF_EXTRACT_KIT = "pdf_extract_kit"
    PYMUPDF = "pymupdf"

class DetectionMode(str, Enum):
    STRICT = "strict"
    BALANCED = "balanced"
    OPEN = "open"

class BloomLevel(str, Enum):
    REMEMBER = "Remember"
    UNDERSTAND = "Understand"
    APPLY = "Apply"
    ANALYZE = "Analyze"
    EVALUATE = "Evaluate"
    CREATE = "Create"

class SRAlogrithm(str, Enum):
    SM2 = "sm2"
    ANKI = "anki"
    LEITNER = "leitner"

class ExplanationDepth(str, Enum):
    FULL = "full"
    CORE_ONLY = "core_only"
    STEPS_ONLY = "steps_only"

class AssessmentRole(str, Enum):
    FORMATIVE = "formative"
    SUMMATIVE = "summative"
    DIAGNOSTIC = "diagnostic"
    PRACTICE = "practice"

class ModelRouting(BaseModel):
    extraction: str = "gemini/gemini-1.5-pro"
    generation: str = "anthropic/claude-3-haiku"
    validation: str = "openai/gpt-4o"

class BudgetConfig(BaseModel):
    max_daily_usd: float = 10.0

class StorageSettings(BaseModel):
    image_mode: ImageMode = ImageMode.CDN

class ExtractionSettings(BaseModel):
    engine: ExtractionEngine = ExtractionEngine.PDF_EXTRACT_KIT
    min_question_number: int = 1
    max_question_number: Optional[int] = None
    question_detection_mode: DetectionMode = DetectionMode.BALANCED

class ObservabilityConfig(BaseModel):
    litellm_callbacks: List[str] = Field(default_factory=lambda: ["opik"])

class BloomTaxonomyConfig(BaseModel):
    enabled: bool = True
    target_levels: List[BloomLevel] = Field(default_factory=lambda: list(BloomLevel))

class SpacedRepetitionConfig(BaseModel):
    enabled: bool = True
    algorithm: SRAlogrithm = SRAlogrithm.SM2

class CognitiveLoadConfig(BaseModel):
    enabled: bool = True
    explanation_depth: ExplanationDepth = ExplanationDepth.FULL

class LearningScienceConfig(BaseModel):
    profile: str = "default"
    bloom_taxonomy: BloomTaxonomyConfig = Field(default_factory=BloomTaxonomyConfig)
    spaced_repetition: SpacedRepetitionConfig = Field(default_factory=SpacedRepetitionConfig)
    elaborative_interrogation: Dict[str, bool] = Field(default_factory=lambda: {"enabled": True})
    cognitive_load: CognitiveLoadConfig = Field(default_factory=CognitiveLoadConfig)
    retrieval_practice: Dict[str, bool] = Field(default_factory=lambda: {"enabled": True, "generate_variants": False})
    interleaving: Dict[str, bool] = Field(default_factory=lambda: {"enabled": True})
    formative_summative_tagging: Dict[str, Any] = Field(default_factory=lambda: {"enabled": True, "default_role": "formative"})
    assessment_role_tagging: Dict[str, bool] = Field(default_factory=lambda: {"enabled": True})

class HIASettings(BaseModel):
    enabled: bool = True
    default_resilience_target: str = "High"
    generate_critique_exercises: bool = True
    generate_variants: bool = True
    variant_count: int = 3

class TargetTable(BaseModel):
    id: str
    label: str

class WorkspaceConfig(BaseModel):
    curriculums: List[str] = Field(default_factory=list)
    target_tables: List[TargetTable] = Field(default_factory=list)

class EdmateConfig(BaseModel):
    """Root configuration for Edmate."""
    model_routing: ModelRouting = Field(default_factory=ModelRouting)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    storage_settings: StorageSettings = Field(default_factory=StorageSettings)
    extraction_settings: ExtractionSettings = Field(default_factory=ExtractionSettings)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    learning_science: LearningScienceConfig = Field(default_factory=LearningScienceConfig)
    hia_settings: HIASettings = Field(default_factory=HIASettings)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
