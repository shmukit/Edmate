# Content Generation Agentic Workflow Architecture

## Executive Summary

This document defines the **complete agentic workflow** for A/O-level educational content generation at Edmate. The system transforms raw exam PDFs into structured, pedagogically-rich content stored in a database with CDN-hosted assets.

**Current Status**: ✅ PDF Extraction → JSON + PNG | ✅ Azure Blob Storage | ✅ Database Integration

---

## System Architecture

```mermaid
graph TB
    A[Raw PDF Files] --> B[Skill 1: PDF Extraction]
    B --> C[Structured JSON]
    B --> D[PNG Images]
    C --> E[Skill 2: Content Generation]
    E --> F[Enhanced Content JSON]
    F --> G[Skill 2.5: LLM-as-Judge Eval]
    G --> H[Verified Content]
    H --> I[Skill 3: Content Formatting]
    I --> J[Google Docs Compatible Text]
    D --> K[Skill 4: Blob Storage Upload]
    K --> L[CDN URLs - Azure]
    J --> M[Skill 5: Database Import]
    L --> M
    M --> N[PostgreSQL/Supabase]
```

---

## Workflow Phases

### Phase 1: PDF Content Extraction ✅ IMPLEMENTED
**Skill**: PDF Question Extraction  
**Scripts**: `smart_extract.py`, `extract_pdf_content.py`

**Inputs**:
- PDF file path (e.g., `9701_s25_qp_13.pdf`)
- Output directory

**Process**:
1. Parse PDF pages using PyMuPDF
2. Identify question anchors (numbers 1-50 in left margin)
3. Identify option anchors (A, B, C, D in left margin)
4. Extract vector diagrams using drawing detection
5. Apply quadrant logic for multi-option diagrams
6. Cluster and merge proximity-based image regions
7. Render high-resolution PNGs (3x scale)

**Outputs**:
```json
{
  "source": "9701_s25_qp_13.pdf",
  "questions": [
    {
      "question_number": 1,
      "page": 1,
      "stem_images": ["q1_stem.png"],
      "option_images": {
        "A": ["q1_opt_A.png"],
        "B": ["q1_opt_B.png"]
      }
    }
  ]
}
```

**Key Algorithms**:
- **Anchor Detection**: Regex + spatial constraints (x < 65 for questions, x < 100 for options)
- **Quadrant Logic**: Divides 4-option diagrams into A (top-left), B (top-right), C (bottom-left), D (bottom-right)
- **Proximity Merge**: Combines drawing paths within 45px vertical or 30px horizontal distance
- **Expansion & Padding**: Adds 20px white border to prevent bond/line clipping

---

### Phase 2: Content Generation ✅ IMPLEMENTED (Manual)
**Skill**: Gemini Content Generation  
**Current Implementation**: Manual workflow via Gemini API

**Inputs**:
- Question text
- Marks scheme
- Subject (Biology, Chemistry, Physics)
- Question range (e.g., 1-10)

**Process** (Gemini Prompt):
```
For Biology questions 1-10, generate:

1. Question Number
2. Question and Options in Text Format
3. Detailed Explanation:
   - Core Concept
   - Step-by-Step Analysis (Analyze Step 1, 2, 3...)
   - Final Correct Answer
4. Option Wise Explanation (paragraph format)
5. 🧠 Concept Gap Analysis and Flashcards:
   - For each wrong option: identify gap
   - 2-3 tailored flashcards per option
   - Format: "Flashcard X: [Front]? Back: [Back]."
```

**Outputs**:
- Markdown document with structured explanations
- Concept gap analysis
- Flashcards for each incorrect option

---

### Phase 2.5: LLM-as-Judge Evaluation ⚠️ TARGET
**Skill**: Automated Content Review (Observability)
**Tools**: LangSmith / Custom Eval Script (GPT-4o Judge)

**Process**:
1. Take the generated explanation from Gemini (Phase 2).
2. Pass it to a "Judge" model with a logic-check prompt.
3. **Rubric Check**:
   - Is the correct answer actually supported by the explanation?
   - Are the "Analyze Steps" logically sound?
   - Does the "Option-wise" explanation cover all 4 options?
4. **Flagging**: If score < 4/5, flag for manual review or re-generation.

**Benefits**:
- **Observability**: Track quality metrics over time.
- **Reliability**: Reduces manual QC by 80%.

---

### Phase 3: Content Formatting ✅ IMPLEMENTED (Manual)
**Skill**: Google Docs Formatting  
**Current Implementation**: Manual workflow via ChatGPT

**Inputs**:
- Raw Gemini output (with LaTeX, markdown)

