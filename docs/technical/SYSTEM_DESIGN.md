# Edmate — System Design

**AI-Powered Educational Content Platform for A/O-Level Students**

> Last Updated: March 2026

---

## 1. Overview

Edmate transforms raw Cambridge A/O-Level exam PDFs into structured, pedagogically-rich learning materials. The platform extracts questions and diagrams from PDFs, generates AI-powered explanations and flashcards, stores assets on a CDN, and persists structured data in a PostgreSQL database (Supabase).

### Design Goals

| Goal | Description |
|------|-------------|
| **Accuracy** | Faithful extraction of questions, diagrams, and answer options |
| **Scalability** | Process 100–1,000 exam PDFs in a single pipeline run |
| **Cost Efficiency** | Stay within free/near-free tiers for storage and DB |
| **Extensibility** | Easy to add new subjects, pipeline stages, and AI models |
| **Quality** | LLM-as-Judge evaluation ensures generated content meets a rubric |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Edmate Platform                         │
│                                                                 │
│  ┌──────────┐   ┌──────────────┐   ┌──────────────────────┐   │
│  │  PDF     │──▶│  Extraction  │──▶│  Content Generation  │   │
│  │  Inputs  │   │   Pipeline   │   │ (Any LLM via router) │   │
│  └──────────┘   └──────┬───────┘   └──────────┬───────────┘   │
│                         │                       │               │
│              ┌──────────┴────┐     ┌────────────▼──────────┐   │
│              │  CDN Upload   │     │  LLM-as-Judge QC Eval │   │
│              │ (Cloudflare   │     └────────────┬──────────┘   │
│              │     R2)       │                  │               │
│              └──────┬────────┘     ┌────────────▼──────────┐   │
│                     │              │  Database Import       │   │
│                     └─────────────▶│  (Supabase/PostgreSQL)│   │
│                                    └───────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Pipeline Architecture (Detailed)

```mermaid
graph TB
    A[Raw PDF Files] --> B[Phase 1: Multi-Engine Extraction]
    B -->|vision| V[VisionExtractionAdapter]
    B -->|kit| K[KitExtractionAdapter]
    B -->|lightweight| P[PyMuPDFAdapter]
    
    V --> C[Standardized JSON]
    K --> C
    P --> C
    V --> D[PNG Images]
    K --> D
    
    C --> E[Phase 2: Content Generation - LLM Router]
    E --> F[Enriched Content JSON]
    D --> G[Asset Persistence - Cloudflare R2]
    F --> H[Database Import - Postgres]
    G --> H
```

### Pipeline Phases

| Phase | Name | Status | Key Script |
|-------|------|--------|------------|
| 1 | Multi-Engine Extraction | ✅ Implemented | `adapters/vision_extraction_adapter.py`, `kit_extraction_adapter.py`, `pymupdf_adapter.py` |
| 2 | Content Generation | ✅ Implemented | `content_generator.py`, `model_router.py` |
| 2.5 | LLM-as-Judge QC | ⚠️ Planned | — |
| 3 | Asset Storage | ✅ Implemented | `upload_to_storage.py` |
| 4 | Database Import | ✅ Implemented | `import_to_db.py` |
| — | Orchestration | ✅ Implemented | `pipeline_orchestrator.py` |

---

## 4. Repository Structure

```
Edmate/
├── README.md              # Project overview & quick start
├── ROADMAP.md             # Public product roadmap
├── docs/
│   ├── pedagogy/          # Learning science & QC rubrics
│   ├── technical/         # Architecture, schemas, and workflows
│   ├── product/           # Use cases, PRDs, and plans
│   ├── contributing/      # Guides for developers
│   └── brand/             # Guidelines & assets
└── content_gen/           # AI Pipeline Core
└── qc_viewer/             # Automation Hub (UI + API)
```

---

## 5. Data Flow

