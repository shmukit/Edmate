"""PDF-Extract-Kit wrapper — public API and orchestration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional

import fitz

from content_gen.scripts.extraction.kit._bootstrap import (
    CONTENT_GEN_ROOT,
    HAS_KIT,
    KIT_PATH,
    initialize_tasks_and_models,
)
from content_gen.scripts.extraction.kit.image_utils import KitImageUtilsMixin
from content_gen.scripts.extraction.kit.page_processor import KitPageProcessorMixin
from content_gen.scripts.extraction.kit.question_builder import KitQuestionBuilderMixin
from content_gen.scripts.extraction.kit.text_utils import KitTextUtilsMixin


class PDFExtractKitWrapper(
    KitPageProcessorMixin,
    KitTextUtilsMixin,
    KitImageUtilsMixin,
    KitQuestionBuilderMixin,
):
    """
    Wrapper for PDF-Extract-Kit that provides a simple interface
    compatible with the old smart_extract.py output format
    """

    def __init__(
        self,
        pdf_path: Optional[str] = None,
        output_dir: Optional[str] = None,
        use_gpu: bool = False,
        min_question_number: int = 1,
        max_question_number: Optional[int] = None,
        question_detection_mode: str = "balanced",
        extraction_noise_patterns: Optional[List[str]] = None,
    ) -> None:
        self.use_gpu = use_gpu
        self.pdf_path = pdf_path
        self.output_dir = Path(output_dir) if output_dir else None
        self.min_question_number = min_question_number
        self.max_question_number = max_question_number
        self.question_detection_mode = question_detection_mode
        if extraction_noise_patterns is None:
            from content_gen.core.config_schema import DEFAULT_EXTRACTION_NOISE_PATTERNS

            self.extraction_noise_patterns = list(DEFAULT_EXTRACTION_NOISE_PATTERNS)
        else:
            self.extraction_noise_patterns = list(extraction_noise_patterns)

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = CONTENT_GEN_ROOT / "data" / "extracted"

        if self.pdf_path:
            self.base_name = Path(self.pdf_path).stem
            self.images_dir = self.output_dir / "images" / self.base_name
            self.images_dir.mkdir(parents=True, exist_ok=True)
            self.outputs_dir = self.output_dir.parent / "outputs"
            self.outputs_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.base_name = None
            self.images_dir = None
            self.outputs_dir = None

        self._init_models()

    def _init_models(self) -> None:
        """Initialize PDF-Extract-Kit AI models"""
        if not HAS_KIT:
            print("❌ Cannot initialize models: PDF-Extract-Kit not found in tools/")
            self.layout_detector = None
            return
        if initialize_tasks_and_models is None:
            print("❌ Cannot initialize models: config loader is unavailable")
            self.layout_detector = None
            return

        device = "cuda" if self.use_gpu else "cpu"
        config = {
            "tasks": {
                "layout_detection": {
                    "model": "layout_detection_yolo",
                    "model_config": {
                        "img_size": 1280,
                        "conf_thres": 0.25,
                        "iou_thres": 0.45,
                        "model_path": str(
                            KIT_PATH / "models/Layout/YOLO/doclayout_yolo_ft.pt"
                        ),
                        "device": device,
                    },
                }
            }
        }

        print("🤖 Initializing PDF-Extract-Kit AI models...")
        task_instances = initialize_tasks_and_models(config)
        self.layout_detector = task_instances["layout_detection"]
        print("✅ Models loaded successfully")

    def extract(
        self, progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict:
        if not HAS_KIT:
            raise RuntimeError(
                "Extraction failed: PDF-Extract-Kit is not installed or found in tools/"
            )
        if not self.pdf_path:
            raise ValueError("pdf_path must be set before calling extract()")
        if (
            not self.output_dir
            or not self.base_name
            or not self.images_dir
            or not self.outputs_dir
        ):
            raise ValueError(
                "output_dir/base_name/images_dir/outputs_dir must be initialized before calling extract()"
            )
        if self.layout_detector is None:
            raise RuntimeError("Layout detector is not initialized")

        doc = fitz.open(self.pdf_path)
        all_questions: List[Dict] = []

        print(f"📄 Processing: {self.pdf_path}")
        print(f"   Pages: {len(doc)}")

        if progress_callback:
            progress_callback(25, "Extracting diagrams and images via Vision AI...")

        last_q_num: Optional[int] = None
        for page_num in range(len(doc)):
            page = doc[page_num]
            questions_on_page, last_q_num = self._process_page(
                page, page_num + 1, doc, last_q_num
            )
            all_questions.extend(questions_on_page)

        doc.close()

        if progress_callback:
            progress_callback(45, "Parsing text and layout structures...")

        merged_questions = self._merge_questions(all_questions)
        output = {
            "source": self.pdf_path,
            "base_name": self.base_name,
            "questions": merged_questions,
            "raw_questions": all_questions,
            "total_questions": len(merged_questions),
            "extraction_settings": {
                "min_question_number": self.min_question_number,
                "max_question_number": self.max_question_number,
                "question_detection_mode": self.question_detection_mode,
            },
        }

        json_path = self.output_dir / f"{self.base_name}_extracted.json"
        with open(json_path, "w") as f:
            json.dump(output, f, indent=2)

        self._generate_processed_text(output)

        print("\n✅ Extraction complete!")
        print(f"   Questions: {len(merged_questions)}")
        print(f"   JSON: {json_path}")
        print(f"   Text Output: {self.outputs_dir / f'{self.base_name}_processed.txt'}")
        print(
            f"   Images: {self.images_dir} ({len(list(self.images_dir.glob('*.png')))} files)"
        )

        return output

    def extract_questions(
        self,
        source_path: str,
        output_dir: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Dict:
        """Adapter-compatible extraction method"""
        self.pdf_path = source_path
        self.output_dir = Path(output_dir)
        self.base_name = Path(source_path).stem

        self.images_dir = self.output_dir / "images" / self.base_name
        self.images_dir.mkdir(parents=True, exist_ok=True)

        self.outputs_dir = self.output_dir.parent / "outputs"
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

        return self.extract(progress_callback=progress_callback)


def main() -> None:
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract questions from PDF using PDF-Extract-Kit"
    )
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument(
        "--output-dir",
        default="content_gen/data/extracted",
        help="Output directory",
    )

    args = parser.parse_args()

    extractor = PDFExtractKitWrapper(args.pdf_path, args.output_dir)
    extractor.extract()


if __name__ == "__main__":
    main()
