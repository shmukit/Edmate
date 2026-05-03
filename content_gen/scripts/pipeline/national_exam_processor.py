import os
import sys
import json
import re
import argparse
from pathlib import Path
import fitz  # PyMuPDF
from typing import List, Dict, cast, Any, Optional
from dotenv import load_dotenv

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Load environment variables
env_path = Path(project_root) / "content_gen" / ".env"
load_dotenv(env_path)

# Explicitly set env vars for litellm and other components
import dotenv

env_vars = dotenv.dotenv_values(env_path)
for key, value in env_vars.items():
    if value:
        os.environ[key] = value

# Set Vertex AI Location
os.environ["VERTEXAI_LOCATION"] = "asia-south1"

from content_gen.core.segmentation import TextSegmentationUtility
from content_gen.core.model_router import ModelRoutingEngine
from content_gen.core.config_schema import ExtractionEngine
from content_gen.adapters.vision_extraction_adapter import VisionExtractionAdapter
from content_gen.adapters.kit_extraction_adapter import KitExtractionAdapter
from content_gen.adapters.pymupdf_adapter import PyMuPDFAdapter
from content_gen.scripts.prompts import NATIONAL_EXAM_SYSTEM_PROMPT, NATIONAL_EXAM_EXTRACTION_PROMPT

import time


