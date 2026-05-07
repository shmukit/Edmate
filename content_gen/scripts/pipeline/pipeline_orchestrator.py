import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional, cast
import argparse

# Import modular core
from content_gen.core.media_encoding import png_file_to_data_uri
from content_gen.core.model_router import ModelRoutingEngine
from content_gen.core.config_schema import ExtractionEngine
from content_gen.adapters.postgres_adapter import PostgresStorageAdapter

# Import local modules
from content_gen.adapters.kit_extraction_adapter import KitExtractionAdapter
from content_gen.adapters.pymupdf_adapter import PyMuPDFAdapter
from content_gen.adapters.vision_extraction_adapter import VisionExtractionAdapter
from content_gen.scripts.processing.upload_to_storage import StorageUploader
from content_gen.scripts.processing.content_generator import ContentGenerator


class PipelineOrchestrator:
    def __init__(
        self,
        storage_bucket: Optional[str] = None,
        db_connection: Optional[str] = None,
        router: Optional[ModelRoutingEngine] = None
    ):
        """
        Initialize modular pipeline orchestrator
        """
        self.storage_bucket = storage_bucket
        self.db_connection = db_connection
        self.router = router or ModelRoutingEngine()
        self.generator = ContentGenerator(router=self.router)
        self.storage = (
            PostgresStorageAdapter(db_connection, edmate_config=self.router.config)
            if db_connection
            else None
        )

        # Initialize Extractor based on config
        engine = self.router.config.extraction_settings.engine
        engine_key = engine.value if isinstance(engine, ExtractionEngine) else str(engine).lower()
        es = self.router.config.extraction_settings
        ws = self.router.config.workspace
        default_subject = (ws.default_subject or "General").strip() or "General"
        if engine_key == ExtractionEngine.PYMUPDF.value:
            self.extractor = PyMuPDFAdapter()
        elif engine_key in (
            ExtractionEngine.VISION.value,
            ExtractionEngine.MULTIMODAL.value,
            ExtractionEngine.PDF_EXTRACT_KIT.value,
        ):
            if engine_key == ExtractionEngine.PDF_EXTRACT_KIT.value:
                self.extractor = KitExtractionAdapter(
                    min_question_number=es.min_question_number,
                    max_question_number=es.max_question_number,
                    question_detection_mode=str(es.question_detection_mode.value)
                    if hasattr(es.question_detection_mode, "value")
                    else str(es.question_detection_mode),
                    extraction_noise_patterns=list(es.extraction_noise_patterns),
                    default_subject=default_subject,
                )
            else:
                self.extractor = VisionExtractionAdapter(router=self.router)
        else:
            self.extractor = VisionExtractionAdapter(router=self.router)

    def _convert_to_base64(self, image_path: Path) -> str:
        """Converts an image file to a base64 Data URI."""
        try:
            return png_file_to_data_uri(image_path)
        except Exception as e:
            print(f"⚠️ Failed to base64 encode {image_path}: {e}")
            return ""

    def process_pdf(
        self,
        pdf_path: str,
        output_dir: str,
        subject: str,
        difficulty: Optional[str] = "Medium",
        topics: Optional[List[str]] = None,
        cleanup_images: bool = False,
        curriculum: Optional[str] = None,
    ) -> Dict:
        """
        Process a single PDF through the modular Edmate pipeline.
        """
        pdf_name = Path(pdf_path).stem
        print(f"\n🚀 [MODULAR] Processing: {pdf_name}")

        report = {
            "pdf": pdf_name,
            "extraction": None,
            "processing": None,
            "persistence": None,
            "errors": []
        }

        # Step 1: Multimodal Extraction (The "Eyes")
        _eng = self.router.config.extraction_settings.engine
        _eng_disp = _eng.value if hasattr(_eng, "value") else str(_eng)
        print(f"👁️  Step 1: Extracting with {_eng_disp}...")
        extracted_questions = self.extractor.extract_content(
            Path(pdf_path), Path(output_dir))
        report["extraction"] = {"questions": len(extracted_questions)}

        # Step 2: Modular Content Generation (The "Brain")
        generated_questions = []
        try:
            print("🤖 Step 2: Generating educational content via ModelRouter...")
            generated_questions = self.generator.generate_for_questions(
                extracted_questions,
                subject=subject,
                curriculum=curriculum,
            )
            report["processing"] = {"count": len(generated_questions)}
        except Exception as e:
            report["errors"].append(f"Content generation failed: {e}")

        # Step 3: Modular Persistence (The "Legs")
        if self.storage:
            # 2. Storage Upload (Conditional)
            cdn_mapping = {}
            images_root = Path(output_dir) / "images" / pdf_name
            if not images_root.exists():
                images_root = Path(output_dir) / "images"
            images = list(images_root.rglob("*.png")) if images_root.exists() else []
            if self.router.config.storage_settings.image_mode == "base64":
                print("📦 Encoding images to Base64...")
                for img_path in images:
                    b64_str = self._convert_to_base64(img_path)
                    if b64_str:
                        cdn_mapping[img_path.name] = b64_str
            else:
                storage_bucket = self.storage_bucket
                if storage_bucket is None:
                    raise ValueError("storage_bucket must be set to upload images")
                print(
                    f"☁️ Uploading {len(images)} images to {storage_bucket}...")
                uploader = StorageUploader()
                cdn_mapping, _ = uploader.upload_directory(
                    images_dir=str(images_root),
                    container=storage_bucket,
                    base_path=f"diagrams/{pdf_name}",
                )

            try:
                print("📥 Step 3: Persisting to Database...")
                for q in generated_questions:
                    # Enrich with paper metadata
                    q.paper_code = pdf_name
                    q.metadata.update({
                        "difficulty": difficulty,
                        "subject": subject,
                        "topic_hint": topics[0] if topics else None
                    })
                    self.storage.save_question(q)

                # Batch save flashcards
                all_fcs = []
                for q in generated_questions:
                    all_fcs.extend(q.flashcards)

                if all_fcs:
                    self.storage.save_flashcards(all_fcs, {"subject": subject})

                report["persistence"] = {"status": "complete"}
            except Exception as e:
                report["errors"].append(f"Persistence failed: {e}")

        return report

    def process_batch(
        self,
        input_dir: str,
        output_dir: str,
        subject: str,
        difficulty: Optional[str] = None,
        topics: Optional[List[str]] = None,
        cleanup_images: bool = False
    ) -> Dict:
        """
        Process all PDFs in a directory

        Args:
            input_dir: Directory containing PDF files
            output_dir: Output directory for extracted data
            subject: Subject name
            difficulty: Difficulty level
            topics: Topic tags
            cleanup_images: Delete local images after upload

        Returns:
            Batch report with all PDFs processed
        """
        pdf_files = list(Path(input_dir).glob("*.pdf"))

        if not pdf_files:
            print(f"❌ No PDF files found in {input_dir}")
            return {"pdfs": [], "errors": ["No PDFs found"]}

        print(f"\n🚀 Starting batch processing: {len(pdf_files)} PDFs")
        print(f"{'='*60}\n")

        batch_report = {
            "total_pdfs": len(pdf_files),
            "pdfs": [],
            "summary": {
                "total_questions": 0,
                "total_diagrams": 0,
                "total_errors": 0
            }
        }

        for pdf_path in pdf_files:
            report = self.process_pdf(
                pdf_path=str(pdf_path),
                output_dir=output_dir,
                subject=subject,
                difficulty=difficulty,
                topics=topics,
                cleanup_images=cleanup_images
            )

            batch_report["pdfs"].append(report)

            # Update summary
            if report.get("extraction"):
                batch_report["summary"]["total_questions"] += report["extraction"]["questions"]
            if report.get("upload"):
                batch_report["summary"]["total_diagrams"] += report["upload"]["uploaded"]
            batch_report["summary"]["total_errors"] += len(report["errors"])

        # Print summary
        print(f"\n{'='*60}")
        print("📊 Batch Processing Summary")
        print(f"{'='*60}")
        print(f"  PDFs Processed: {batch_report['total_pdfs']}")
        print(
            f"  Questions Extracted: {batch_report['summary']['total_questions']}")
        print(
            f"  Diagrams Uploaded: {batch_report['summary']['total_diagrams']}")
        print(f"  Errors: {batch_report['summary']['total_errors']}")
        print(f"{'='*60}\n")

        return batch_report


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="End-to-end content generation pipeline")

    # Input/Output
    parser.add_argument("--input-dir", required=True,
                        help="Directory containing PDF files")
    parser.add_argument(
        "--output-dir", default="content_gen/data/extracted", help="Output directory")

    # Metadata
    parser.add_argument(
        "--subject",
        default=None,
        help="Subject label for generation metadata (default: workspace.default_subject in edmate_config.yaml, else General).",
    )
    parser.add_argument("--difficulty", choices=["Easy", "Medium", "Hard"])
    parser.add_argument("--topics", nargs="+", help="Topic tags")

    # Storage
    parser.add_argument(
        "--storage-provider",
        choices=["auto", "azure"],
        default="auto",
        help="Storage backend selector (kept for backward compatibility; currently ignored).",
    )
    parser.add_argument("--storage-bucket",
                        help="CDN/storage bucket or container name (needed for non-base64 image mode)")
    parser.add_argument("--cleanup-images", action="store_true",
                        help="Delete local images after upload")

    # Database
    parser.add_argument(
        "--db-url", help="Database connection string (or use DATABASE_URL env var)")
    parser.add_argument("--create-schema", action="store_true",
                        help="Create database schema before import")

    # Processing
    parser.add_argument(
        "--single-pdf", help="Process a single PDF instead of batch")

    args = parser.parse_args()

    if args.storage_provider != "auto":
        print("ℹ️ --storage-provider is deprecated and currently ignored.")

    # Get database URL
    db_url: Optional[str] = cast(Optional[str], args.db_url or os.getenv("DATABASE_URL"))

    # Initialize orchestrator
    orchestrator = PipelineOrchestrator(
        storage_bucket=args.storage_bucket,
        db_connection=db_url
    )
    subject_resolved = (args.subject or "").strip() or (
        orchestrator.router.config.workspace.default_subject or "General"
    )

    # Create schema if requested
    if args.create_schema and db_url:
        print("🏗️  Creating database schema...")
        PostgresStorageAdapter.initialize_schema(
            db_url, edmate_config=orchestrator.router.config
        )

    # Process
    if args.single_pdf:
        # Single PDF mode
        report = orchestrator.process_pdf(
            pdf_path=args.single_pdf,
            output_dir=args.output_dir,
            subject=subject_resolved,
            difficulty=args.difficulty,
            topics=args.topics,
            cleanup_images=args.cleanup_images
        )

        # Save report
        report_path = Path(args.output_dir) / \
            f"{Path(args.single_pdf).stem}_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        sys.exit(0 if len(report["errors"]) == 0 else 1)

    else:
        # Batch mode
        batch_report = orchestrator.process_batch(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            subject=subject_resolved,
            difficulty=args.difficulty,
            topics=args.topics,
            cleanup_images=args.cleanup_images
        )

        # Save batch report
        report_path = Path(args.output_dir) / "batch_report.json"
        with open(report_path, 'w') as f:
            json.dump(batch_report, f, indent=2)

        print(f"💾 Batch report saved to: {report_path}")

        sys.exit(0 if batch_report["summary"]["total_errors"] == 0 else 1)


if __name__ == "__main__":
    main()
