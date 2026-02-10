#!/usr/bin/env python3
"""
PDF-Extract-Kit Wrapper
Unified interface for PDF extraction using PDF-Extract-Kit AI models
Replaces: smart_extract.py, extract_pdf_content.py, extract_diagram.py
"""
import os
import sys
import json
import fitz
from pathlib import Path
from typing import Dict, List, Optional

# Add PDF-Extract-Kit to path - use absolute path
SCRIPT_DIR = Path(__file__).parent.absolute()
KIT_PATH = SCRIPT_DIR.parent.parent / "tools" / "PDF-Extract-Kit"
sys.path.insert(0, str(KIT_PATH))

from pdf_extract_kit.utils.config_loader import load_config, initialize_tasks_and_models
import pdf_extract_kit.tasks  # Trigger registration


class PDFExtractKitWrapper:
    """
    Wrapper for PDF-Extract-Kit that provides a simple interface
    compatible with the old smart_extract.py output format
    """
    
    def __init__(self, pdf_path: str, output_dir: str = "content_gen/data/extracted"):
        """
        Initialize PDF extractor
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory for extracted data
        """
        self.pdf_path = pdf_path
        self.output_dir = Path(output_dir)
        self.base_name = Path(pdf_path).stem
        # Create PDF-specific subfolder for images
        self.images_dir = self.output_dir / "images" / self.base_name
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize PDF-Extract-Kit models
        self._init_models()
        
    def _init_models(self):
        """Initialize PDF-Extract-Kit AI models"""
        # Configuration for layout detection
        config = {
            "tasks": {
                "layout_detection": {
                    "model": "layout_detection_yolo",
                    "model_config": {
                        "img_size": 1280,
                        "conf_thres": 0.25,
                        "iou_thres": 0.45,
                        "model_path": str(KIT_PATH / "models/Layout/YOLO/doclayout_yolo_ft.pt"),
                        "device": "cpu"  # Change to "cuda" if GPU available
                    }
                }
            }
        }
        
        print("🤖 Initializing PDF-Extract-Kit AI models...")
        task_instances = initialize_tasks_and_models(config)
        self.layout_detector = task_instances["layout_detection"]
        print("✅ Models loaded successfully")
        
    def extract(self) -> Dict:
        """
        Extract questions and diagrams from PDF
        
        Returns:
            Dictionary with structure:
            {
                "source": "path/to/pdf",
                "questions": [
                    {
                        "question_number": 1,
                        "page": 1,
                        "stem_images": ["q1_stem.png"],
                        "option_images": {"A": ["q1_opt_A.png"], ...}
                    }
                ]
            }
        """
        doc = fitz.open(self.pdf_path)
        all_questions = []
        
        print(f"📄 Processing: {self.pdf_path}")
        print(f"   Pages: {len(doc)}")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            questions_on_page = self._process_page(page, page_num + 1, doc)
            all_questions.extend(questions_on_page)
            
        doc.close()
        
        output = {
            "source": self.pdf_path,
            "base_name": self.base_name,
            "questions": all_questions
        }
        
        # Save JSON
        json_path = self.output_dir / f"{self.base_name}_extracted.json"
        with open(json_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✅ Extraction complete!")
        print(f"   Questions: {len(all_questions)}")
        print(f"   JSON: {json_path}")
        print(f"   Images: {self.images_dir} ({len(list(self.images_dir.glob('*.png')))} files)")
        
        return output
    
    def _process_page(self, page, page_num: int, doc) -> List[Dict]:
        """
        Process a single page using PDF-Extract-Kit
        
        Args:
            page: PyMuPDF page object
            page_num: Page number (1-indexed)
            doc: PyMuPDF document object
            
        Returns:
            List of question dictionaries
        """
        # Render page to image for AI detection
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        temp_img_path = self.images_dir / f"_temp_page_{page_num}.png"
        pix.save(str(temp_img_path))
        
        # Run layout detection
        results = self.layout_detector.predict_images(str(temp_img_path), str(self.images_dir))
        layout_result = results[0]
        boxes = layout_result.boxes
        
        # Detect question numbers with their Y positions
        question_positions = self._detect_question_numbers_with_positions(page)
        
        # Process detected elements
        questions = {}
        
        for box in boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()  # [x0, y0, x1, y1] in pixels
            
            # Map back to PDF coordinates (we used matrix(2,2))
            pdf_bbox = [c / 2 for c in xyxy]
            y_mid = (pdf_bbox[1] + pdf_bbox[3]) / 2
            
            type_name = self.layout_detector.model.id_to_names.get(cls, "unknown")
            
            # Only process figures, tables, and formulas
            if type_name in ["figure", "table", "isolate_formula"]:
                # Assign to question number based on Y position
                q_num = self._assign_to_question(y_mid, question_positions, page_num)
                
                if q_num:
                    if q_num not in questions:
                        questions[q_num] = {
                            "question_number": q_num,
                            "page": page_num,
                            "stem_images": [],
                            "option_images": {}
                        }
                    
                    # Extract and save image
                    img_path = self._extract_bbox_image(page, pdf_bbox, q_num, type_name)
                    
                    # Categorize as stem or option image
                    # For now, treat all as stem images (can be enhanced with option detection)
                    questions[q_num]["stem_images"].append(str(img_path))
        
        # Clean up temp image
        temp_img_path.unlink()
        
        return list(questions.values())
    
    def _detect_question_numbers_with_positions(self, page) -> List[tuple]:
        """
        Detect question numbers and their Y positions
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            List of (question_number, y_position) tuples
        """
        import re
        
        # Get text with position info
        blocks = page.get_text("dict")["blocks"]
        question_positions = []
        
        for block_idx, block in enumerate(blocks):
            if "lines" in block:
                for i, line in enumerate(block["lines"]):
                    # Get line text
                    line_text = ""
                    for span in line["spans"]:
                        line_text += span["text"]
                    
                    line_text = line_text.strip()
                    
                    # Check X position first - must be left-aligned
                    x_pos = line["bbox"][0]
                    if x_pos >= 100:
                        continue  # Skip indented lines (answer options)
                    
                    # Pattern 1: Number on same line as question text (Q10+)
                    # Examples: "10 Methanol...", "12 A student...", "35 1-chloro...", "17 Q, R and S..."
                    match = re.match(r'^(\d+)\s+([A-Z\d])', line_text)
                    if match:
                        q_num = int(match.group(1))
                        if 1 <= q_num <= 50:
                            y_pos = line["bbox"][1]
                            question_positions.append((q_num, y_pos))
                            continue
                    
                    # Pattern 2: Number on separate line (Q1-9)
                    # Example: "1" followed by "A Boltzmann distribution..."
                    if re.match(r'^\d+$', line_text):
                        q_num = int(line_text)
                        if 1 <= q_num <= 50:
                            # Check next line in same block
                            is_question = False
                            
                            if i + 1 < len(block["lines"]):
                                next_line_text = ""
                                for span in block["lines"][i + 1]["spans"]:
                                    next_line_text += span["text"]
                                next_line_text = next_line_text.strip()
                                
                                if next_line_text and next_line_text[0].isupper():
                                    # Filter out chemical formulas
                                    if not (len(next_line_text) == 1 or (len(next_line_text) >= 2 and next_line_text[1].isdigit())):
                                        is_question = True
                            
                            # If not found in same block, check next block
                            if not is_question and block_idx + 1 < len(blocks):
                                next_block = blocks[block_idx + 1]
                                if "lines" in next_block and len(next_block["lines"]) > 0:
                                    next_line_text = ""
                                    for span in next_block["lines"][0]["spans"]:
                                        next_line_text += span["text"]
                                    next_line_text = next_line_text.strip()
                                    
                                    if next_line_text and next_line_text[0].isupper():
                                        # Filter out chemical formulas
                                        if not (len(next_line_text) == 1 or (len(next_line_text) >= 2 and next_line_text[1].isdigit())):
                                            is_question = True
                            
                            if is_question:
                                y_pos = line["bbox"][1]
                                question_positions.append((q_num, y_pos))
        
        # Sort by Y position (top to bottom)
        return sorted(question_positions, key=lambda x: x[1])
    
    def _assign_to_question(
        self, 
        y_pos: float, 
        question_positions: List[tuple], 
        page_num: int
    ) -> Optional[int]:
        """
        Assign a detected element to a question number based on Y position
        
        Args:
            y_pos: Y coordinate of element
            question_positions: List of (question_num, y_position) tuples
            page_num: Current page number
            
        Returns:
            Question number or None
        """
        if not question_positions:
            # No questions detected on this page, skip this element
            return None
        
        # Find the question this element belongs to
        # Element belongs to the question above it (closest question with y < element_y)
        for i in range(len(question_positions) - 1, -1, -1):
            q_num, q_y = question_positions[i]
            if y_pos >= q_y:  # Element is below this question
                return q_num
        
        # If element is above all questions, assign to first question
        return question_positions[0][0]
    
    def _extract_bbox_image(
        self, 
        page, 
        bbox: List[float], 
        q_num: int, 
        element_type: str
    ) -> Path:
        """
        Extract and save image from bounding box
        
        Args:
            page: PyMuPDF page object
            bbox: Bounding box [x0, y0, x1, y1]
            q_num: Question number
            element_type: Type of element (figure, table, formula)
            
        Returns:
            Path to saved image
        """
        # Minimal padding for tight clipping - no surrounding text
        pad = 5  # Just enough to avoid cutting edges
            
        final_bbox = [
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(page.rect.width, bbox[2] + pad),
            min(page.rect.height, bbox[3] + pad)
        ]
        
        # Generate filename
        img_name = f"q{q_num}_{element_type}.png"
        img_path = self.images_dir / img_name
        
        # Extract high-resolution image
        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=fitz.Rect(final_bbox))
        pix.save(str(img_path))
        
        return img_path


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract questions from PDF using PDF-Extract-Kit")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--output-dir", default="content_gen/data/extracted", help="Output directory")
    
    args = parser.parse_args()
    
    extractor = PDFExtractKitWrapper(args.pdf_path, args.output_dir)
    extractor.extract()


if __name__ == "__main__":
    main()
