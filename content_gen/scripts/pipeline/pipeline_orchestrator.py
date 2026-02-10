#!/usr/bin/env python3
"""
End-to-End Pipeline Orchestrator
Coordinates PDF extraction, storage upload, and database import
"""
import os
import sys
import json
import glob
from pathlib import Path
from typing import List, Dict
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import local modules
from extraction.pdf_extract_kit_wrapper import PDFExtractKitWrapper
from processing.upload_to_storage import StorageUploader
from processing.import_to_db import DatabaseImporter, create_schema


class PipelineOrchestrator:
    def __init__(
        self,
        storage_provider: str = "r2",
        storage_bucket: str = None,
        db_connection: str = None
    ):
        """
        Initialize pipeline orchestrator
        
        Args:
            storage_provider: "r2" or "s3"
            storage_bucket: Storage bucket name
            db_connection: Database connection string
        """
        self.storage_provider = storage_provider
        self.storage_bucket = storage_bucket
        self.db_connection = db_connection
        
        # Initialize components
        self.uploader = StorageUploader(provider=storage_provider) if storage_bucket else None
        
    def process_pdf(
        self,
        pdf_path: str,
        output_dir: str,
        subject: str,
        difficulty: str = None,
        topics: List[str] = None,
        cleanup_images: bool = False
    ) -> Dict:
        """
        Process a single PDF through the full pipeline
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory for extracted data
            subject: Subject name
            difficulty: Difficulty level
            topics: Topic tags
            cleanup_images: Delete local images after upload
            
        Returns:
            Report with counts and errors
        """
        pdf_name = Path(pdf_path).stem
        print(f"\n{'='*60}")
        print(f"📄 Processing: {pdf_name}")
        print(f"{'='*60}\n")
        
        report = {
            "pdf": pdf_name,
            "extraction": None,
            "upload": None,
            "import": None,
            "errors": []
        }
        
        # Step 1: Extract PDF
        try:
            print("🔍 Step 1: Extracting PDF content using PDF-Extract-Kit...")
            extractor = PDFExtractKitWrapper(pdf_path, output_dir)
            extraction_result = extractor.extract()
            
            json_path = Path(output_dir) / f"{pdf_name}_extracted.json"
            images_dir = Path(output_dir) / "images"
            
            report["extraction"] = {
                "questions": len(extraction_result["questions"]),
                "json_path": str(json_path)
            }
            print(f"  ✅ Extracted {len(extraction_result['questions'])} questions")
            
        except Exception as e:
            report["errors"].append(f"Extraction failed: {e}")
            print(f"  ❌ Extraction failed: {e}")
            return report
        
        # Step 2: Upload to storage
        cdn_mapping = {}
        if self.uploader and self.storage_bucket:
            try:
                print("\n📤 Step 2: Uploading images to storage...")
                base_path = f"diagrams/{pdf_name}"
                cdn_mapping, upload_report = self.uploader.upload_directory(
                    images_dir=str(images_dir),
                    bucket=self.storage_bucket,
                    base_path=base_path
                )
                
                report["upload"] = upload_report
                
                # Save CDN mapping
                cdn_mapping_path = Path(output_dir) / f"{pdf_name}_cdn_mapping.json"
                with open(cdn_mapping_path, 'w') as f:
                    json.dump({"cdn_mapping": cdn_mapping, "report": upload_report}, f, indent=2)
                
                # Cleanup local images if requested
                if cleanup_images and upload_report["failed"] == 0:
                    for img_file in images_dir.glob("*.png"):
                        img_file.unlink()
                    print(f"  🗑️  Cleaned up {upload_report['uploaded']} local images")
                
            except Exception as e:
                report["errors"].append(f"Upload failed: {e}")
                print(f"  ❌ Upload failed: {e}")
        else:
            print("\n⏭️  Step 2: Skipping storage upload (not configured)")
        
        # Step 3: Import to database
        if self.db_connection:
            try:
                print("\n📥 Step 3: Importing to database...")
                with DatabaseImporter(self.db_connection) as importer:
                    import_report = importer.import_questions(
                        json_path=str(json_path),
                        cdn_mapping=cdn_mapping,
                        paper_code=pdf_name,
                        subject=subject,
                        difficulty=difficulty,
                        topics=topics
                    )
                
                report["import"] = import_report
                
            except Exception as e:
                report["errors"].append(f"Import failed: {e}")
                print(f"  ❌ Import failed: {e}")
        else:
            print("\n⏭️  Step 3: Skipping database import (not configured)")
        
        return report
    
    def process_batch(
        self,
        input_dir: str,
        output_dir: str,
        subject: str,
        difficulty: str = None,
        topics: List[str] = None,
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
        pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
        
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
                pdf_path=pdf_path,
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
        print(f"  Questions Extracted: {batch_report['summary']['total_questions']}")
        print(f"  Diagrams Uploaded: {batch_report['summary']['total_diagrams']}")
        print(f"  Errors: {batch_report['summary']['total_errors']}")
        print(f"{'='*60}\n")
        
        return batch_report


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="End-to-end content generation pipeline")
    
    # Input/Output
    parser.add_argument("--input-dir", required=True, help="Directory containing PDF files")
    parser.add_argument("--output-dir", default="content_gen/data/extracted", help="Output directory")
    
    # Metadata
    parser.add_argument("--subject", required=True, choices=["Biology", "Chemistry", "Physics"])
    parser.add_argument("--difficulty", choices=["Easy", "Medium", "Hard"])
    parser.add_argument("--topics", nargs="+", help="Topic tags")
    
    # Storage
    parser.add_argument("--storage-provider", choices=["r2", "s3"], help="Storage provider")
    parser.add_argument("--storage-bucket", help="Storage bucket name")
    parser.add_argument("--cleanup-images", action="store_true", help="Delete local images after upload")
    
    # Database
    parser.add_argument("--db-url", help="Database connection string (or use DATABASE_URL env var)")
    parser.add_argument("--create-schema", action="store_true", help="Create database schema before import")
    
    # Processing
    parser.add_argument("--single-pdf", help="Process a single PDF instead of batch")
    
    args = parser.parse_args()
    
    # Get database URL
    db_url = args.db_url or os.getenv("DATABASE_URL")
    
    # Create schema if requested
    if args.create_schema and db_url:
        print("🏗️  Creating database schema...")
        create_schema(db_url)
    
    # Initialize orchestrator
    orchestrator = PipelineOrchestrator(
        storage_provider=args.storage_provider or "r2",
        storage_bucket=args.storage_bucket,
        db_connection=db_url
    )
    
    # Process
    if args.single_pdf:
        # Single PDF mode
        report = orchestrator.process_pdf(
            pdf_path=args.single_pdf,
            output_dir=args.output_dir,
            subject=args.subject,
            difficulty=args.difficulty,
            topics=args.topics,
            cleanup_images=args.cleanup_images
        )
        
        # Save report
        report_path = Path(args.output_dir) / f"{Path(args.single_pdf).stem}_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        sys.exit(0 if len(report["errors"]) == 0 else 1)
    
    else:
        # Batch mode
        batch_report = orchestrator.process_batch(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            subject=args.subject,
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
