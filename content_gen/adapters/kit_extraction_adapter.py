from pathlib import Path
from typing import List
from .base_extraction import BaseExtractionAdapter
from ..core.schemas import ProcessedQuestion
from ..scripts.extraction.pdf_extract_kit_wrapper import PDFExtractKitWrapper

class KitExtractionAdapter(BaseExtractionAdapter):
    """
    Adapter for the high-fidelity PDF-Extract-Kit engine.
    Uses multimodal vision models for precise diagram extraction.
    """
    
    def __init__(self, use_gpu: bool = True):
        self.wrapper = PDFExtractKitWrapper(use_gpu=use_gpu)

    def extract_content(self, source_path: Path, output_dir: Path) -> List[ProcessedQuestion]:
        # Invoke the existing wrapper logic
        # Note: The current wrapper returns raw dicts, we would 
        # normally map them to ProcessedQuestion here.
        # For now, we utilize the wrapper's built-in extraction flow.
        result = self.wrapper.extract_questions(str(source_path), str(output_dir))
        
        # Mapping logic from raw extraction JSON to Pydantic models
        questions = []
        for q_data in result.get("questions", []):
            questions.append(ProcessedQuestion(
                question_number=q_data.get("question_number", 0),
                question_text=q_data.get("question_text", ""),
                options=q_data.get("options", {}),
                subject="Biology", # Default, ideally resolved from source
                metadata={
                    "stem_images": q_data.get("stem_images", []),
                    "option_images": q_data.get("option_images", {})
                }
            ))
        return questions

    def get_supported_formats(self) -> List[str]:
        return [".pdf"]
