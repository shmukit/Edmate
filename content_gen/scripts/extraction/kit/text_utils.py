"""Text reconstruction and noise cleaning for PDF-Extract-Kit wrapper."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional


class KitTextUtilsMixin:
    # --- cross-mixin attribute dependencies (set by PDFExtractKitWrapper.__init__) ---
    extraction_noise_patterns: List[str]
    outputs_dir: Optional[Path]
    base_name: Optional[str]
    def _clean_noise(self, text: str) -> str:
        """Filter global noise and map symbols from reconstructed text parts"""
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

        text = re.sub(r"\d{4}/\d{2}/\w+/\d{2}", "", text)
        text = re.sub(r"© UCLES.*", "", text, flags=re.I)
        text = re.sub(r"\[Turn over", "", text, flags=re.I)

        for pattern in self.extraction_noise_patterns:
            if pattern:
                text = re.sub(pattern, "", text, flags=re.I | re.DOTALL)

        return text.strip()

    def _reconstruct_line_text(
        self, spans: List[Dict], avg_baseline: float, main_size: float
    ) -> str:
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

    def _generate_processed_text(self, output_data: Dict) -> None:
        """Generate the standard processed text file in data/outputs following prompts.py"""
        outputs_dir = self.outputs_dir
        base_name = self.base_name
        if outputs_dir is None or base_name is None:
            raise ValueError(
                "outputs_dir and base_name must be initialized before generating processed text"
            )
        text_path = outputs_dir / f"{base_name}_processed.txt"

        sorted_qs = sorted(
            output_data.get("questions", []), key=lambda x: x["question_number"]
        )

        with open(text_path, "w", encoding="utf-8") as f:
            for q in sorted_qs:
                f.write(
                    f"Question {q['question_number']}Question and Options in Text Format\n\n"
                )

                f.write(f"{q['question_text'].strip()}\n\n")

                opts = q["options"]
                opt_str = f"A. {opts['A']} B. {opts['B']} C. {opts['C']} D. {opts['D']}"
                f.write(f"{opt_str.strip()}\n\n")

                f.write("Detailed Explanation of the Question and Right Answer\n\n")
                f.write("[EXPLANATION_PLACEHOLDER]\n\n")
                f.write("Option Wise Explanation (Detailed)\n\n")
                f.write("[OPTION_EXPLANATION_PLACEHOLDER]\n\n")
                f.write("### 🧠 Concept Gap Analysis and Flashcards\n\n")
                f.write("[FLASHCARDS_PLACEHOLDER]\n\n")
                f.write("-" * 50 + "\n\n")