```
[PDF File]
    │
    ▼ PyMuPDF + PDF-Extract-Kit
[JSON: questions, options, page refs]
[PNG: diagrams (stem + per-option)]
    │
    ├──▶ [Cloudflare R2] ──▶ [Public CDN URLs]
    │
    ▼ LLM Router API (prompts.py)
[Enhanced JSON: explanation, flashcards, concept gaps]
    │
    ▼ Formatting pass (provider-configurable)
[Unicode-clean text, Google Docs compatible]
    │
    ▼ psycopg2 / supabase-py
[PostgreSQL / Supabase]
```

---

## 6. Database Schema

All tables reside in the Supabase-managed PostgreSQL instance.

### `questions`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | `gen_random_uuid()` |
| `question_number` | INT | Question # in paper |
| `paper_code` | TEXT | e.g. `9701_s25_qp_13` |
| `subject` | TEXT | `Biology`, `Chemistry`, `Physics`, `Math` |
| `question_text` | TEXT | Full stem text |
| `options` | JSONB | `{"A": "...", "B": "..."}` |
| `correct_answer` | TEXT | `A`, `B`, `C`, or `D` |
| `explanation` | TEXT | AI-generated explanation |
| `core_concept` | TEXT | Key concept covered |
| `difficulty` | TEXT | `Easy`, `Medium`, `Hard` |
| `topics` | TEXT[] | Array of topic tags |
| `created_at` | TIMESTAMP | Auto |
| `updated_at` | TIMESTAMP | Auto |

### `diagrams`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `question_id` | UUID FK → `questions` | Cascade delete |
| `cdn_url` | TEXT | Cloudflare R2 public URL |
| `diagram_type` | TEXT | `stem`, `option_A`..`option_D` |
| `page_number` | INT | Source PDF page |
| `alt_text` | TEXT | AI-generated description |
| `created_at` | TIMESTAMP | Auto |

### `flashcards`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `question_id` | UUID FK → `questions` | |
| `option_letter` | TEXT | `A`–`D` (wrong option this targets) |
| `front_text` | TEXT | Question side |
| `back_text` | TEXT | Answer side |
| `concept_gap` | TEXT | Gap this flashcard addresses |
| `created_at` | TIMESTAMP | Auto |

### `concept_gaps`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `question_id` | UUID FK → `questions` | |
| `option_letter` | TEXT | Which wrong option |
| `gap_description` | TEXT | Description of the knowledge gap |
| `created_at` | TIMESTAMP | Auto |

### Key Indexes

```sql
CREATE INDEX idx_questions_paper   ON questions(paper_code);
CREATE INDEX idx_questions_subject ON questions(subject);
CREATE INDEX idx_diagrams_question ON diagrams(question_id);
CREATE INDEX idx_flashcards_question ON flashcards(question_id);
CREATE INDEX idx_concept_gaps_question ON concept_gaps(question_id);
```

---

## 7. Infrastructure & Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Database** | Supabase (PostgreSQL) | Managed, free tier |
| **File Storage / CDN** | Cloudflare R2 | Zero egress fees, S3-compatible |
| **AI — Generation** | Provider-configurable via LiteLLM | Explanations, flashcards |
| **AI — Formatting** | Provider-configurable via LiteLLM | LaTeX → Unicode, Docs compatibility |
| **PDF Extraction** | PyMuPDF + PDF-Extract-Kit | Vector diagram rendering |
| **Language** | Python 3.8+ | Pipeline scripts |
| **Config** | `.env` + `python-dotenv` | Credentials management |

### Environment Variables

```bash
# Cloudflare R2 / AWS S3
CLOUDFLARE_R2_ACCESS_KEY=...
CLOUDFLARE_R2_SECRET_KEY=...
CLOUDFLARE_R2_ENDPOINT=https://<account>.r2.cloudflarestorage.com
R2_BUCKET_NAME=edmate-diagrams

# Database
DATABASE_URL=postgresql://user:pass@host:5432/edmate

# AI APIs
LITELLM_API_KEY=...
# Optional provider-specific aliases:
GEMINI_API_KEY=...
OPENAI_API_KEY=...
```

