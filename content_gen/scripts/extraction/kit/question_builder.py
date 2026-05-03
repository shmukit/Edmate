"""Merge question fragments across pages."""
from __future__ import annotations

from abc import abstractmethod
from typing import Dict, List


class KitQuestionBuilderMixin:
    # --- cross-mixin method dependency (provided by KitPageProcessorMixin) ---
    @abstractmethod
    def _is_valid_question_number(self, number: int) -> bool: ...
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
                        "D": (q.get("options", {}).get("D", "") or "").strip(),
                    },
                    "stem_images": list(dict.fromkeys(q.get("stem_images", []) or [])),
                    "option_images": q.get("option_images", {}) or {},
                }
                continue

            q_text = (q.get("question_text") or "").strip()
            if q_text:
                merged[num]["question_text"] = (
                    f"{merged[num]['question_text']} {q_text}".strip()
                )

            for opt in ["A", "B", "C", "D"]:
                opt_text = (q.get("options", {}).get(opt, "") or "").strip()
                if not opt_text:
                    continue
                existing = merged[num]["options"].get(opt, "")
                merged[num]["options"][opt] = f"{existing} {opt_text}".strip()

            merged[num]["stem_images"] = list(
                dict.fromkeys(
                    merged[num]["stem_images"] + (q.get("stem_images", []) or [])
                )
            )

        return sorted(merged.values(), key=lambda item: item["question_number"])
