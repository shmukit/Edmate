"""Per-page layout and text partitioning for PDF-Extract-Kit wrapper."""
from __future__ import annotations

import re
from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import fitz


class KitPageProcessorMixin:
    # --- cross-mixin attribute dependencies (set by PDFExtractKitWrapper.__init__) ---
    layout_detector: Optional[Any]
    images_dir: Optional[Path]
    question_detection_mode: str
    min_question_number: int
    max_question_number: Optional[int]

    # --- cross-mixin method dependencies (provided by sibling mixins) ---
    @abstractmethod
    def _clean_noise(self, text: str | None) -> str: ...

    @abstractmethod
    def _reconstruct_line_text(
        self, spans: List[Dict], avg_baseline: float, main_size: float
    ) -> str: ...

    @abstractmethod
    def _extract_bbox_image(
        self, page: fitz.Page, bbox: List[float], q_num: int, element_type: str
    ) -> Path: ...
    def _process_page(
        self,
        page: fitz.Page,
        page_num: int,
        doc: fitz.Document,
        last_q_num: Optional[int] = None,
    ) -> tuple[List[Dict], Optional[int]]:
        """
        Process a single page using span-level partitioning and coordinate mapping.
        Returns (list of question fragments, updated last_q_num).
        """
        question_positions = self._detect_question_numbers_with_positions(page)

        if not question_positions:
            if last_q_num:
                question_positions = [(last_q_num, 0)]
            else:
                return [], None

        questions: Dict[int, Dict] = {}
        new_last_q_num = last_q_num

        for q_num, _ in question_positions:
            if self._is_valid_question_number(q_num):
                questions[q_num] = {
                    "question_number": q_num,
                    "page": page_num,
                    "question_text": "",
                    "options": {"A": "", "B": "", "C": "", "D": ""},
                    "stem_images": [],
                    "option_images": {},
                }
                new_last_q_num = q_num

        all_spans: List[Dict] = []
        text_dict = cast(Dict, page.get_text("dict"))
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        raw_t = span.get("text")
                        text = "" if raw_t is None else str(raw_t)
                        if not text.strip():
                            continue
                        if span.get("text") != text:
                            span = {**span, "text": text}
                        all_spans.append(span)

        spans_by_question = {q: [] for q in questions}
        for span in all_spans:
            y_mid = (span["bbox"][1] + span["bbox"][3]) / 2
            q_num = self._assign_to_question(y_mid, question_positions, page_num)
            if q_num and q_num in spans_by_question:
                spans_by_question[q_num].append(span)

        for q_num, spans in spans_by_question.items():
            if not spans:
                continue

            spans.sort(key=lambda s: (s["bbox"][1] + s["bbox"][3]) / 2)
            visual_lines: List[List[Dict]] = []
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
                line_baselines = [
                    s["bbox"][1]
                    for s in vline
                    if abs(s["size"] - line_main_size) < 0.5
                ]
                line_avg_baseline = (
                    sum(line_baselines) / len(line_baselines)
                    if line_baselines
                    else vline[0]["bbox"][1]
                )

                marker_indices = []
                for i, span in enumerate(vline):
                    txt = (span.get("text") or "").strip().rstrip(".")
                    font = span["font"].lower()
                    x = span["bbox"][0]
                    known_cols = [70, 81, 170, 181, 270, 281, 370, 381]
                    is_bold = "bold" in font or "bold" in span.get("flags_str", "").lower()
                    if txt in ["A", "B", "C", "D"] and is_bold and any(
                        abs(x - c) < 15 for c in known_cols
                    ):
                        marker_indices.append((i, txt))

                if marker_indices:
                    if marker_indices[0][0] > 0:
                        prefix_text = self._reconstruct_line_text(
                            vline[0 : marker_indices[0][0]],
                            line_avg_baseline,
                            line_main_size,
                        )
                        prefix_text = (self._clean_noise(prefix_text) or "").strip()
                        if prefix_text:
                            if current_field == "question_text":
                                questions[q_num]["question_text"] += " " + prefix_text
                            else:
                                questions[q_num]["options"][current_field] += " " + prefix_text

                    for m_idx in range(len(marker_indices)):
                        start_idx, opt_letter = marker_indices[m_idx]
                        end_idx = (
                            marker_indices[m_idx + 1][0]
                            if m_idx + 1 < len(marker_indices)
                            else len(vline)
                        )
                        opt_text = self._reconstruct_line_text(
                            vline[start_idx + 1 : end_idx],
                            line_avg_baseline,
                            line_main_size,
                        )
                        opt_text = (self._clean_noise(opt_text) or "").strip()
                        questions[q_num]["options"][opt_letter] += " " + opt_text
                        current_field = opt_letter
                else:
                    line_text = self._reconstruct_line_text(
                        vline, line_avg_baseline, line_main_size
                    )
                    line_text = (self._clean_noise(line_text) or "").strip()
                    if line_text:
                        if current_field == "question_text":
                            if not questions[q_num]["question_text"]:
                                line_text = re.sub(r"^\d+[\.\s]*", "", line_text)
                            questions[q_num]["question_text"] += " " + line_text
                        else:
                            questions[q_num]["options"][current_field] += " " + line_text

        layout_detector = self.layout_detector
        if layout_detector is None:
            raise RuntimeError("Layout detector is not initialized")
        images_dir = self.images_dir
        if images_dir is None:
            raise ValueError("images_dir must be initialized before processing page images")
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        temp_img_path = images_dir / f"_temp_page_{page_num}.png"
        pix.save(str(temp_img_path))
        results = layout_detector.predict_images(str(temp_img_path), str(images_dir))
        layout_result = results[0]
        boxes = layout_result.boxes

        for box in boxes:
            cls = int(box.cls[0])
            xyxy = box.xyxy[0].tolist()
            pdf_bbox = [c / 2 for c in xyxy]
            y_mid = (pdf_bbox[1] + pdf_bbox[3]) / 2
            type_name = layout_detector.model.id_to_names.get(cls, "unknown")

            if type_name in ["figure", "table", "isolate_formula"]:
                q_num = self._assign_to_question(y_mid, question_positions, page_num)
                if q_num and q_num in questions:
                    img_path = self._extract_bbox_image(page, pdf_bbox, q_num, type_name)
                    questions[q_num]["stem_images"].append(str(img_path))
        temp_img_path.unlink()

        for q in questions.values():
            q["question_text"] = (q.get("question_text") or "").strip()
            q["question_text"] = re.sub(r"^(\d+[\.\s]*)+", "", q["question_text"])
            for opt in q["options"]:
                val = (q["options"].get(opt) or "").strip()
                val = re.sub(r"\s+[\d_]$", "", val)
                q["options"][opt] = val

        return list(questions.values()), new_last_q_num

    def _detect_question_numbers_with_positions(self, page: fitz.Page) -> List[tuple]:
        """
        Detect question numbers and their Y positions

        Args:
            page: PyMuPDF page object

        Returns:
            List of (question_number, y_position) tuples
        """
        text_dict = cast(Dict, page.get_text("dict"))
        blocks = text_dict.get("blocks", [])
        question_positions: List[tuple] = []

        min_x = 1000.0
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    min_x = min(min_x, line["bbox"][0])

        for block_idx, block in enumerate(blocks):
            if "lines" in block:
                for i, line in enumerate(block["lines"]):
                    line_text = " ".join(
                        (span.get("text") or "").strip()
                        for span in line["spans"]
                        if (span.get("text") or "").strip()
                    )
                    line_text = line_text.strip()

                    if re.search(r"\d{4}/\d{2}/\w+/\d{2}", line_text):
                        continue
                    if "© UCLES" in line_text:
                        continue

                    x_pos = line["bbox"][0]
                    if x_pos > min_x + 50 and x_pos > 150:
                        continue

                    if self.question_detection_mode == "strict":
                        marker_pattern = r"^(\d+)\s+([A-Z][a-z]+)"
                    elif self.question_detection_mode == "open":
                        marker_pattern = r"^(\d+)[\.\s]*([A-Z\d\(\\]|$)"
                    else:
                        marker_pattern = r"^(\d+)[\.\s]*([A-Z]|\\|\(|\$|[a-z]{3,})"

                    match = re.match(marker_pattern, line_text)
                    if match:
                        q_num = int(match.group(1))
                        if self._is_valid_question_number(q_num):
                            y_pos = line["bbox"][1]
                            question_positions.append((q_num, y_pos))
                            continue

                    q_num_match = re.match(r"^(\d+)[\.]?$", line_text)
                    if q_num_match:
                        q_num = int(q_num_match.group(1))
                        if self._is_valid_question_number(q_num):
                            is_question = False
                            check_text = ""
                            if i + 1 < len(block["lines"]):
                                check_text = " ".join(
                                    (s.get("text") or "") for s in block["lines"][i + 1]["spans"]
                                ).strip()
                            elif block_idx + 1 < len(blocks):
                                next_block = blocks[block_idx + 1]
                                if "lines" in next_block and len(next_block["lines"]) > 0:
                                    check_text = " ".join(
                                        (s.get("text") or "") for s in next_block["lines"][0]["spans"]
                                    ).strip()

                            if len(check_text) > 3:
                                if not re.search(r"\d{4}/\d{2}/\w+/\d{2}", check_text):
                                    is_question = True

                            if is_question:
                                y_pos = line["bbox"][1]
                                question_positions.append((q_num, y_pos))

        sorted_positions = sorted(question_positions, key=lambda x: x[1])
        deduped: List[tuple] = []
        seen: set = set()
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
        page_num: int,
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
            return None

        if y_pos > 775:
            return None

        for i in range(len(question_positions) - 1, -1, -1):
            q_num, q_y = question_positions[i]
            if y_pos >= q_y:
                return q_num

        return None

    def _is_valid_question_number(self, number: int) -> bool:
        """Question number guardrails, configurable per curriculum/run."""
        if number < self.min_question_number:
            return False
        if self.max_question_number is not None and number > self.max_question_number:
            return False
        return True