---

## 8. Content Generation Design

### AI Prompt Architecture (`prompts.py`)

Content generation follows a structured chain:

1. **Question + Mark Scheme** → router-selected generation model
2. **Output**: Explanation, step-by-step analysis, correct answer, option-wise analysis, flashcards
3. **Formatting pass** → router-selected formatting model converts LaTeX to Unicode for Google Docs

### LLM-as-Judge QC (Phase 2.5 — Planned)

A second model acts as evaluator on generated output before database import:

| Check | Criterion |
|-------|-----------|
| Answer Validity | Correct answer is supported by the explanation |
| Logical Soundness | "Analyze Steps" are logically consistent |
| Coverage | All 4 options are covered in option-wise explanation |
| Flashcard Alignment | Flashcards map to identifiable concept gaps |

**Threshold**: Score ≥ 4/5 required; otherwise flagged for manual review or re-generation.

---

## 9. Supported Subjects

| Subject | A-Level Code | O-Level Code |
|---------|-------------|-------------|
| Biology | 9700 | 5090 |
| Chemistry | 9701 | 5070 |
| Physics | 9702 | 5054 |
| Mathematics | 9709 | 4024 |

---

## 10. Performance Benchmarks

| Stage | 100 PDFs | Notes |
|-------|----------|-------|
| PDF Extraction | ~10 min | ~2,000 questions, ~5,000 images |
| CDN Upload | ~5 min | ~500 MB of PNGs |
| DB Import | ~2 min | Bulk inserts |
| **Total** | **~17 min** | End-to-end pipeline |

**Estimated monthly cost**: ~$0.01 (R2 storage + Supabase free tier)

---

## 11. Scalability

Edmate is designed to scale from single-operator use to a fully automated batch processing system.

### Vertical Scaling (Current)
The pipeline runs on a single machine. Python's `multiprocessing` can be introduced to saturate all CPU cores during PDF extraction.

### Horizontal Scaling (Planned)
For large-scale ingestion (1,000+ PDFs), the pipeline can be distributed:

| Strategy | Description |
|----------|-------------|
| **Worker Pool** | Split PDF list across N workers using `concurrent.futures.ProcessPoolExecutor` |
| **Job Queue** | Push PDF paths to a Redis / RQ queue; multiple worker processes consume and process independently |
| **Stateless Workers** | Each worker only reads PDFs and writes to shared DB/CDN — no shared local state |

### Async Processing
For AI API calls, async I/O reduces idle time waiting for API responses:

```python
import asyncio
import aiohttp

async def generate_content_batch(questions: list) -> list:
    async with aiohttp.ClientSession() as session:
        tasks = [generate_content(session, q) for q in questions]
        return await asyncio.gather(*tasks)  # Concurrent API calls
```

**Scalability Targets**:

| Metric | Current | Target |
|--------|---------|--------|
| PDFs / run | 100 | 1,000+ |
| Pipeline workers | 1 | N (horizontal) |
| API concurrency | Sequential | Async (10–50 parallel) |
| Processing time (100 PDFs) | ~17 min | < 10 min |

---

## 12. Availability

Edmate relies on managed infrastructure that provides built-in availability guarantees.

### Database — Supabase (PostgreSQL)

| Feature | Detail |
|---------|--------|
| **Replication** | Supabase runs primary + read replicas; automatic failover on primary failure |
| **Backups** | Daily automated backups on paid tier; point-in-time recovery (PITR) available |
| **Uptime SLA** | 99.9% (Supabase Pro) |

### File Storage — Cloudflare R2

| Feature | Detail |
|---------|--------|
| **Redundancy** | Objects stored across multiple availability zones by default |
| **Durability** | 99.999999999% (11 nines) object durability |
| **CDN Availability** | Served via Cloudflare's global edge network (300+ PoPs) |

