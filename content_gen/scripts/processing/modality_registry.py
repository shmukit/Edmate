from typing import Dict, Any, List, Optional
from google.genai import types


class Modality:
    def __init__(self, id: str, name: str, prompt_chunk: str, schema_fragment: Dict[str, Any]):
        self.id = id
        self.name = name
        self.prompt_chunk = prompt_chunk
        self.schema_fragment = schema_fragment


# Registry of all available modalities
MODALITIES: Dict[str, Modality] = {
    "core_concept": Modality(
        id="core_concept",
        name="Core Concept",
        prompt_chunk="Summarize the main educational principle behind this question.",
        schema_fragment={"core_concept": types.Schema(type=types.Type.STRING)}
    ),
    "detailed_explanation": Modality(
        id="detailed_explanation",
        name="Detailed Explanation",
        prompt_chunk="Provide a step-by-step logic leading to the answer. CRITICAL: End with '**Final Correct Answer: [LETTER]**'.",
        schema_fragment={"detailed_explanation": types.Schema(type=types.Type.STRING)}
    ),
    "option_analysis": Modality(
        id="option_analysis",
        name="Option Analysis",
        prompt_chunk="Explain why each option (A, B, C, D) is correct or incorrect.",
        schema_fragment={
            "option_analysis": types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "A": types.Schema(type=types.Type.STRING),
                    "B": types.Schema(type=types.Type.STRING),
                    "C": types.Schema(type=types.Type.STRING),
                    "D": types.Schema(type=types.Type.STRING),
                }
            )
        }
    ),
    "flashcards": Modality(
        id="flashcards",
        name="Flashcards",
        prompt_chunk="Generate 2-3 conceptual flashcards based on this question.",
        schema_fragment={
            "flashcards": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "question": types.Schema(type=types.Type.STRING),
                        "answer": types.Schema(type=types.Type.STRING),
                    }
                )
            )
        }
    )
}


def get_modalities(ids: List[str]) -> List[Modality]:
    return [MODALITIES[mid] for mid in ids if mid in MODALITIES]
