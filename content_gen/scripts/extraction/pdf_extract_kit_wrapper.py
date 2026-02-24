#!/usr/bin/env python3
"""
PDF-Extract-Kit Wrapper
Unified interface for PDF extraction using PDF-Extract-Kit AI models
Replaces: smart_extract.py, extract_pdf_content.py, extract_diagram.py
"""
import os
import sys
import json
import re
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
    
    def __init__(self, pdf_path: str, output_dir: str = None):
        """
        Initialize PDF extractor
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory for extracted data (defaults to data/extracted relative to script)
        """
        self.pdf_path = pdf_path
        
        # Determine working directory or use provided output_dir
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Default to data/extracted relative to the content_gen root
            script_path = Path(__file__).parent.absolute()
            self.output_dir = script_path.parent.parent / "data" / "extracted"
        self.base_name = Path(pdf_path).stem
        # Create PDF-specific subfolder for images
        self.images_dir = self.output_dir / "images" / self.base_name
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        # Sub-folder for processed text files (relative to data root)
        self.outputs_dir = self.output_dir.parent / "outputs"
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        # Generate standard processed text file in data/outputs
        self._generate_processed_text(output)
        
        print(f"\n✅ Extraction complete!")
        print(f"   Questions: {len(all_questions)}")
        print(f"   JSON: {json_path}")
        print(f"   Text Output: {self.outputs_dir / f'{self.base_name}_processed.txt'}")
        print(f"   Images: {self.images_dir} ({len(list(self.images_dir.glob('*.png')))} files)")
        
        return output
    
    def _process_page(self, page, page_num: int, doc) -> List[Dict]:
        """
        Process a single page using span-level partitioning and coordinate mapping
        """
        if page_num == 1:
            return []
            
        # Detect question numbers with their Y positions
        question_positions = self._detect_question_numbers_with_positions(page)
        if not question_positions:
            return []
            
        questions = {}
        for q_num, _ in question_positions:
            if 1 <= q_num <= 40:
                questions[q_num] = {
                    "question_number": q_num,
                    "page": page_num,
                    "question_text": "",
                    "options": {"A": "", "B": "", "C": "", "D": ""},
                    "stem_images": [],
                    "option_images": {}
                }
        
        # 1. Collect all spans
        all_spans = []
        text_dict = page.get_text("dict")
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if not span["text"].strip(): continue
                        all_spans.append(span)
        
        # 2. Group spans into questions
        spans_by_question = {q: [] for q in questions}
        for span in all_spans:
            y_mid = (span["bbox"][1] + span["bbox"][3]) / 2
            q_num = self._assign_to_question(y_mid, question_positions, page_num)
            if q_num and q_num in spans_by_question:
                spans_by_question[q_num].append(span)
                
        # 3. Process each question
        for q_num, spans in spans_by_question.items():
            if not spans: continue
            
            # Group into Visual Lines
            spans.sort(key=lambda s: (s["bbox"][1] + s["bbox"][3]) / 2)
            visual_lines = []
            if spans:
                current_line = [spans[0]]
                for s in spans[1:]:
                    last_y_mid = (current_line[-1]["bbox"][1] + current_line[-1]["bbox"][3]) / 2
                    curr_y_mid = (s["bbox"][1] + s["bbox"][3]) / 2
                    if abs(curr_y_mid - last_y_mid) < 9:
                        current_line.append(s)
                    else:
                        visual_lines.append(current_line)
                        current_line = [s]
                visual_lines.append(current_line)
                
            current_field = "question_text"
            
            for vline in visual_lines:
                vline.sort(key=lambda s: s["bbox"][0])
                line_main_size = max(s["size"] for s in vline)
                line_baselines = [s["bbox"][1] for s in vline if abs(s["size"] - line_main_size) < 0.5]
                line_avg_baseline = sum(line_baselines) / len(line_baselines) if line_baselines else vline[0]["bbox"][1]
                
                # Robust Marker Detection (A-D)
                marker_indices = []
                for i, span in enumerate(vline):
                    txt = span["text"].strip().rstrip('.')
                    font = span["font"].lower()
                    x = span["bbox"][0]
                    # Markers are Bold A-D at specific columns
                    known_cols = [70, 81, 170, 181, 270, 281, 370, 381]
                    is_bold = "bold" in font or "bold" in span.get("flags_str", "").lower()
                    if txt in ["A", "B", "C", "D"] and is_bold and any(abs(x - c) < 15 for c in known_cols):
                        marker_indices.append((i, txt))
                
                if marker_indices:
                    # Handle text before first marker
                    if marker_indices[0][0] > 0:
                        prefix_text = self._reconstruct_line_text(vline[0:marker_indices[0][0]], line_avg_baseline, line_main_size)
                        prefix_text = self._clean_noise(prefix_text)
                        if prefix_text:
                            if current_field == "question_text":
                                questions[q_num]["question_text"] += " " + prefix_text
                            else:
                                questions[q_num]["options"][current_field] += " " + prefix_text
                    
                    for m_idx in range(len(marker_indices)):
                        start_idx, opt_letter = marker_indices[m_idx]
                        end_idx = marker_indices[m_idx+1][0] if m_idx+1 < len(marker_indices) else len(vline)
                        opt_text = self._reconstruct_line_text(vline[start_idx+1:end_idx], line_avg_baseline, line_main_size)
                        opt_text = self._clean_noise(opt_text)
                        questions[q_num]["options"][opt_letter] += " " + opt_text
                        current_field = opt_letter
                else:
                    line_text = self._reconstruct_line_text(vline, line_avg_baseline, line_main_size)
                    line_text = self._clean_noise(line_text)
                    if line_text:
                        if current_field == "question_text":
                            if not questions[q_num]["question_text"]:
                                line_text = re.sub(r'^\d+[\.\s]*', '', line_text)
                            questions[q_num]["question_text"] += " " + line_text
                        else:
                            questions[q_num]["options"][current_field] += " " + line_text

        # Handle images
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        temp_img_path = self.images_dir / f"_temp_page_{page_num}.png"
        pix.save(str(temp_img_path))
        results = self.layout_detector.predict_images(str(temp_img_path), str(self.images_dir))
        layout_result = results[0]
        boxes = layout_result.boxes
        
        for box in boxes:
            cls = int(box.cls[0])
            xyxy = box.xyxy[0].tolist()
            pdf_bbox = [c / 2 for c in xyxy]
            y_mid = (pdf_bbox[1] + pdf_bbox[3]) / 2
            type_name = self.layout_detector.model.id_to_names.get(cls, "unknown")
            
            if type_name in ["figure", "table", "isolate_formula"]:
                q_num = self._assign_to_question(y_mid, question_positions, page_num)
                if q_num and q_num in questions:
                    img_path = self._extract_bbox_image(page, pdf_bbox, q_num, type_name)
                    questions[q_num]["stem_images"].append(str(img_path))
        temp_img_path.unlink()
        
        # Cleanup
        for q in questions.values():
            q["question_text"] = q["question_text"].strip()
            q["question_text"] = re.sub(r'^(\d+[\.\s]*)+', '', q["question_text"])
            for opt in q["options"]:
                # Clean up options and remove trailing artifacts like single digits or underscores
                val = q["options"][opt].strip()
                val = re.sub(r'\s+[\d_]$', '', val)
                q["options"][opt] = val
        
        return list(questions.values())

    def _clean_noise(self, text: str) -> str:
        """Filter global noise from reconstructed text parts"""
        text = re.sub(r'\d{4}/\d{2}/\w+/\d{2}', '', text)
        text = re.sub(r'© UCLES.*', '', text, flags=re.I)
        text = re.sub(r'\[Turn over', '', text, flags=re.I)
        return text.strip()

    def _reconstruct_line_text(self, spans: List[Dict], avg_baseline: float, main_size: float) -> str:
        """Helper to reconstruct text with markup from a list of spans on one line"""
        if not spans: return ""
        parts = []
        for span in spans:
            text = span["text"]
            size = span["size"]
            top = span["bbox"][1]
            
            if size < main_size * 0.9:
                if top < avg_baseline - 1: parts.append(f"^{text}")
                elif top > avg_baseline + 1: parts.append(f"_{text}")
                else: parts.append(text)
            else:
                parts.append(text)
        return "".join(parts).strip()

    def _generate_processed_text(self, output_data: Dict):
        """Generate the standard processed text file in data/outputs following prompts.py"""
        text_path = self.outputs_dir / f"{self.base_name}_processed.txt"
        
        # Group duplicates (e.g. question split across pages)
        final_questions = {}
        for q in output_data["questions"]:
            num = q["question_number"]
            if 1 <= num <= 40:
                if num not in final_questions:
                    final_questions[num] = q
                else:
                    # Merge content
                    if q["question_text"]:
                        final_questions[num]["question_text"] += " " + q["question_text"]
                    for opt in ["A", "B", "C", "D"]:
                        if q["options"][opt]:
                            final_questions[num]["options"][opt] += " " + q["options"][opt]
                    final_questions[num]["stem_images"].extend(q["stem_images"])
        
        sorted_qs = sorted(final_questions.values(), key=lambda x: x["question_number"])
        
        with open(text_path, 'w', encoding='utf-8') as f:
            for q in sorted_qs:
                f.write(f"Question {q['question_number']}Question and Options in Text Format\n\n")
                
                # Question text
                f.write(f"{q['question_text'].strip()}\n\n")
                
                # Options
                opts = q["options"]
                # Match the reference format: A. Text B. Text ...
                opt_str = f"A. {opts['A']} B. {opts['B']} C. {opts['C']} D. {opts['D']}"
                f.write(f"{opt_str.strip()}\n\n")
                
                f.write("Detailed Explanation of the Question and Right Answer\n\n")
                f.write("[EXPLANATION_PLACEHOLDER]\n\n")
                f.write("Option Wise Explanation (Detailed)\n\n")
                f.write("[OPTION_EXPLANATION_PLACEHOLDER]\n\n")
                f.write("### 🧠 Concept Gap Analysis and Flashcards\n\n")
                f.write("[FLASHCARDS_PLACEHOLDER]\n\n")
                f.write("-" * 50 + "\n\n")
    
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
                    
                    # Skip paper codes/footers that look like numbers
                    if re.search(r'\d{4}/\d{2}/\w+/\d{2}', line_text): continue
                    if "© UCLES" in line_text: continue
                    
                    # Check X position first - must be left-aligned
                    x_pos = line["bbox"][0]
                    if x_pos >= 100:
                        continue  # Skip indented lines (answer options)
                    
                    # Pattern 1: Number on same line as question text (Q10+)
                    match = re.match(r'^(\d+)\s+([A-Z\d])', line_text)
                    if match:
                        q_num = int(match.group(1))
                        if 1 <= q_num <= 40: # STRICT LIMIT
                            y_pos = line["bbox"][1]
                            question_positions.append((q_num, y_pos))
                            continue
                    
                    # Pattern 2: Number on separate line (Q1-9)
                    if re.match(r'^\d+$', line_text):
                        q_num = int(line_text)
                        if 1 <= q_num <= 40: # STRICT LIMIT
                            # Check next line/block for validation
                            is_question = False
                            
                            # Validation: next line should start with a Capital letter 
                            # AND NOT look like a paper code
                            check_text = ""
                            if i + 1 < len(block["lines"]):
                                for span in block["lines"][i + 1]["spans"]:
                                    check_text += span["text"]
                            elif block_idx + 1 < len(blocks):
                                next_block = blocks[block_idx + 1]
                                if "lines" in next_block and len(next_block["lines"]) > 0:
                                    for span in next_block["lines"][0]["spans"]:
                                        check_text += span["text"]
                            
                            check_text = check_text.strip()
                            if check_text and check_text[0].isupper():
                                if not re.search(r'\d{4}/\d{2}/\w+/\d{2}', check_text):
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