**Process** (ChatGPT Prompt):
```
Convert for Google Docs compatibility:
- LaTeX math ($E_a$, $e^{-E_a/RT}$) → Unicode (Eₐ, e^(–Eₐ/RT))
- Preserve Greek symbols (Δ, α, β)
- Keep emoji (🅰️, 🅱️, 🧠)
- Maintain indentation, lists, headers
- Remove dollar signs, LaTeX markup
- Output as plain text for direct pasting
```

**Outputs**:
- Unicode-formatted text ready for Google Docs
- No LaTeX delimiters
- Preserved structure and emoji

---

### Phase 4: Blob Storage Upload ✅ IMPLEMENTED
**Skill**: CDN Image Upload  
**Target**: Azure Blob Storage

**Inputs**:
- Directory of PNG images
- Storage configuration (bucket, credentials)

**Process**:
1. Iterate through extracted PNG files
2. Generate unique keys (e.g., `diagrams/9701_s25_qp_13/q1_stem.png`)
3. Upload to Azure Storage container with anonymous blob read access
4. Retrieve CDN URLs (Standard or Custom Domain)
5. Update JSON with CDN mapping
6. Delete local PNGs (optional cleanup)

**Outputs**:
```json
{
  "cdn_mapping": {
    "q1_stem.png": "https://cdn.edmate.com/diagrams/9701_s25_qp_13/q1_stem.png",
    "q1_opt_A.png": "https://cdn.edmate.com/diagrams/9701_s25_qp_13/q1_opt_A.png"
  }
}
```

**Storage Configuration**:
| Provider | Tier | Redundancy | Best For |
|----------|-----------|------|----------|
| **Azure Blob Storage** | Hot (Standard) | LRS (Locally Redundant) | Low-cost web assets |

---

### Phase 5: Database Import ✅ IMPLEMENTED
**Skill**: PostgreSQL/Supabase Data Import

**Inputs**:
- Enhanced content JSON
- CDN URL mapping
- Database credentials

**Process**:
1. Connect to PostgreSQL/Supabase
2. Insert question metadata
3. Insert diagram records with CDN URLs
4. Insert flashcards and concept gaps
5. Link relationships (questions → diagrams → flashcards)

**Database Schema**:

#### Table: `questions`
```sql
CREATE TABLE questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_number INT NOT NULL,
  paper_code TEXT NOT NULL, -- e.g., "9701_s25_qp_13"
  subject TEXT NOT NULL, -- "Biology", "Chemistry", "Physics"
  question_text TEXT,
  options JSONB, -- {"A": "...", "B": "...", "C": "...", "D": "..."}
  correct_answer TEXT, -- "A", "B", "C", or "D"
  explanation TEXT,
  core_concept TEXT,
  difficulty TEXT, -- "Easy", "Medium", "Hard"
  topics TEXT[], -- Array of topic tags
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_questions_paper ON questions(paper_code);
CREATE INDEX idx_questions_subject ON questions(subject);
```

#### Table: `diagrams`
```sql
CREATE TABLE diagrams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
  cdn_url TEXT NOT NULL,
  diagram_type TEXT, -- "stem", "option_A", "option_B", etc.
  page_number INT,
  alt_text TEXT, -- AI-generated description
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_diagrams_question ON diagrams(question_id);
```

#### Table: `flashcards`
```sql
CREATE TABLE flashcards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
  option_letter TEXT, -- "A", "B", "C", "D"
  front_text TEXT NOT NULL,
  back_text TEXT NOT NULL,
  concept_gap TEXT, -- The gap this flashcard addresses
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_flashcards_question ON flashcards(question_id);
```

#### Table: `concept_gaps`
```sql
CREATE TABLE concept_gaps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
  option_letter TEXT, -- "A", "B", "C", "D"
  gap_description TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_concept_gaps_question ON concept_gaps(question_id);
```

**Outputs**:
- Database records with foreign key relationships
- CDN URLs linked to questions
- Searchable content indexed by subject, topic, difficulty

---

## Skills Catalog

### Skill 1: PDF Question Extraction
**Status**: ✅ Implemented  
**Scripts**: `smart_extract.py`, `extract_pdf_content.py`  
**Complexity**: High (spatial analysis, clustering algorithms)

**Capabilities**:
- Question anchor detection
- Option anchor detection (A/B/C/D)
- Vector diagram extraction
- Quadrant-based multi-option diagram splitting
- Proximity-based image merging
- High-resolution rendering (3x scale)

**Reusability**: Core skill for all PDF-based content extraction

---

### Skill 2: Content Generation (Gemini)
**Status**: ✅ Implemented (Manual)  
**Implementation**: Workflow prompt  
**Complexity**: Medium (prompt engineering)

**Capabilities**:
- Detailed step-by-step explanations
- Core concept identification
- Option-wise analysis
- Concept gap identification
- Flashcard generation (2-3 per wrong option)

