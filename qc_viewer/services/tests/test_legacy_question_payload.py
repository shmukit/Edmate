import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from content_gen.core.schemas import Flashcard, ProcessedQuestion
from qc_viewer.services.legacy_question_payload import (
    build_legacy_question_dict,
    resolve_diagram_data_uri,
)


class TestLegacyQuestionPayload(unittest.TestCase):
    def test_resolve_diagram_from_b64_metadata(self):
        q = ProcessedQuestion(
            question_number=1,
            question_text="Q?",
            options={"A": "1", "B": "2", "C": "3", "D": "4"},
            correct_options=["A"],
            subject="Physics",
            metadata={"stem_images_b64": ["data:image/png;base64,xxx"]},
        )
        self.assertEqual(resolve_diagram_data_uri(q), "data:image/png;base64,xxx")

    def test_resolve_diagram_from_file(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "stem.png"
            p.write_bytes(b"\x89PNG\r\n\x1a\n")  # minimal PNG header bytes; reader only base64 encodes
            q = ProcessedQuestion(
                question_number=1,
                question_text="Q?",
                options={"A": "1"},
                correct_options=[],
                subject="Physics",
                metadata={"stem_images": [str(p)]},
            )
            uri = resolve_diagram_data_uri(q)
            if uri is None:
                self.fail("Expected data URI from stem image file")
            self.assertTrue(uri.startswith("data:image/png;base64,"))

    def test_build_legacy_question_dict_contract_warnings(self):
        q = ProcessedQuestion(
            question_number=2,
            question_text="Stem",
            options={"A": "a", "B": "b", "C": "c", "D": "d"},
            correct_options=["B"],
            subject="Chemistry",
            explanation_body="Final Correct Answer: B\n",
            option_wise_explanation="Option A: x\nOption B: y\nOption C: z\nOption D: w\n",
            metadata={
                "generation_quality": {
                    "has_explanation": True,
                    "has_final_answer": False,
                }
            },
        )
        legacy = build_legacy_question_dict(q)
        self.assertEqual(legacy["correct_answer"], "B")
        self.assertIn("has_final_answer", legacy["contract_warnings"])
        self.assertEqual(len(legacy["generated_content"]["flashcards"]), 0)

    def test_build_legacy_with_flashcards(self):
        q = ProcessedQuestion(
            question_number=1,
            question_text="Q",
            options={"A": "1", "B": "2", "C": "3", "D": "4"},
            correct_options=["A"],
            subject="Bio",
            flashcards=[Flashcard(front_text="F", back_text="B")],
        )
        legacy = build_legacy_question_dict(q)
        self.assertEqual(
            legacy["generated_content"]["flashcards"],
            [{"question": "F", "answer": "B"}],
        )


if __name__ == "__main__":
    unittest.main()