class NationalExamProcessor:
    """
    Standalone exam processor: supports legacy text+regex path or the same
    multimodal extractors as PipelineOrchestrator (vision / pdf_extract_kit / pymupdf).
    """

    def __init__(
        self,
        curriculum: str = "General",
        output_dir: str = "content_gen/data/outputs/national_exams",
        extraction_engine: Optional[str] = None,
    ):
        self.curriculum = curriculum
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.router = ModelRoutingEngine()
        es = self.router.config.extraction_settings
        if extraction_engine:
            self.extraction_engine = extraction_engine.strip().lower()
        else:
            eng = es.engine
            self.extraction_engine = (
                eng.value if hasattr(eng, "value") else str(eng)
            ).lower()

    def extract_text(self, pdf_path: Path) -> str:
        doc = fitz.open(str(pdf_path))
        text = ""
        for page in doc:
            text += cast(str, page.get_text("text"))
        doc.close()
        return text

    def _extract_questions_structured(self, path: Path) -> List[Dict[str, Any]]:
        """Run configured extraction engine and map to legacy question dict shape."""
        tmp_root = self.output_dir / "_extract_cache" / path.stem
        tmp_root.mkdir(parents=True, exist_ok=True)

        eng = self.extraction_engine
        if eng in (ExtractionEngine.VISION.value, ExtractionEngine.MULTIMODAL.value):
            adapter = VisionExtractionAdapter(router=self.router)
            items = adapter.extract_content(path, tmp_root)
        elif eng == ExtractionEngine.PDF_EXTRACT_KIT.value:
            adapter = KitExtractionAdapter(
                min_question_number=self.router.config.extraction_settings.min_question_number,
                max_question_number=self.router.config.extraction_settings.max_question_number,
                question_detection_mode=str(
                    self.router.config.extraction_settings.question_detection_mode.value
                )
                if hasattr(
                    self.router.config.extraction_settings.question_detection_mode, "value"
                )
                else str(self.router.config.extraction_settings.question_detection_mode),
                extraction_noise_patterns=list(
                    self.router.config.extraction_settings.extraction_noise_patterns
                ),
                default_subject=self.router.config.workspace.default_subject or "General",
            )
            items = adapter.extract_content(path, tmp_root)
        elif eng == ExtractionEngine.PYMUPDF.value:
            items = PyMuPDFAdapter().extract_content(path, tmp_root)
        else:
            full_text = self.extract_text(path)
            preset = self.router.config.extraction_settings.segmentation_preset
            return TextSegmentationUtility.segment_exam(full_text, preset=preset)

        mapped: List[Dict[str, Any]] = []
        for pq in items:
            qtype = "MCQ" if pq.options else "General"
            meta = dict(pq.metadata or {})
            mapped.append(
                {
                    "section": "Unknown",
                    "question_number": pq.question_number,
                    "question_text": pq.question_text,
                    "options": pq.options or {},
                    "type": qtype,
                    "extraction_metadata": meta,
                }
            )
        return mapped

    def process_pdf(self, pdf_path: str):
        path = Path(pdf_path)
        print(f"\n📄 Processing: {path.name} (engine={self.extraction_engine})")

        questions = self._extract_questions_structured(path)
        print(f"🔍 Found {len(questions)} questions in {path.name}")

        processed_results = []

        for q in questions:
            print(f"  🤖 Generating content for Q{q['question_number']} ({q['type']})...")

            options_text = ""
            for k, v in q["options"].items():
                options_text += f"{k}. {v}\n"

            diagram_note = ""
            meta = q.get("extraction_metadata") or {}
            if meta.get("stem_images") or meta.get("stem_images_b64"):
                diagram_note = "\n[Note: This item includes diagram(s) in the extracted PDF pipeline metadata.]"

            prompt = (
                NATIONAL_EXAM_EXTRACTION_PROMPT.replace("[Curriculum]", self.curriculum).format(
                    question_text=q["question_text"] + diagram_note,
                    options_text=options_text or "No options",
                    question_type=q["type"],
                )
            )

            success = False
            retries = 3
            while not success and retries > 0:
                try:
                    response = self.router.generate_content(
                        prompt=prompt,
                        task_type="generation",
                        system_prompt=NATIONAL_EXAM_SYSTEM_PROMPT.replace(
                            "[Curriculum]", self.curriculum
                        ),
                    )

                    cc = self._extract_marker(response, "CC")
                    de = self._extract_marker(response, "DE")
                    oe = self._extract_marker(response, "OE")

                    if q["type"] != "MCQ":
                        oe = ""

                    row = {
                        "question_number": q["question_number"],
                        "section": q["section"],
                        "type": q["type"],
                        "question_text": q["question_text"],
                        "options": q["options"],
                        "core_concept": cc,
                        "detailed_explanation": de,
                        "option_wise_explanation": oe,
                        "raw_response": response,
                    }
                    if q.get("extraction_metadata"):
                        row["extraction_metadata"] = q["extraction_metadata"]
                    processed_results.append(row)
                    success = True
                    time.sleep(1)
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        print(
                            f"    ⚠️ Rate limit hit. Sleeping for 10s... (Retries left: {retries})"
                        )
                        time.sleep(10)
                        retries -= 1
                    else:
                        print(f"    ❌ Error: {e}")
                        break

        output_file = self.output_dir / f"{path.stem}_processed.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(processed_results, f, indent=2, ensure_ascii=False)

        txt_output = self.output_dir / f"{path.stem}_processed.txt"
        with open(txt_output, "w", encoding="utf-8") as f:
            for res in processed_results:
                f.write(f"{res['section']} Question {res['question_number']}\n")
                f.write(f"{'='*30}\n")
                f.write(f"Question: {res['question_text']}\n")
                if res["options"]:
                    f.write("Options:\n")
                    for k, v in res["options"].items():
                        f.write(f"  {k}. {v}\n")
                f.write(f"\nCore Concept:\n{res['core_concept']}\n")
                f.write(f"\nDetailed Explanation:\n{res['detailed_explanation']}\n")
                if res["option_wise_explanation"]:
                    f.write(f"\nOption Wise Explanation:\n{res['option_wise_explanation']}\n")
                f.write(f"\n{'-'*50}\n\n")

        print(f"✅ Finished! Outputs saved in {self.output_dir}")

    def _extract_marker(self, text: str, marker: str) -> str:
        pattern = f"\\[{marker}_START\\](.*?)\\[{marker}_END\\]"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process one or more exam PDFs.")
    parser.add_argument(
        "--pdf",
        dest="pdfs",
        nargs="*",
        default=[],
        help="Explicit PDF file paths to process.",
    )
    parser.add_argument(
        "--input-dir",
        default="content_gen/data/inputs",
        help="Directory to scan for PDFs when --pdf is not provided.",
    )
    parser.add_argument(
        "--output-dir",
        default="content_gen/data/outputs/national_exams",
        help="Directory for generated outputs.",
    )
    parser.add_argument(
        "--curriculum",
        default="General",
        help="Curriculum name injected into prompts (override edmate_config workspace.default_curriculum if desired).",
    )
    parser.add_argument(
        "--extraction-engine",
        default=None,
        choices=["vision", "multimodal", "pdf_extract_kit", "pymupdf", "legacy"],
        help="Override edmate_config extraction_settings.engine. Use 'legacy' for text+regex only.",
    )
    args = parser.parse_args()

    processor = NationalExamProcessor(
        curriculum=args.curriculum,
        output_dir=args.output_dir,
        extraction_engine=args.extraction_engine,
    )
    explicit_pdfs = [Path(p) for p in args.pdfs]
    discovered_pdfs = list(Path(args.input_dir).glob("*.pdf")) if not explicit_pdfs else []
    pdfs = explicit_pdfs or discovered_pdfs

    if not pdfs:
        print("⚠️ No PDFs found. Provide --pdf paths or place files in --input-dir.")
        sys.exit(0)

    for pdf in pdfs:
        if pdf.exists():
            processor.process_pdf(str(pdf))
        else:
            print(f"⚠️ File not found: {pdf}")
