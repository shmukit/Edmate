# Edmate AI Architecture

Edmate AI is built on a modular, headless architecture designed for high-fidelity educational content generation.

## 1. The Modular Pipeline
Our pipeline is divided into distinct stages to ensure maximum quality and resilience:

- **Ingestion**: Multi-format support (PDF, DOCX, Images).
- **Extraction**: Hybrid pipeline using OCR, Layout Analysis, and Vision-based LLMs.
- **Pedagogy Engine**: Real-time analysis of content against learning science principles.
- **Generation**: Context-aware content creation (MCQs, Explanations, Distractors).
- **Validation (HIA)**: Automated verification of correctness and pedagogical integrity.

## 2. Headless Design
The backend is a standalone FastAPI service that can be integrated into any LMS or platform via a standardized JSON schema.

## 3. Bring Your Own Key (BYOK)
We prioritize privacy and control, allowing users to provide their own LLM API keys for processing.
