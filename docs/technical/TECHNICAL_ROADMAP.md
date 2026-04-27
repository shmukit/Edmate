# 🗺️ Edmate Platform Roadmap

This document outlines the future modularity scopes and technical milestones for the Edmate Content Automation Pipeline.

---

## 🛠️ Upcoming Modularity Scopes

### 1. Extraction Modularity (High Priority)
*   **Goal**: Decouple the pipeline from `PDF-Extract-Kit` to allow BYO-Extraction.
*   **Adapters to Build**:
    *   `PymupdfExtractor` (Lightweight, text-only).
    *   `UnstructuredExtractor` (Universal document parsing).
    *   `MathpixExtractor` (Specialized LaTeX/Formula extraction).
*   **Status**: 💡 Planned.

### 2. Export Modularity (High Priority)
*   **Goal**: Allow Edmate to export content into institutional standards beyond our internal JSON.
*   **Adapters to Build**:
    *   `QTIExporter`: Standard for Canvas, Moodle, and Blackboard.
    *   `AnkiExporter`: Direct `.apkg` generation for medical/language students.
    *   `PDFExporter`: Professional, printable question papers.
*   **Status**: 💡 Planned.

### 3. Dynamic "Orkestra-Style" Routing
*   **Goal**: Implement AI-driven complexity detection to auto-route prompts.
*   **Concept**:
    *   Use a KNN or lightweight classifier (like Orkestra) to determine if a prompt is "Simple" or "Complex."
    *   Automate the switch between Haiku and Pro models without manual config.
*   **Status**: 🔍 Investigating.

### 4. Pedagogical Judge Logic
*   **Goal**: Automated QC using a separate high-reasoning LLM to score content against a strict educational rubric.
*   **Status**: 💡 Planned.

---

## 📅 Timeline

### Q2 2026: The "Universal Connector" Phase
- [ ] Implement `BaseExtractionAdapter`.
- [ ] Add support for CSV/Excel source ingestion.
- [ ] Launch `BaseExportAdapter` with initial Markdown/LaTeX support.

### Q3 2026: The "Agentic Intelligence" Phase
- [ ] Integrate Dynamic Complexity Routing (Orkestra-style).
- [ ] Implement the "Pedagogical Judge" validation layer.
- [ ] Expand MCP Server to support "Streaming" updates.

---

## 🤝 Contribution
If you are interested in leading one of these modularity scopes, please refer to our **[CONTRIBUTING_MODULAR.md](../contributing/CONTRIBUTING_MODULAR.md)** guide.
