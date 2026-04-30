from pathlib import Path
import os
from typing import List, Optional, Callable
from content_gen.adapters.base_extraction import BaseExtractionAdapter
from content_gen.core.schemas import ProcessedQuestion
from content_gen.scripts.extraction.pdf_extract_kit_wrapper import PDFExtractKitWrapper


class KitExtractionAdapter(BaseExtractionAdapter):
    """
    Adapter for the high-fidelity PDF-Extract-Kit engine.
    Uses multimodal vision models for precise diagram extraction.
    """

    def __init__(
        self,
        use_gpu: bool = False,
        min_question_number: int = 1,
        max_question_number: int | None = None,
        question_detection_mode: str = "balanced",
    ):
        try:
            self.wrapper = PDFExtractKitWrapper(
                use_gpu=use_gpu,
                min_question_number=min_question_number,
                max_question_number=max_question_number,
                question_detection_mode=question_detection_mode,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize PDF-Extract-Kit: {e}\n"
                "Please ensure all machine learning dependencies (e.g. doclayout_yolo, torch) are installed, "
                "or switch the 'extraction_engine' config to 'pymupdf' in edmate_config.yaml to use the lightweight extractor."
            ) from e

    def extract_content(
        self, 
        source_path: Path, 
        output_dir: Path, 
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[ProcessedQuestion]:
        # Invoke the existing wrapper logic
        import base64
        result = self.wrapper.extract_questions(
            str(source_path), str(output_dir), progress_callback=progress_callback)

        # Mapping logic from raw extraction JSON to Pydantic models
        questions = []
        for q_data in result.get("questions", []):
            stem_image_paths = list(q_data.get("stem_images", []))
            stem_images_b64 = []
            for img_path in stem_image_paths:
                try:
                    if os.path.exists(img_path):
                        with open(img_path, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode("utf-8")
                            stem_images_b64.append(f"data:image/png;base64,{b64}")
                except Exception:
                    continue

            questions.append(ProcessedQuestion(
                question_number=q_data.get("question_number", 0),
                question_text=q_data.get("question_text", ""),
                options=q_data.get("options", {}),
                subject=q_data.get("subject", "Physics"),  # Fallback to Physics for 9702 papers
                metadata={
                    "stem_images": stem_image_paths,
                    "stem_images_b64": stem_images_b64,
                    "option_images": q_data.get("option_images", {})
                }
            ))
        return questions

    def get_supported_formats(self) -> List[str]:
        return [".pdf"]
