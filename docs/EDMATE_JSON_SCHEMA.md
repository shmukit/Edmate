# Edmate Standard JSON Schema (v1.0.0)

To achieve a "Plug & Play" ecosystem, Edmate enforces a unified schema for all educational content. Whether the source is a scanned PDF, an Excel sheet, or a raw text document, the output must conform to this specification.

---

## 1. Schema Specification

```json
{
  "$schema": "https://edmate.ai/schemas/v1/question.json",
  "version": "1.0.0",
  "id": "uuid-v4",
  "metadata": {
    "curriculum": "string (e.g., 'Cambridge O-Level', 'NCTB Bangladesh')",
    "subject": "string",
    "topic": "string",
    "subtopic": "string",
    "difficulty": "enum['Easy', 'Medium', 'Hard']",
    "exam_context": {
      "board": "string",
      "year": "string",
      "session": "string",
      "variant": "string"
    }
  },
  "content": {
    "type": "enum['mcq', 'short_answer', 'true_false', 'structured']",
    "stimulus": "string (Optional: Context or passage preceding the question)",
    "question_text": "string (Supports LaTeX)",
    "options": [
      {
        "id": "string (A, B, C, D)",
        "text": "string",
        "is_correct": "boolean",
        "explanation": "string (Detailed reasoning for this specific option)"
      }
    ],
    "explanations": {
      "core_concept": "string",
      "detailed_logic": "string (Step-by-step reasoning)",
      "final_answer_display": "string",
      "bloom_taxonomy": "enum['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create']"
    },
    "flashcard_bridge": [
      {
        "front": "string",
        "back": "string",
        "type": "enum['concept', 'recall', 'problem_solving']"
      }
    ]
  },
  "media": [
    {
      "id": "string",
      "type": "enum['image', 'video', 'table']",
      "content_ref": "string (URL or Base64)",
      "alt_text": "string"
    }
  ],
  "accessibility": {
    "screen_reader_text": "string"
  }
}
```

---

## 2. Key Design Principles

1.  **LaTeX Support:** All string fields (`question_text`, `options[].text`, `explanations`) must support LaTeX wrapped in `$...$` or `$$...$$`.
2.  **Option-Level Granularity:** Unlike basic generators, Edmate requires an explanation for **every** option (A, B, C, D) to facilitate deeper learning.
3.  **Flashcard Decoupling:** Flashcards are generated as a sub-object of the question, allowing them to be extracted and used in the 3D viewer independently.
4.  **Platform Agnostic:** This schema is designed to be consumed by any frontend (Web, Mobile, 3D) or exported to any LMS (Canvas, Moodle).

---

## 3. Example Instance (Chemistry MCQ)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "curriculum": "Cambridge O-Level",
    "subject": "Chemistry",
    "topic": "Atomic Structure",
    "difficulty": "Medium"
  },
  "content": {
    "type": "mcq",
    "question_text": "What is the number of protons in an atom of $\\ce{^{23}_{11}Na}$?",
    "options": [
      {"id": "A", "text": "11", "is_correct": true, "explanation": "The atomic number (subscript) represents the number of protons."},
      {"id": "B", "text": "12", "is_correct": false, "explanation": "12 is the number of neutrons ($23 - 11 = 12$)."},
      {"id": "C", "text": "23", "is_correct": false, "explanation": "23 is the mass number (protons + neutrons)."},
      {"id": "D", "text": "34", "is_correct": false, "explanation": "34 is the sum of mass and atomic number, which has no physical meaning here."}
    ],
    "explanations": {
      "core_concept": "Atomic Number and Mass Number",
      "detailed_logic": "Step 1: Identify the atomic symbol. Step 2: Extract the subscript (11). Step 3: Conclude that protons = 11.",
      "final_answer_display": "**Final Correct Answer: A**"
    },
    "flashcard_bridge": [
      {
        "front": "How do you find the number of protons from an atomic symbol like $\\ce{^{A}_{Z}X}$?",
        "back": "It is equal to the atomic number (Z), shown as the subscript.",
        "type": "concept"
      }
    ]
  }
}
```
