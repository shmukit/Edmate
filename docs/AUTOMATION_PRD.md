# PRD: Edmate Modular Automation Engine

## 1. Context & User Challenges
Content creators for O/A-level curricula (Cambridge, Edexcel, etc.) currently face high manual labor costs in extracting metadata from PDF/Excel past papers. 
**Challenges:**
- **Inconsistent Formats**: Different sessions/variants change layouts.
- **Manual Data Entry**: Copy-pasting core concepts and explanations is error-prone.
- **Diagram Fragmentation**: Images within multiple-choice options are frequently lost or badly cropped during OCR extraction.

## 2. User Journey / Flow
1. **Upload**: User drags a PDF/Excel file into the Hub.
2. **Configure**: User selects the Provider, Target Table (e.g., Chemistry), and Modalities.
3. **Execution**: The engine processes the file in the background with live logic shown in the real-time Analytics Dashboard.
4. **Admin Review & Override**: User views results and can **directly edit** any field in a live markdown editor.
5. **Visual Management**: User clicks any extracted diagram to open the built-in **Image Editor** for cropping, replacing, or annotating natively.
6. **AI Refinement**: User provides specifically targeted feedback (e.g., "Make this more concise") to have the AI regenerate a single question on command.
7. **Bulk Injection**: User triggers "Accept All" to commit verified drafts to the production database safely.

## 3. Core Features (Advanced)
- **Visual Extraction (OCR & Multi-Diagram)**: Automated diagram extraction utilizing strict boundary coordinate polling (2px padding bounds) supporting distinct diagrams for properties like Question Body, and Options A, B, C, D respectively.
- **Built-in Image Editor Suite**: Integrated Fabric.js engine supporting non-destructive cropping, pencil annotations, highlighters, and instantaneous local image uploads/replacements.
- **Real-Time Analytics Dashboard**: Real-time performance monitoring showing draft volumes, extraction success vs failure rates, and categorized pipeline metrics.
- **Iterative Refinement**: Closed-loop feedback system for prompt-based AI rewriting.
- **Subject-Specific Mapping**: Dynamic injection into subject/grade-specific database tables, or the **unified "questions" table** (primary target).
- **Soft Rejections & Draft Continuity**: Rejected questions are flagged for audit rather than deleted. State tracks unsaved edits automatically allowing seamless UI resumes.

## 4. Technical Dependencies
- **Backend Architecture**: FastAPI (Python), PostgreSQL (Database Service v2).
- **Vision Extraction**: Google Vertex AI (Gemini), OpenAI Vision API.
- **Image Logic**: `PyMuPDF` (fitz), `Pillow` (PIL) for image crop extractions, `Fabric.js` for frontend canvas interactions.
- **State Persistence**: Draft JSON storage system mapped to asynchronous event triggers.

## 5. User Acceptance Criteria (UAC)
- [x] **Speed**: Handle multi-column PDF layouts (~20 pages) intelligently.
- [x] **Overrides**: Admin can edit and save changes directly via the review interface (Text & Graphics).
- [x] **Image Processing**: Admin can add, crop, replace, highlight, or remove images securely.
- [x] **Refinement**: "Refine with AI" accurately interprets feedback to rewrite content dynamically.
- [x] **Database Integrity**: Questions inject cleanly into respective tables mapping associated explanations or flashcards efficiently.
- [x] **Platform Polish**: Implement clear indicators, darkmode aesthetics, and consistent toast notification loops.
