from pathlib import Path
from unittest.mock import MagicMock

from content_gen.adapters.kit_extraction_adapter import KitExtractionAdapter
from content_gen.scripts.extraction.pdf_extract_kit_wrapper import PDFExtractKitWrapper
from content_gen.scripts.processing.content_generator import ContentGenerator


def _wrapper_without_init() -> PDFExtractKitWrapper:
    wrapper = PDFExtractKitWrapper.__new__(PDFExtractKitWrapper)
    wrapper.min_question_number = 1
    wrapper.max_question_number = 40
    wrapper.question_detection_mode = "balanced"
    return wrapper


def test_wrapper_merges_split_question_fragments():
    wrapper = _wrapper_without_init()
    merged = wrapper._merge_questions([
        {
            "question_number": 2,
            "page": 2,
            "question_text": "Part one",
            "options": {"A": "alpha", "B": "", "C": "", "D": ""},
            "stem_images": ["/tmp/q2.png"],
            "option_images": {}
        },
        {
            "question_number": 2,
            "page": 3,
            "question_text": "Part two",
            "options": {"A": "", "B": "beta", "C": "", "D": ""},
            "stem_images": ["/tmp/q2.png", "/tmp/q2b.png"],
            "option_images": {}
        }
    ])

    assert len(merged) == 1
    assert merged[0]["question_number"] == 2
    assert merged[0]["question_text"] == "Part one Part two"
    assert merged[0]["options"]["A"] == "alpha"
    assert merged[0]["options"]["B"] == "beta"
    assert merged[0]["stem_images"] == ["/tmp/q2.png", "/tmp/q2b.png"]


def test_wrapper_does_not_assign_preamble_to_first_question():
    wrapper = _wrapper_without_init()
    assigned = wrapper._assign_to_question(
        y_pos=10.0,
        question_positions=[(1, 100.0), (2, 200.0)],
        page_num=2
    )
    assert assigned is None


def test_content_generator_flashcard_parser_handles_colons():
    generator = ContentGenerator(router=MagicMock())
    parsed = generator._parse_flashcards(
        "Flashcard 1: What is force: in physics? Back: Rate of change of momentum.\n"
        "Flashcard 2: Define SI unit? Back: Standard unit."
    )
    assert len(parsed) == 2
    assert parsed[0].front_text == "What is force: in physics?"
    assert parsed[0].back_text == "Rate of change of momentum."


def test_kit_adapter_preserves_image_paths_and_base64(tmp_path: Path):
    img_path = tmp_path / "q1.png"
    img_path.write_bytes(b"image-bytes")

    adapter = KitExtractionAdapter.__new__(KitExtractionAdapter)
    adapter.wrapper = MagicMock()
    adapter.wrapper.extract_questions.return_value = {
        "questions": [
            {
                "question_number": 1,
                "question_text": "Q",
                "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
                "stem_images": [str(img_path)],
                "option_images": {}
            }
        ]
    }

    result = adapter.extract_content(tmp_path / "source.pdf", tmp_path)
    meta = result[0].metadata
    assert meta["stem_images"] == [str(img_path)]
    assert meta["stem_images_b64"][0].startswith("data:image/png;base64,")


def test_wrapper_question_number_range_is_configurable():
    wrapper = _wrapper_without_init()
    wrapper.max_question_number = None
    assert wrapper._is_valid_question_number(85) is True
    wrapper.max_question_number = 40
    assert wrapper._is_valid_question_number(85) is False


def test_parse_response_returns_empty_for_multi_without_headers():
    generator = ContentGenerator(router=MagicMock())
    parsed = generator._parse_response(
        "This is a combined response with no explicit question headers.",
        [1, 2, 3]
    )
    assert parsed == {}


def test_validate_generated_content_flags_missing_sections():
    generator = ContentGenerator(router=MagicMock())
    bad = generator._validate_generated_content({
        "explanation_generated": "Short text",
        "options_explanation_generated": "Option A: one",
        "flashcards_generated": "",
    })
    assert bad["retry_required"] is True

    good = generator._validate_generated_content({
        "explanation_generated": "Core Concept: X\nFinal Correct Answer: B",
        "options_explanation_generated": "Option A: a\nOption B: b\nOption C: c\nOption D: d",
        "flashcards_generated": "Flashcard 1: Q? Back: A\nFlashcard 2: Q2? Back: A2",
    })
    assert good["retry_required"] is False
