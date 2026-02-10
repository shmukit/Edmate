# Content Generation Agentic Workflow Architecture

## Executive Summary

This document defines the **complete agentic workflow** for A/O-level educational content generation at Edmate. The system transforms raw exam PDFs into structured, pedagogically-rich content stored in a database with CDN-hosted assets.

**Current Status**: ✅ PDF Extraction → JSON + PNG | ⚠️ Missing: Database & Blob Storage Integration

---

## System Architecture

```mermaid
graph TB
    A[Raw PDF Files] --> B[Skill 1: PDF Extraction]
    B --> C[Structured JSON]
    B --> D[PNG Images]
    C --> E[Skill 2: Content Generation]
    E --> F[Enhanced Content JSON]
    F --> G[Skill 3: Content Formatting]
    G --> H[Google Docs Compatible Text]
    D --> I[Skill 4: Blob Storage Upload]
    I --> J[CDN URLs - R2/S3]
    H --> K[Skill 5: Database Import]
    J --> K
    K --> L[PostgreSQL/Supabase]
    L --> M[Production System]
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

### Phase 4: Blob Storage Upload ⚠️ NOT IMPLEMENTED
**Skill**: CDN Image Upload  
**Target**: Cloudflare R2 or AWS S3

**Inputs**:
- Directory of PNG images
- Storage configuration (bucket, credentials)

**Process**:
1. Iterate through extracted PNG files
2. Generate unique keys (e.g., `diagrams/9701_s25_qp_13/q1_stem.png`)
3. Upload to R2/S3 with public-read ACL
4. Retrieve CDN URLs
5. Update JSON with CDN URLs
6. Delete local PNGs (optional)

**Outputs**:
```json
{
  "cdn_mapping": {
    "q1_stem.png": "https://cdn.edmate.com/diagrams/9701_s25_qp_13/q1_stem.png",
    "q1_opt_A.png": "https://cdn.edmate.com/diagrams/9701_s25_qp_13/q1_opt_A.png"
  }
}
```

**Storage Recommendations**:
| Provider | Free Tier | Cost | Best For |
|----------|-----------|------|----------|
| **Cloudflare R2** | 10GB | $0.015/GB/month | Zero egress fees |
| **AWS S3** | 5GB (12 months) | $0.023/GB/month | Mature ecosystem |
| **Supabase Storage** | 1GB | $0.021/GB/month | Integrated with Supabase DB |

---

### Phase 5: Database Import ⚠️ NOT IMPLEMENTED
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
**Status**: ⚠️ Not Implemented  
**Target Script**: `upload_to_storage.py`  
**Complexity**: Medium (API integration)

**Capabilities**:
- R2/S3 upload with retry logic
- CDN URL generation
- Batch processing
- Local cleanup (optional)
- URL mapping generation

**Reusability**: Universal asset upload skill

---

### Skill 5: Database Import
**Status**: ⚠️ Not Implemented  
**Target Script**: `import_to_db.py`  
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
**Status**: ⚠️ Not Implemented

**Full Pipeline**:
```bash
python content_gen/scripts/pipeline_orchestrator.py \
  --input-dir content_gen/data/inputs \
  --output-dir content_gen/data/extracted \
  --storage-provider r2 \
  --db-connection postgresql://user:pass@host/db
```

**Steps**:
1. **Extract**: Process all PDFs in input directory
2. **Upload**: Upload PNGs to R2/S3, get CDN URLs
3. **Import**: Insert questions + diagrams into database
4. **Cleanup**: Delete local PNGs (optional)
5. **Report**: Generate summary (questions processed, images uploaded, errors)

**Estimated Time** (100 PDFs):
- Extraction: ~10 minutes
- Upload: ~5 minutes
- Import: ~2 minutes
- **Total**: ~17 minutes

---

## Configuration

### Environment Variables
```bash
# Blob Storage (R2)
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=edmate-diagrams
R2_PUBLIC_URL=https://cdn.edmate.com

# Blob Storage (S3)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_S3_BUCKET=edmate-diagrams
AWS_REGION=us-east-1

# Database (PostgreSQL/Supabase)
DATABASE_URL=postgresql://user:pass@host:5432/edmate
# OR
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key
```

---

## Scalability Metrics

| Metric | Current | Target (Phase 4-5) |
|--------|---------|-------------------|
| **PDFs Processed** | 1-10 (manual) | 100-500 (automated) |
| **Processing Time** | ~30 min/PDF | ~10 sec/PDF |
| **Storage** | Local disk | R2/S3 CDN |
| **Database** | None | PostgreSQL/Supabase |
| **Total Pipeline Time** | N/A | ~17 min (100 PDFs) |
| **Cost** | $0 | ~$0.50/month (R2 + DB) |

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
