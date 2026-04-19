# PRD: Edmate Modular Automation Engine

## 1. Context & User Challenges
Content creators for O/A-level curricula (Cambridge, Edexcel, etc.) currently face high manual labor costs in extracting metadata from PDF/Excel past papers. 
**Challenges:**
- **Inconsistent Formats**: Different sessions/variants change layouts.
- **Manual Data Entry**: Copy-pasting core concepts and explanations is error-prone.
- **Diagram Fragmentation**: Images are often lost during manual extraction.

## 2. User Journey / Flow
1. **Upload**: User drags a PDF/Excel file into the Hub.
2. **Configure**: User selects the Provider, Target Table (e.g., Chemistry), and Modalities.
3. **Execution**: The engine processes the file in the background with live monitoring.
4. **Admin Review & Override**: User views results and can **directly edit** any field (Question text, Explanations, Options) in a live editor.
5. **AI Refinement**: User can provide specifically targeted feedback (e.g., "Make this more concise") to have the AI regenerate a single question.
6. **Bulk Injection**: User can "Accept All" verified questions or "Reject" specific entries before committing to the production database.

## 3. Core Features (Advanced)
- **Visual Extraction (OCR + Cropping)**: Automated diagram extraction with 5px padding and vision calibration.
- **Admin Editor**: Real-time override of AI-generated content before production injection.
- **Iterative Refinement**: Closed-loop feedback system for AI rewriting.
- **Subject-Specific Mapping**: Dynamic injection into subject/grade-specific database tables, or the **unified "questions" table** (primary target).
- **Soft Rejections**: Rejected questions are flagged for audit rather than deleted, allowing for later correction and retry.
- **Audit Tracking**: `last_reviewed_at` timestamps and sorted draft history.

## 4. Technical Dependencies
- **Backend**: FastAPI (Python), PostgreSQL (Database Service v2).
- **Vision**: Google Vertex AI (Gemini), OpenAI Vision API.
- **Libraries**: `PyMuPDF` (fitz), `Pillow` (PIL) for image cropping.
- **Persistence**: Draft JSON storage with real-time sync.

## 5. User Acceptance Criteria (UAC)
- [x] **Speed**: Handle multi-column PDF layouts (~20 pages) in under 2 minutes.
- [x] **Overrides**: Admin can edit and save changes directly in the review panel.
- [x] **Refinement**: "Refine with AI" successfully updates content using user feedback.
- [x] **Database Integrity**: Questions inject correctly into subject-specific tables (Chemistry, Biology, etc.) with associated flashcards.
- [x] **UX**: Clickable rows, bulk actions, and standardized toast notifications.
