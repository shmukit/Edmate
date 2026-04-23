# Edmate: The Modular content Automation Service (Strategy & Plan)

## 1. Vision & Core Proposition
Edmate is an open-source service platform designed to be the "Content Infrastructure" for teachers, publishers, and EdTech developers.

**Core Value:** Provide an automated pipeline to convert any source material (**PDF, Excel, Docx**, etc.) into beautiful, structured Q&A, explanations, and visual study aids (Flashcards, etc.) for **any curriculum** using **any LLM**.

---

## 2. Competitive Landscape & "Unfair Advantages"

### Market Position
| Solution Type | Examples | Edmate's Advantage |
| :--- | :--- | :--- |
| **Consumer SaaS** | Quizgecko, Quizizz | **Workflow:** Edmate provides a professional "Draft -> Review -> QC" pipeline. |
| **Structural AI** | MentoMind, MinerU | **Experience:** Edmate turns raw extraction into "Beautiful" UI (3D Flashcards). |
| **Generic AI** | NotebookLM | **Automation:** Edmate is a "headless" factory, not just a search tool. |

### Strategic Differentiators
1.  **Regional Optimization:** Native support for Bangladesh NCTB and British (CIE/Edexcel) A/O-Level formatting.
2.  **High-Fidelity Math:** Sophisticated LaTeX and formula extraction (using specialized engines).
3.  **The "Wow" Factor:** Interactive 3D content that feels like a "Next-Gen" product.

---

## 3. Modular Platform Architecture ("Plug & Play")

The platform is built as a **Switchboard** where stage of the pipeline is a hotswappable plugin.

*   **Ingestion Plugins:** Drivers for PDF (MinerU/PDF-Extract-Kit), Sheet (OpenPyXL), and Word.
*   **Prompt Library:** Modular templates for different curricula and teacher styles (Subject-Matter focus).
*   **Inference Adapter:** Standardized interface supporting **BYOK (Bring Your Own Key)** for OpenAI, Gemini, Anthropic, or local Ollama.
*   **Exporter Plugins:** Modular outputs for JSON, LaTeX, Markdown, and 3D Flashcard bridges.

---

## 4. Monetization & Business Model

### Tiers of Service
*   **Community (Free/Open Source):** 
    *   Self-hosted version for developers and teachers.
    *   **BYOK Model:** Users pay AI providers directly; Edmate is free to use.
*   **Pro (Individual):** 
    *   Managed SaaS with hosted UI and included AI tokens for non-technical teachers.
*   **Studio / Team:** 
    *   Collaborative QC Workspace for content teams/agencies to verify and polish AI output.
*   **Enterprise (Service API):** 
    *   Headless API for platforms like **Alopoth** to plug in their own content engines without building from scratch.

---

## 5. Strategic Roadmap

### Phase 1: The Engine (Open Source)
- [ ] Finalize the "Switchboard" pipeline orchestration.
- [ ] Implement BYOK support for major LLM providers.
- [ ] Standardize the "Educational Q&A" JSON Schema.

### Phase 2: The UI & Workflow
- [ ] Launch the Professional QC Dashboard.
- [ ] Build the One-Click Export to major LMS platforms (Canvas/Moodle/Google Classroom).

### Phase 3: The Ecosystem
- [ ] Open the "Prompt Marketplace" for subject-matter experts.
- [ ] Launch the B2B Service API for high-scale institutional partners.
