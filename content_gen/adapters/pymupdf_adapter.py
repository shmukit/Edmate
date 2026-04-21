import fitz  # PyMuPDF
from pathlib import Path
from typing import List
from content_gen.adapters.base_extraction import BaseExtractionAdapter
from content_gen.core.schemas import ProcessedQuestion


class PyMuPDFAdapter(BaseExtractionAdapter):
    """
    Lightweight, CPU-only PDF extractor.
    Optimized for text extraction without the overhead of vision models.
    """

    def extract_content(self, source_path: Path, output_dir: Path) -> List[ProcessedQuestion]:
        print(f"📄 Extracting text via PyMuPDF: {source_path.name}")
        doc = fitz.open(str(source_path))
        full_text = ""
        for page in doc:
            full_text += page.get_text()

        # Simplified logic: treat entire text as one block/question for now
        # In a real scenario, we would apply regex patterns to split by Q1, Q2 etc.
        questions = [
            ProcessedQuestion(
                question_number=1,
                question_text=full_text[:2000],  # Preview
                subject="General",
                metadata={"engine": "pymupdf"}
            )
        ]
        doc.close()
        return questions

    def get_supported_formats(self) -> List[str]:
        return [".pdf"]
