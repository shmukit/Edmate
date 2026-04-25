# Edmate Standard JSON Schema (v1.2.0)

Edmate enforces a unified schema for all educational content output. This schema is designed to be consumed by downstream platforms, LMS systems, and applications — **not students directly**. Every field exists to give the consuming platform the information it needs to implement learning science techniques (spaced repetition, Bloom's-level filtering, interleaving, adaptive difficulty) without any additional AI calls.

---

## 1. Schema Specification

```json
{
  "$schema": "https://edmate.ai/schemas/v1.2/question.json",
  "version": "1.2.0",
  "id": "uuid-v4",
  "metadata": {
    "curriculum": "string (e.g., 'Cambridge O-Level', 'NCTB Bangladesh', 'CBSE Grade 10')",
    "subject": "string",
    "topic": "string",
    "subtopic": "string",
    "difficulty": "enum['Easy', 'Medium', 'Hard']",
    "scaffold_level": "enum['Foundation', 'Core', 'Extension'] (Cognitive Load layering)",
    "assessment_role": "enum['formative', 'summative', 'diagnostic', 'practice']",
    "retrieval_mode": "enum['low_stakes', 'summative'] (Retrieval Practice tagging)",
    "question_variant_group_id": "uuid (Groups multiple question types testing the same concept)",
    "concept_links": ["string (Related topic/concept for Interleaving tags)"],
    "interleaving_tags": ["string (Cross-topic subject areas this question touches)"],
    "exam_context": {
      "board": "string",
      "year": "string",
      "session": "string",
      "variant": "string"
    }
  },
  "content": {
    "type": "enum['mcq', 'short_answer', 'true_false', 'fill_in_blank', 'matching', 'structured', 'worked_example', 'ai_critique', 'isomorphic_variant', 'scaffolded_sequence', 'contextualizable_template', 'viva_prompt', 'metacognitive_reflection']",
    "stimulus": "string (Optional: Context or passage preceding the question)",
    "question_text": "string (Supports LaTeX)",
    "options": [
      {
        "id": "string (A, B, C, D)",
        "text": "string",
        "is_correct": "boolean",
        "explanation": "string (Why this option is correct/incorrect)",
        "concept_gap": "string (Misconception this option targets — for platform feedback engines)"
      }
    ],
    "explanations": {
      "core_concept": "string (One-sentence summary — Cognitive Load: lowest layer)",
      "detailed_logic": "string (Step-by-step reasoning — Cognitive Load: middle layer)",
      "final_answer_display": "string (Verdict — Cognitive Load: top layer)",
      "bloom_taxonomy": "enum['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create']"
    },
    "flashcard_bridge": [
      {
        "front": "string",
        "back": "string",
        "type": "enum['concept', 'recall', 'problem_solving']",
        "ease_factor": "float (SM-2 default: 2.5 — Spaced Repetition metadata)",
        "interval": "integer (SM-2 default: 1 day)",
        "next_review_date": "string|null (ISO 8601 — null until first review by platform)"
      }
    ],
    "rubric": [
      {
        "criterion": "string (For short_answer, structured, worked_example types)",
        "max_marks": "integer",
        "descriptor": "string"
      }
    ],
    "hia_details": {
      "planted_errors": [
        {
          "type": "string (e.g., 'omission', 'calculation', 'logic')",
          "description": "string",
          "severity": "enum['minor', 'moderate', 'major', 'critical']"
        }
      ],
      "variant_parameters": {
        "master_template": "string",
        "variables": ["string"]
      },
      "scaffold_steps": [
        {
          "step": "integer",
          "task": "string",
          "evidence_type": "string"
        }
      ],
      "viva_probes": [
        {
          "stage": "enum['Verify', 'Illustrate', 'Validate', 'Apply']",
          "prompt": "string",
          "follow_ups": ["string"]
        }
      ]
    }
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
  },
  "learning_science_applied": {
    "profile": "string (e.g., 'default', 'exam_prep', 'beginner', 'custom')",
    "techniques": [
      {
        "name": "string (e.g., \"Bloom's Taxonomy\", \"Spaced Repetition (SM-2)\")",
        "level": "string|null (e.g., \"Apply\" for Bloom's — null for non-level techniques)",
        "description": "string (Human-readable description of how this technique was applied)"
      }
    ],
    "config_snapshot": {
      "explanation_depth": "string (e.g., \"full\")",
      "bloom_target_levels": ["string"],
      "spaced_repetition_algorithm": "string",
      "assessment_role_default": "string"
    },
    "schema_version": "string (e.g., \"1.2.0\")"
  },
  "ai_integrity_label": {
    "resilience_score": "enum['Low', 'Medium', 'High', 'Very High']",
    "strategy_applied": "string (e.g., 'Process-over-Product', 'Critical Evaluation')",
    "vulnerability_notes": "string",
    "mitigation_recommendation": "string (e.g., 'Pair with oral defense')"
  }
}
```

---

## 2. Key Design Principles

1.  **LaTeX Support:** All string fields (`question_text`, `options[].text`, `explanations`) must support LaTeX wrapped in `$...$` or `$$...$$`.
2.  **Option-Level Granularity:** Unlike basic generators, Edmate requires an explanation for **every** option (A, B, C, D) to facilitate deeper learning.
3.  **HIA (High-Integrity) First:** Edmate prioritizes the generation of High-Integrity Assessments (Tier 5) to combat AI-induced cheating in modern education.
4.  **Flashcard Decoupling:** Flashcards are generated as a sub-object of the question, allowing them to be extracted and used in the 3D viewer independently.
5.  **Platform Agnostic:** This schema is designed to be consumed by any frontend (Web, Mobile, 3D) or exported to any LMS (Canvas, Moodle).

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
