#!/usr/bin/env python3
"""
PDF-Extract-Kit Wrapper
Unified interface for PDF extraction using PDF-Extract-Kit AI models
Replaces: smart_extract.py, extract_pdf_content.py, extract_diagram.py
"""
import os
import sys
from pathlib import Path

# Add PDF-Extract-Kit to path - MUST happen before local imports
KIT_PATH = Path(__file__).parent.parent.parent / "tools" / "PDF-Extract-Kit"
if str(KIT_PATH) not in sys.path:
    sys.path.insert(0, str(KIT_PATH))

try:
    import pdf_extract_kit.tasks  # Trigger registration
    from pdf_extract_kit.utils.config_loader import load_config, initialize_tasks_and_models
    HAS_KIT = True
except (ImportError, ModuleNotFoundError):
    HAS_KIT = False
    initialize_tasks_and_models = None
    print("⚠️ PDF-Extract-Kit not found. Extraction features using this engine will be disabled.")
import json
import re
import fitz
from typing import Dict, List, Optional, Callable


class PDFExtractKitWrapper:
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
    ):
        """
        Initialize PDF extractor

        Args:
            pdf_path: Optional path to PDF file
            output_dir: Optional output directory
            use_gpu: Whether to use GPU for models
        """
        self.use_gpu = use_gpu
        self.pdf_path = pdf_path
        self.output_dir = Path(output_dir) if output_dir else None
        self.min_question_number = min_question_number
        self.max_question_number = max_question_number
        self.question_detection_mode = question_detection_mode

        # Determine working directory or use provided output_dir
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Default to data/extracted relative to the content_gen root
            script_path = Path(__file__).parent.absolute()
            self.output_dir = script_path.parent.parent / "data" / "extracted"
        if self.pdf_path:
            self.base_name = Path(self.pdf_path).stem
            # Create PDF-specific subfolder for images
            self.images_dir = self.output_dir / "images" / self.base_name
            self.images_dir.mkdir(parents=True, exist_ok=True)

            # Sub-folder for processed text files (relative to data root)
            self.outputs_dir = self.output_dir.parent / "outputs"
            self.outputs_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.base_name = None
            self.images_dir = None
            self.outputs_dir = None

        # Initialize PDF-Extract-Kit models
        self._init_models()

    def _init_models(self):
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
                        "device": device
                    }
                }
            }
        }

        print("🤖 Initializing PDF-Extract-Kit AI models...")
        task_instances = initialize_tasks_and_models(config)
        self.layout_detector = task_instances["layout_detection"]
        print("✅ Models loaded successfully")

    def extract(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict:
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
        if not HAS_KIT:
            raise RuntimeError("Extraction failed: PDF-Extract-Kit is not installed or found in tools/")
        if not self.pdf_path:
            raise ValueError("pdf_path must be set before calling extract()")
        if not self.output_dir or not self.base_name or not self.images_dir or not self.outputs_dir:
            raise ValueError(
                "output_dir/base_name/images_dir/outputs_dir must be initialized before calling extract()"
            )
        if self.layout_detector is None:
            raise RuntimeError("Layout detector is not initialized")

        doc = fitz.open(self.pdf_path)
        all_questions = []

        print(f"📄 Processing: {self.pdf_path}")
        print(f"   Pages: {len(doc)}")
        
        if progress_callback:
            progress_callback(25, "Extracting diagrams and images via Vision AI...")

        last_q_num = None
        for page_num in range(len(doc)):
            page = doc[page_num]
            questions_on_page, last_q_num = self._process_page(page, page_num + 1, doc, last_q_num)
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
            }
        }

        # Save JSON
        json_path = self.output_dir / f"{self.base_name}_extracted.json"
        with open(json_path, 'w') as f:
            json.dump(output, f, indent=2)

        # Generate standard processed text file in data/outputs
        self._generate_processed_text(output)

        print(f"\n✅ Extraction complete!")
        print(f"   Questions: {len(merged_questions)}")
        print(f"   JSON: {json_path}")
        print(
            f"   Text Output: {self.outputs_dir / f'{self.base_name}_processed.txt'}")
        print(
            f"   Images: {self.images_dir} ({len(list(self.images_dir.glob('*.png')))} files)")

        return output

    def extract_questions(self, source_path: str, output_dir: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict:
        """
        Adapter-compatible extraction method
        """
        self.pdf_path = source_path
        self.output_dir = Path(output_dir)
        self.base_name = Path(source_path).stem
        
        # Create PDF-specific subfolder for images
        self.images_dir = self.output_dir / "images" / self.base_name
        self.images_dir.mkdir(parents=True, exist_ok=True)

        # Sub-folder for processed text files (relative to data root)
        self.outputs_dir = self.output_dir.parent / "outputs"
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

        return self.extract(progress_callback=progress_callback)

    def _process_page(self, page, page_num: int, doc, last_q_num: Optional[int] = None) -> tuple[List[Dict], Optional[int]]:
        """
        Process a single page using span-level partitioning and coordinate mapping.
        Returns (list of question fragments, updated last_q_num).
        """
        # Detect question numbers with their Y positions
        question_positions = self._detect_question_numbers_with_positions(page)
        
        # If no questions on this page, but we have a last_q_num from previous page,
        # treat the entire page as a continuation of that question.
        if not question_positions:
            if last_q_num:
                # Use a dummy position for the whole page
                question_positions = [(last_q_num, 0)]
            else:
                # Still no starting point, likely a cover page or instructions
                return [], None

        questions = {}
        new_last_q_num = last_q_num
        
        for q_num, _ in question_positions:
            if self._is_valid_question_number(q_num):
                questions[q_num] = {
                    "question_number": q_num,
                    "page": page_num,
                    "question_text": "",
                    "options": {"A": "", "B": "", "C": "", "D": ""},
                    "stem_images": [],
                    "option_images": {}
                }
                new_last_q_num = q_num

        # 1. Collect all spans
        all_spans = []
        text_dict = page.get_text("dict")
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if not span["text"].strip():
                            continue
                        all_spans.append(span)

        # 2. Group spans into questions
        spans_by_question = {q: [] for q in questions}
        for span in all_spans:
            y_mid = (span["bbox"][1] + span["bbox"][3]) / 2
            q_num = self._assign_to_question(
                y_mid, question_positions, page_num)
            if q_num and q_num in spans_by_question:
                spans_by_question[q_num].append(span)

        # 3. Process each question
        for q_num, spans in spans_by_question.items():
            if not spans:
                continue

            # Group into Visual Lines
            spans.sort(key=lambda s: (s["bbox"][1] + s["bbox"][3]) / 2)
            visual_lines = []
            if spans:
                current_line = [spans[0]]
                for s in spans[1:]:
                    last_y_mid = (
                        current_line[-1]["bbox"][1] + current_line[-1]["bbox"][3]) / 2
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
                line_baselines = [s["bbox"][1] for s in vline if abs(
                    s["size"] - line_main_size) < 0.5]
                line_avg_baseline = sum(
                    line_baselines) / len(line_baselines) if line_baselines else vline[0]["bbox"][1]

                # Robust Marker Detection (A-D)
                marker_indices = []
                for i, span in enumerate(vline):
                    txt = span["text"].strip().rstrip('.')
                    font = span["font"].lower()
                    x = span["bbox"][0]
                    # Markers are Bold A-D at specific columns
                    known_cols = [70, 81, 170, 181, 270, 281, 370, 381]
                    is_bold = "bold" in font or "bold" in span.get(
                        "flags_str", "").lower()
                    if txt in ["A", "B", "C", "D"] and is_bold and any(abs(x - c) < 15 for c in known_cols):
                        marker_indices.append((i, txt))

                if marker_indices:
                    # Handle text before first marker
                    if marker_indices[0][0] > 0:
                        prefix_text = self._reconstruct_line_text(
                            vline[0:marker_indices[0][0]], line_avg_baseline, line_main_size)
                        prefix_text = self._clean_noise(prefix_text)
                        if prefix_text:
                            if current_field == "question_text":
                                questions[q_num]["question_text"] += " " + \
                                    prefix_text
                            else:
                                questions[q_num]["options"][current_field] += " " + \
                                    prefix_text

                    for m_idx in range(len(marker_indices)):
                        start_idx, opt_letter = marker_indices[m_idx]
                        end_idx = marker_indices[m_idx+1][0] if m_idx + \
                            1 < len(marker_indices) else len(vline)
                        opt_text = self._reconstruct_line_text(
                            vline[start_idx+1:end_idx], line_avg_baseline, line_main_size)
                        opt_text = self._clean_noise(opt_text)
                        questions[q_num]["options"][opt_letter] += " " + opt_text
                        current_field = opt_letter
                else:
                    line_text = self._reconstruct_line_text(
                        vline, line_avg_baseline, line_main_size)
                    line_text = self._clean_noise(line_text)
                    if line_text:
                        if current_field == "question_text":
                            if not questions[q_num]["question_text"]:
                                line_text = re.sub(
                                    r'^\d+[\.\s]*', '', line_text)
                            questions[q_num]["question_text"] += " " + line_text
                        else:
                            questions[q_num]["options"][current_field] += " " + line_text

        # Handle images
        layout_detector = self.layout_detector
        if layout_detector is None:
            raise RuntimeError("Layout detector is not initialized")
        images_dir = self.images_dir
        if images_dir is None:
            raise ValueError("images_dir must be initialized before processing page images")
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        temp_img_path = images_dir / f"_temp_page_{page_num}.png"
        pix.save(str(temp_img_path))
        results = layout_detector.predict_images(
            str(temp_img_path), str(images_dir))
        layout_result = results[0]
        boxes = layout_result.boxes

        for box in boxes:
            cls = int(box.cls[0])
            xyxy = box.xyxy[0].tolist()
            pdf_bbox = [c / 2 for c in xyxy]
            y_mid = (pdf_bbox[1] + pdf_bbox[3]) / 2
            type_name = layout_detector.model.id_to_names.get(
                cls, "unknown")

            if type_name in ["figure", "table", "isolate_formula"]:
                q_num = self._assign_to_question(
                    y_mid, question_positions, page_num)
                if q_num and q_num in questions:
                    img_path = self._extract_bbox_image(
                        page, pdf_bbox, q_num, type_name)
                    questions[q_num]["stem_images"].append(str(img_path))
        temp_img_path.unlink()

        # Cleanup
        for q in questions.values():
            q["question_text"] = q["question_text"].strip()
            q["question_text"] = re.sub(
                r'^(\d+[\.\s]*)+', '', q["question_text"])
            for opt in q["options"]:
                # Clean up options and remove trailing artifacts like single digits or underscores
                val = q["options"][opt].strip()
                val = re.sub(r'\s+[\d_]$', '', val)
                q["options"][opt] = val

        return list(questions.values()), new_last_q_num

    def _clean_noise(self, text: str) -> str:
        """Filter global noise and map symbols from reconstructed text parts"""
        # Symbol mapping for common Greek/Math characters found in Cambridge papers
        symbol_map = {
            "\uf070": "π",
            "\uf061": "α",
            "\uf062": "β",
            "\uf067": "γ",
            "\uf044": "Δ",
            "\uf0b0": "°",
            "\uf0b1": "±",
            "\uf0e6": "(",
            "\uf0f6": ")",
            "\uf0e7": "[",
            "\uf0f7": "]",
            "\uf03d": "=",
            "\uf02b": "+",
            "\uf02d": "–",
            "\uf057": "Ω",
            "\uf0b8": "÷",
        }
        for code, char in symbol_map.items():
            text = text.replace(code, char)
            
        # Paper codes and Cambridge footers
        text = re.sub(r'\d{4}/\d{2}/\w+/\d{2}', '', text)
        text = re.sub(r'© UCLES.*', '', text, flags=re.I)
        text = re.sub(r'\[Turn over', '', text, flags=re.I)
        
        # Robust cleanup for common Cambridge boilerplate noise
        noise_patterns = [
            r'Permission to reproduce items where third-party owned material.*',
            r'reasonable effort has been made by the publisher.*',
            r'To avoid the issue of disclosure of answer-related information.*',
            r'Cambridge Assessment International Education is part of.*',
            r'University of Cambridge Local Examinations Syndicate.*',
            r'Every publisher will be pleased to make amends.*',
            r'Assessment International Education Copyright Acknowledgements.*'
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.I | re.DOTALL)

        return text.strip()

    def _reconstruct_line_text(self, spans: List[Dict], avg_baseline: float, main_size: float) -> str:
        """Helper to reconstruct text with markup from a list of spans on one line"""
        if not spans:
            return ""
        parts = []
        for span in spans:
            text = span["text"]
            size = span["size"]
            top = span["bbox"][1]

            if size < main_size * 0.9:
                if top < avg_baseline - 1:
                    parts.append(f"^{text}")
                elif top > avg_baseline + 1:
                    parts.append(f"_{text}")
                else:
                    parts.append(text)
            else:
                parts.append(text)
        return "".join(parts).strip()

    def _generate_processed_text(self, output_data: Dict):
        """Generate the standard processed text file in data/outputs following prompts.py"""
        outputs_dir = self.outputs_dir
        base_name = self.base_name
        if outputs_dir is None or base_name is None:
            raise ValueError("outputs_dir and base_name must be initialized before generating processed text")
        text_path = outputs_dir / f"{base_name}_processed.txt"

        sorted_qs = sorted(
            output_data.get("questions", []),
            key=lambda x: x["question_number"]
        )

        with open(text_path, 'w', encoding='utf-8') as f:
            for q in sorted_qs:
                f.write(
                    f"Question {q['question_number']}Question and Options in Text Format\n\n")

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

        text_dict = page.get_text("dict")
        blocks = text_dict.get("blocks", [])
        question_positions = []

        # 1. Identify leftmost possible position on page
        min_x = 1000.0
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    min_x = min(min_x, line["bbox"][0])

        for block_idx, block in enumerate(blocks):
            if "lines" in block:
                for i, line in enumerate(block["lines"]):
                    # Get line text
                    line_text = " ".join(span["text"].strip() for span in line["spans"] if span["text"].strip())
                    line_text = line_text.strip()

                    # Skip paper codes/footers that look like numbers
                    if re.search(r'\d{4}/\d{2}/\w+/\d{2}', line_text):
                        continue
                    if "© UCLES" in line_text:
                        continue

                    # Check position: Question numbers are typically near the leftmost edge
                    x_pos = line["bbox"][0]
                    # Allow up to 50px indentation from the leftmost text element
                    if x_pos > min_x + 50 and x_pos > 150:
                        continue

                    # Pattern 1: Number + Text/Marker on same line
                    if self.question_detection_mode == "strict":
                        marker_pattern = r'^(\d+)\s+([A-Z][a-z]+)'
                    elif self.question_detection_mode == "open":
                        marker_pattern = r'^(\d+)[\.\s]*([A-Z\d\(\\]|$)'
                    else: # balanced
                        # More inclusive: allow space or dot, and any uppercase or special starter
                        marker_pattern = r'^(\d+)[\.\s]*([A-Z]|\\|\(|\$|[a-z]{3,})'
                        
                    match = re.match(marker_pattern, line_text)
                    if match:
                        q_num = int(match.group(1))
                        if self._is_valid_question_number(q_num):
                            y_pos = line["bbox"][1]
                            question_positions.append((q_num, y_pos))
                            continue

                    # Pattern 2: Number on separate line (Q1-9 often)
                    # Allow optional trailing dot
                    if re.match(r'^(\d+)[\.]?$', line_text):
                        q_num_match = re.match(r'^(\d+)', line_text)
                        q_num = int(q_num_match.group(1))
                        if self._is_valid_question_number(q_num):
                            # Check next line/block for validation (should look like a question)
                            is_question = False
                            check_text = ""
                            if i + 1 < len(block["lines"]):
                                check_text = " ".join(s["text"] for s in block["lines"][i + 1]["spans"]).strip()
                            elif block_idx + 1 < len(blocks):
                                next_block = blocks[block_idx + 1]
                                if "lines" in next_block and len(next_block["lines"]) > 0:
                                    check_text = " ".join(s["text"] for s in next_block["lines"][0]["spans"]).strip()

                            # Looser validation: just needs to NOT be a footer or very short
                            if len(check_text) > 3:
                                if not re.search(r'\d{4}/\d{2}/\w+/\d{2}', check_text):
                                    is_question = True

                            if is_question:
                                y_pos = line["bbox"][1]
                                question_positions.append((q_num, y_pos))

        # Sort by Y position and de-duplicate by question number (keep first sighting per page).
        sorted_positions = sorted(question_positions, key=lambda x: x[1])
        deduped: List[tuple] = []
        seen = set()
        for q_num, y_pos in sorted_positions:
            if q_num in seen:
                continue
            seen.add(q_num)
            deduped.append((q_num, y_pos))
        return deduped

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

        # Footer Guard: Ignore elements at the very bottom of the page (A4 height is 842pt)
        if y_pos > 775:
            return None

        # Find the question this element belongs to
        # Element belongs to the question above it (closest question with y < element_y)
        for i in range(len(question_positions) - 1, -1, -1):
            q_num, q_y = question_positions[i]
            if y_pos >= q_y:  # Element is below this question
                return q_num

        # If element is above all questions, treat it as preamble/instruction noise.
        return None

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
        # Adaptive padding preserves labels/axes around detector boxes.
        width = max(1.0, bbox[2] - bbox[0])
        height = max(1.0, bbox[3] - bbox[1])
        pad = max(12.0, min(width, height) * 0.08)

        final_bbox = [
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(page.rect.width, bbox[2] + pad),
            min(page.rect.height, bbox[3] + pad)
        ]

        # Generate filename
        images_dir = self.images_dir
        if images_dir is None:
            raise ValueError("images_dir must be initialized before extracting images")
        img_name = f"q{q_num}_{element_type}.png"
        img_path = images_dir / img_name

        # Extract high-resolution image
        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3),
                              clip=fitz.Rect(final_bbox))
        pix.save(str(img_path))

        return img_path

    def _merge_questions(self, questions: List[Dict]) -> List[Dict]:
        """Merge question fragments across pages into canonical runtime questions."""
        merged: Dict[int, Dict] = {}
        for q in questions:
            num = q.get("question_number", 0)
            if not self._is_valid_question_number(num):
                continue

            if num not in merged:
                merged[num] = {
                    "question_number": num,
                    "page": q.get("page"),
                    "question_text": (q.get("question_text") or "").strip(),
                    "options": {
                        "A": (q.get("options", {}).get("A", "") or "").strip(),
                        "B": (q.get("options", {}).get("B", "") or "").strip(),
                        "C": (q.get("options", {}).get("C", "") or "").strip(),
                        "D": (q.get("options", {}).get("D", "") or "").strip()
                    },
                    "stem_images": list(dict.fromkeys(q.get("stem_images", []) or [])),
                    "option_images": q.get("option_images", {}) or {}
                }
                continue

            q_text = (q.get("question_text") or "").strip()
            if q_text:
                merged[num]["question_text"] = f"{merged[num]['question_text']} {q_text}".strip()

            for opt in ["A", "B", "C", "D"]:
                opt_text = (q.get("options", {}).get(opt, "") or "").strip()
                if not opt_text:
                    continue
                existing = merged[num]["options"].get(opt, "")
                merged[num]["options"][opt] = f"{existing} {opt_text}".strip()

            merged[num]["stem_images"] = list(dict.fromkeys(
                merged[num]["stem_images"] + (q.get("stem_images", []) or [])
            ))

        return sorted(merged.values(), key=lambda item: item["question_number"])

    def _is_valid_question_number(self, number: int) -> bool:
        """Question number guardrails, configurable per curriculum/run."""
        if number < self.min_question_number:
            return False
        if self.max_question_number is not None and number > self.max_question_number:
            return False
        return True


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract questions from PDF using PDF-Extract-Kit")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument(
        "--output-dir", default="content_gen/data/extracted", help="Output directory")

    args = parser.parse_args()

    extractor = PDFExtractKitWrapper(args.pdf_path, args.output_dir)
    extractor.extract()


if __name__ == "__main__":
    main()