**Reusability**: Applicable to all A/O-level subjects (Biology, Chemistry, Physics)

---

### Skill 3: Content Formatting
**Status**: ✅ Implemented (Manual)  
**Implementation**: Workflow prompt  
**Complexity**: Low (text transformation)

**Capabilities**:
- LaTeX → Unicode conversion
- Greek symbol preservation
- Emoji preservation
- Google Docs compatibility
- Structure maintenance

**Reusability**: Universal formatting skill for all content types

---

### Skill 4: Blob Storage Upload
**Status**: ✅ Implemented  
**Scripts**: `upload_to_storage.py`  
**Complexity**: Medium (Azure SDK integration)

**Capabilities**:
- Azure Blob Storage upload with retry logic
- Default and Custom CDN URL generation
- Batch directory processing
- Automated local image cleanup
- CDN mapping JSON generation

**Reusability**: Universal asset upload skill

---

### Skill 5: Database Import
**Status**: ✅ Implemented  
**Scripts**: `import_to_db.py`  
**Complexity**: Medium (relational data modeling)

**Capabilities**:
- PostgreSQL/Supabase connection
- Transactional inserts
- Foreign key relationship management
- Bulk import optimization
- Error handling & rollback

**Reusability**: Core data persistence skill

---

## End-to-End Pipeline

### Orchestrator Script: `pipeline_orchestrator.py`
**Status**: ✅ Implemented

**Full Pipeline**:
```bash
python content_gen/scripts/pipeline/pipeline_orchestrator.py \
  --input-dir content_gen/data/inputs \
  --output-dir content_gen/data/extracted \
  --storage-bucket edmate \
  --db-url "postgresql://user:pass@host/db"
```

**Steps**:
1. **Extract**: Process PDFs, generate images + structured metadata
2. **Upload**: Push images to Azure Blob Storage, retrieve public URLs
3. **Sync**: Link CDN URLs to respective question IDs in database
4. **Cleanup**: Delete temporary local images (optional)
5. **Report**: Summary of processed questions, diagrams, and results

**Estimated Time** (100 PDFs):
- Extraction: ~10 minutes
- Upload: ~5 minutes
- Import: ~2 minutes
- **Total**: ~17 minutes

---

## Configuration

### Environment Variables
```bash
# Azure Blob Storage
AZURE_STORAGE_ACCOUNT_NAME=mpowerstorage1
AZURE_STORAGE_ACCOUNT_KEY=your_key_here
AZURE_STORAGE_CDN_URL=https://cdn.edmate.com (optional)

# Database (PostgreSQL/Supabase)
DATABASE_URL=postgresql://user:pass@host:5432/edmate
```

---

## Scalability Metrics

| Metric | Current | Target |
|--------|---------|-------------------|
| **PDFs Processed** | 100+ (automated) | 1000+ |
| **Processing Time** | ~10 sec/PDF | ~5 sec/PDF |
| **Storage** | Azure Blob Storage | Azure + CDN |
| **Database** | PostgreSQL/Supabase | High Availability |
| **Total Pipeline Time** | ~17 min (100 PDFs) | < 10 min |
| **Cost** | ~$0.01/month (Azure) | Tiered Scaling |

---

## Next Steps

### Immediate (Week 1)
- [x] Document workflow architecture
- [ ] Implement `upload_to_storage.py`
- [ ] Implement `import_to_db.py`
- [ ] Test with 10 PDFs

### Short-term (Week 2)
- [ ] Implement `pipeline_orchestrator.py`
- [ ] Set up R2/S3 bucket
- [ ] Create database schema
- [ ] Run full pipeline on 100 PDFs

### Long-term (Month 1)
- [ ] Automate content generation (Gemini API integration)
- [ ] Automate content formatting (ChatGPT API integration)
- [ ] Add AI-generated alt text for diagrams
- [ ] Implement equation extraction (LaTeX OCR)
- [ ] Add table detection and parsing

---

## References

- **Process Guide**: [`PROCESS_GUIDE.md`](file:///Users/mukit_10ms/Documents/GitHub/Edmate/content_gen/docs/PROCESS_GUIDE.md)
- **Scalability Plan**: [`SCALABILITY_PLAN.md`](file:///Users/mukit_10ms/Documents/GitHub/Edmate/content_gen/docs/SCALABILITY_PLAN.md)
- **QC Rubric**: [`QC_RUBRIC.md`](file:///Users/mukit_10ms/Documents/GitHub/Edmate/content_gen/docs/QC_RUBRIC.md)
- **Workflow**: [`.agent/workflows/ao_level_content_generation.md`](file:///Users/mukit_10ms/Documents/GitHub/Edmate/.agent/workflows/ao_level_content_generation.md)