### Pipeline Availability
The pipeline is a batch process, not a long-running service, so traditional load balancing is not applicable at this stage. Availability is ensured by:
- **Idempotency**: Re-running the pipeline on the same PDFs does `UPSERT` — no duplicate rows
- **Checkpoint Logging**: Pipeline logs which PDFs have been processed; on failure, it can resume from the last successful PDF
- **Retry Logic**: See Section 13 (Reliability)

---

## 13. Reliability

### Error Handling & Retry Logic

Each pipeline phase wraps its operations in structured error handling:

```python
import time
import logging

def run_with_retry(fn, args, max_retries=3, backoff=2.0):
    """Retry a pipeline step with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return fn(*args)
        except Exception as e:
            wait = backoff ** attempt
            logging.warning(f"Attempt {attempt+1} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)
    logging.error(f"All {max_retries} attempts failed for {fn.__name__}")
    return None  # Caller decides to skip or abort
```

**Per-phase error policy**:

| Phase | On Failure | Retry? |
|-------|------------|--------|
| PDF Extraction | Log + skip PDF | No (bad PDF is bad PDF) |
| CDN Upload | Log + retry | Yes — 3× with backoff |
| LLM API | Log + retry | Yes — 3× with backoff |
| DB Import | Rollback transaction + log | Yes — 2× |
| Full Pipeline | Write failure report | No — manual intervention |

### Monitoring & Logging

All pipeline runs produce structured logs:

```
logs/
└── runs/
    └── 2026-03-15_12-00-00/
        ├── pipeline.log       # Full run log (INFO/WARNING/ERROR)
        ├── failed_pdfs.txt    # List of PDFs that failed extraction
        └── summary.json       # Stats: total, success, failed, skipped
```

**Log format** (structured):
```json
{ "ts": "2026-03-15T12:00:00Z", "level": "INFO", "phase": "extraction",
  "paper": "9701_s25_qp_13", "questions": 40, "diagrams": 15 }
```

**Key metrics tracked per run**:

| Metric | Description |
|--------|-------------|
| `pdfs_processed` | Total PDFs attempted |
| `pdfs_failed` | PDFs that errored out |
| `questions_extracted` | Total questions written to DB |
| `diagrams_uploaded` | Total CDN uploads |
| `api_errors` | LLM API failures |
| `qc_failures` | Items flagged by LLM-as-Judge |

### Automated Tests

| Test Type | Scope | Tool |
|-----------|-------|------|
| **Unit tests** | Per-function logic (extraction, parsing) | `pytest` |
| **Integration tests** | End-to-end on 1–2 sample PDFs | `pytest` + fixtures |
| **QC eval tests** | LLM-as-Judge scoring validation | Custom eval script |
| **DB schema tests** | FK constraints, index coverage | `pytest` + test DB |

Test command:
```bash
pytest content_gen/tests/ -v --tb=short
```

---

## 14. Performance

### Caching Strategy

To avoid redundant AI API calls (which are slow and costly), responses are cached:

| Cache Layer | What Is Cached | Implementation |
|-------------|---------------|----------------|
| **File Cache** | LLM responses, keyed by `(paper_code, question_number, prompt_hash)` | JSON files in `data/cache/` |
| **DB Cache** | Questions already in DB are skipped on re-run (check by `paper_code + question_number`) | SQL `ON CONFLICT DO NOTHING` |
| **CDN Cache** | Uploaded images are not re-uploaded; keyed by R2 object key existence check | R2 `head_object` check |

```python
import hashlib, json, os

CACHE_DIR = "content_gen/data/cache"

def get_cached_response(paper_code: str, q_num: int, prompt: str):
    key = hashlib.md5(f"{paper_code}_{q_num}_{prompt}".encode()).hexdigest()
    path = f"{CACHE_DIR}/{key}.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)  # Cache hit
    return None  # Cache miss — call API

def save_cached_response(paper_code, q_num, prompt, response):
    key = hashlib.md5(f"{paper_code}_{q_num}_{prompt}".encode()).hexdigest()
    with open(f"{CACHE_DIR}/{key}.json", "w") as f:
        json.dump(response, f)
```

