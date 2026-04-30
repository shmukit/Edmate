import unittest
from typing import Optional
import qc_viewer.services.automation_pipeline as ap
print(f"DEBUG: Module path: {ap.__file__}")

from qc_viewer.services.automation_pipeline import (
    _apply_runtime_model_overrides,
    extract_correct_answer,
    extract_core_concept,
)
from content_gen.core.model_router import ModelRoutingEngine

class MockModelConfig:
    def __init__(self):
        self.extraction_model = "default/extraction"
        self.generation_model = "default/generation"
        self.validation_model = "default/validation"
        self.question_detection_mode = "balanced"
        self.min_question_number = 1
        self.max_question_number = 40

class MockRouter:
    def __init__(self):
        self.config = MockModelConfig()

class TestAutomationPipeline(unittest.TestCase):
    def setUp(self):
        self.router = MockRouter()

    def test_apply_runtime_model_overrides_no_byok(self):
        # Even if provider is sent, if has_api_key is False, it should NOT override
        res = _apply_runtime_model_overrides(self.router, "openai", None, has_api_key=False)
        self.assertIsNone(res["resolved_model"])
        self.assertEqual(self.router.config.generation_model, "default/generation")

    def test_apply_runtime_model_overrides_with_byok(self):
        # If has_api_key is True, it SHOULD override with provider defaults
        res = _apply_runtime_model_overrides(self.router, "openai", None, has_api_key=True)
        self.assertEqual(res["resolved_model"], "openai/gpt-4o-mini")
        self.assertEqual(self.router.config.generation_model, "openai/gpt-4o-mini")

    def test_apply_runtime_model_overrides_explicit_model(self):
        # Explicit model ID should always override
        res = _apply_runtime_model_overrides(self.router, "gemini", "gemini-1.5-pro", has_api_key=True)
        self.assertEqual(res["resolved_model"], "gemini/gemini-1.5-pro")

    def test_extract_correct_answer(self):
        self.assertEqual(extract_correct_answer("Final Correct Answer: B"), "B")
        self.assertEqual(extract_correct_answer("The correct Answer is: C"), "C")
        self.assertEqual(extract_correct_answer("None of the above"), "N/A")

    def test_extract_core_concept(self):
        explanation = "Core Concept: Photosynthesis is the process...\nStep 1: Water is absorbed..."
        self.assertEqual(extract_core_concept(explanation), "Photosynthesis is the process...")
        
        # Test fallback
        explanation_no_core = "Plants use sunlight to make food.\nIt is called photosynthesis."
        self.assertEqual(extract_core_concept(explanation_no_core), "Plants use sunlight to make food.")
        
        # Test truncation
        long_line = "This is a very very long first line that should definitely be truncated because it's way too long to be a core concept title and we want to keep it clean " * 5
        result = extract_core_concept(long_line)
        print(f"DEBUG: Result length: {len(result)}")
        print(f"DEBUG: Result: {result}")
        self.assertTrue(result.endswith("..."))

if __name__ == "__main__":
    unittest.main()
