import os
import sys
import json
import re
import argparse
from pathlib import Path
import fitz # PyMuPDF
from typing import List, Dict, cast
from dotenv import load_dotenv

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Load environment variables
env_path = Path(project_root) / 'content_gen' / '.env'
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
from content_gen.scripts.prompts import NATIONAL_EXAM_SYSTEM_PROMPT, NATIONAL_EXAM_EXTRACTION_PROMPT

import time

class NationalExamProcessor:
    def __init__(self, curriculum: str = "Bangladeshi", output_dir: str = "content_gen/data/outputs/national_exams"):
        self.curriculum = curriculum
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.router = ModelRoutingEngine()

    def extract_text(self, pdf_path: Path) -> str:
        doc = fitz.open(str(pdf_path))
        text = ""
        for page in doc:
            text += cast(str, page.get_text("text"))
        doc.close()
        return text

    def process_pdf(self, pdf_path: str):
        path = Path(pdf_path)
        print(f"\n📄 Processing: {path.name}")
        
        # 1. Extract
        full_text = self.extract_text(path)
        
        # 2. Segment
        questions = TextSegmentationUtility.segment_exam(full_text)
        print(f"🔍 Found {len(questions)} questions in {path.name}")
        
        processed_results = []
        
        # 3. Generate Content
        for q in questions:
            print(f"  🤖 Generating content for Q{q['question_number']} ({q['type']})...")
            
            options_text = ""
            for k, v in q['options'].items():
                options_text += f"{k}. {v}\n"
            
            prompt = NATIONAL_EXAM_EXTRACTION_PROMPT.replace(
                "[Curriculum]", self.curriculum
            ).format(
                question_text=q['question_text'],
                options_text=options_text or "No options",
                question_type=q['type']
            )
            
            success = False
            retries = 3
            while not success and retries > 0:
                try:
                    response = self.router.generate_content(
                        prompt=prompt,
                        task_type="generation",
                        system_prompt=NATIONAL_EXAM_SYSTEM_PROMPT.replace("[Curriculum]", self.curriculum)
                    )
                    
                    # Parse markers
                    cc = self._extract_marker(response, "CC")
                    de = self._extract_marker(response, "DE")
                    oe = self._extract_marker(response, "OE")
                    
                    # Final check for OE if not MCQ
                    if q['type'] != "MCQ":
                        oe = ""
                    
                    processed_results.append({
                        "question_number": q['question_number'],
                        "section": q['section'],
                        "type": q['type'],
                        "question_text": q['question_text'],
                        "options": q['options'],
                        "core_concept": cc,
                        "detailed_explanation": de,
                        "option_wise_explanation": oe,
                        "raw_response": response
                    })
                    success = True
                    # Small cooling period
                    time.sleep(1)
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        print(f"    ⚠️ Rate limit hit. Sleeping for 10s... (Retries left: {retries})")
                        time.sleep(10)
                        retries -= 1
                    else:
                        print(f"    ❌ Error: {e}")
                        break
        
        # 4. Save results
        output_file = self.output_dir / f"{path.stem}_processed.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_results, f, indent=2, ensure_ascii=False)
        
        # Also save a human-readable text version
        txt_output = self.output_dir / f"{path.stem}_processed.txt"
        with open(txt_output, 'w', encoding='utf-8') as f:
            for res in processed_results:
                f.write(f"{res['section']} Question {res['question_number']}\n")
                f.write(f"{'='*30}\n")
                f.write(f"Question: {res['question_text']}\n")
                if res['options']:
                    f.write("Options:\n")
                    for k, v in res['options'].items():
                        f.write(f"  {k}. {v}\n")
                f.write(f"\nCore Concept:\n{res['core_concept']}\n")
                f.write(f"\nDetailed Explanation:\n{res['detailed_explanation']}\n")
                if res['option_wise_explanation']:
                    f.write(f"\nOption Wise Explanation:\n{res['option_wise_explanation']}\n")
                f.write(f"\n{'-'*50}\n\n")

        print(f"✅ Finished! Outputs saved in {self.output_dir}")

    def _extract_marker(self, text: str, marker: str) -> str:
        pattern = f'\\[{marker}_START\\](.*?)\\[{marker}_END\\]'
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
        default="Bangladeshi",
        help="Curriculum name (e.g. Bangladeshi, Indian, etc.)",
    )
    args = parser.parse_args()

    processor = NationalExamProcessor(curriculum=args.curriculum, output_dir=args.output_dir)
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