### Database Indexing

Indexes already defined (see Section 6). Additional performance indexes for future query patterns:

```sql
-- For full-text search on question content (future student portal)
CREATE INDEX idx_questions_fts ON questions USING gin(to_tsvector('english', question_text));

-- For topic-based filtering
CREATE INDEX idx_questions_topics ON questions USING gin(topics);

-- For difficulty-filtered queries
CREATE INDEX idx_questions_difficulty ON questions(difficulty);
```

### API Rate Limiting

LLM providers enforce per-minute token/request limits. The pipeline uses a token bucket approach:

```python
import time

class RateLimiter:
    def __init__(self, requests_per_minute: int):
        self.rpm = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.last_call = 0.0

    def wait(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()

provider_limiter = RateLimiter(requests_per_minute=60)  # tune per provider tier
```

---

## 15. Security

| Area | Measure |
|------|---------|
| **API Keys** | Stored in `.env`, never committed to Git (`.gitignore` enforced) |
| **DB Access** | Supabase Row Level Security (RLS) enabled — pipeline uses a service-role key scoped to write operations only |
| **R2 Bucket** | Objects are public-read (CDN images); write access requires signed credentials |
| **Secrets Rotation** | API keys rotated quarterly or on suspected exposure |
| **`.gitignore`** | `.env`, `data/inputs/`, `data/extracted/`, `data/cache/` all excluded from version control |

---

## 16. Deployment

The pipeline is currently a **locally-run batch process**. Planned deployment options:

| Option | Description | When |
|--------|-------------|------|
| **Local CLI** | `python pipeline_orchestrator.py` on developer machine | Now (current) |
| **Cron Job** | Schedule on a dedicated server or Mac Mini | Short-term |
| **GitHub Actions** | Trigger pipeline on new PDF commit to `data/inputs/` | Short-term |
| **Railway / Fly.io** | Containerised pipeline worker for always-on processing | Long-term |

### Running the Pipeline

```bash
# Full automated pipeline
python content_gen/scripts/pipeline/pipeline_orchestrator.py \
  --input-dir content_gen/data/inputs \
  --output-dir content_gen/data/extracted \
  --storage-bucket edmate-diagrams \
  --db-url "$DATABASE_URL"

# Resume from failed run (skip already-processed PDFs)
python content_gen/scripts/pipeline/pipeline_orchestrator.py \
  --input-dir content_gen/data/inputs \
  --resume
```

---

## 17. Roadmap

### Immediate (Phase 1)
- [x] PDF extraction pipeline
- [x] CDN upload (Cloudflare R2)
- [x] Database import
- [x] Manual content generation (router-configured provider)

### Short-term (Phase 2)
- [ ] Automated LLM API integration (remove manual step)
- [ ] Automated formatting model integration
- [ ] LLM-as-Judge QC pipeline (Phase 2.5)
- [ ] Alt text generation for diagrams (provider-configurable vision model)

### Long-term (Phase 3)
- [ ] Equation extraction (LaTeX-OCR or Mathpix)
- [ ] Table detection and parsing with `pdfplumber`
- [ ] Student-facing web application
- [ ] Adaptive learning / spaced repetition system
- [ ] Multi-year paper ingestion (bulk historical papers)

---

## 18. References

| Document | Path |
|----------|------|
| Agentic Workflow | [`AGENTIC_WORKFLOW.md`](AGENTIC_WORKFLOW.md) |
| Process Guide | [`../contributing/PROCESS_GUIDE.md`](../contributing/PROCESS_GUIDE.md) |
| QC Rubric | [`../pedagogy/QC_RUBRIC.md`](../pedagogy/QC_RUBRIC.md) |
| Scalability Plan | [`SCALABILITY_PLAN.md`](SCALABILITY_PLAN.md) |
| Skills Catalog | [`../product/SKILLS_CATALOG.md`](../product/SKILLS_CATALOG.md) |
| Content Gen README | [`../../content_gen/README.md`](../../content_gen/README.md) |
