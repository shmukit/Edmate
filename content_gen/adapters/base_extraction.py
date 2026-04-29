from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from pathlib import Path
from ..core.schemas import ProcessedQuestion


class BaseExtractionAdapter(ABC):
    """
    Abstract base class for all PDF extraction engines in Edmate.
    Ensures that different tools (kit-based, OCR, or cloud-based) 
    produce a standardized output for the pipeline.
    """

    @abstractmethod
    def extract_content(
        self, 
        source_path: Path, 
        output_dir: Path, 
        progress_callback: Optional[callable] = None
    ) -> List[ProcessedQuestion]:
        """
        Extracts structured content from a source PDF.
        Should handle both text extraction and image/diagram extraction.
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Returns a list of supported file extensions (e.g. ['.pdf', '.docx'])."""
        pass
