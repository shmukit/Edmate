# Content Generation System - Quick Start Guide

## Overview
Complete agentic workflow for A/O-level educational content generation.

**Pipeline**: PDF → Extraction → Storage Upload → Database Import

---

## Setup

### 1. Install Dependencies
```bash
cd content_gen
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Create Database Schema
```bash
python scripts/import_to_db.py \
  --create-schema \
  --db-url "postgresql://user:pass@host:5432/edmate"
```

---

## Usage

### Single PDF Processing (Azure)
```bash
python scripts/pipeline/pipeline_orchestrator.py \
  --single-pdf "data/inputs/9701_s25_qp_13.pdf" \
  --output-dir "data/extracted" \
  --subject Biology \
  --storage-bucket edmate \
  --db-url "postgresql://user:pass@host:5432/edmate"
```

### Batch Processing
```bash
python scripts/pipeline/pipeline_orchestrator.py \
  --input-dir "data/inputs" \
  --output-dir "data/extracted" \
  --subject Chemistry \
  --difficulty Medium \
  --topics "Organic Chemistry" "Alkenes" \
  --storage-bucket edmate \
  --db-url "postgresql://user:pass@host:5432/edmate" \
  --cleanup-images
```

### Individual Steps

#### Extract PDF Only
```bash
python scripts/smart_extract.py
# Or edit the __main__ section with your PDF path
```

#### Upload Images Only (Azure)
```bash
python scripts/processing/upload_to_storage.py \
  data/extracted/images \
  --container edmate \
  --base-path "diagrams/9701_s25_qp_13" \
  --output data/extracted/cdn_mapping.json
```

#### Import to Database Only
```bash
python scripts/import_to_db.py \
  data/extracted/9701_s25_qp_13_smart_extracted.json \
  --cdn-mapping data/extracted/cdn_mapping.json \
  --paper-code 9701_s25_qp_13 \
  --subject Biology \
  --db-url "postgresql://user:pass@host:5432/edmate"
```

---

## Documentation

- **[AGENTIC_WORKFLOW.md](docs/AGENTIC_WORKFLOW.md)**: Complete workflow architecture
- **[SKILLS_CATALOG.md](docs/SKILLS_CATALOG.md)**: Formal skills definitions
- **[PROCESS_GUIDE.md](docs/PROCESS_GUIDE.md)**: Content generation guide
- **[SCALABILITY_PLAN.md](docs/SCALABILITY_PLAN.md)**: Scalability strategy

---

## File Structure

```
content_gen/
├── scripts/
│   ├── smart_extract.py           # PDF extraction
│   ├── upload_to_storage.py       # Blob storage upload
│   ├── import_to_db.py            # Database import
│   └── pipeline_orchestrator.py   # End-to-end pipeline
├── data/
│   ├── inputs/                    # Raw PDFs
│   └── extracted/                 # JSON + images
├── docs/
│   ├── AGENTIC_WORKFLOW.md
│   ├── SKILLS_CATALOG.md
│   ├── PROCESS_GUIDE.md
│   └── SCALABILITY_PLAN.md
├── requirements.txt
└── .env.example
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_STORAGE_ACCOUNT_NAME` | Yes | Azure storage account name |
| `AZURE_STORAGE_ACCOUNT_KEY` | Yes | Azure storage access key |
| `AZURE_STORAGE_CDN_URL` | No | Optional custom CDN domain for Azure |
| `DATABASE_URL` | Yes | PostgreSQL connection string |

---

## Database Schema

See [AGENTIC_WORKFLOW.md](docs/AGENTIC_WORKFLOW.md#phase-5-database-import) for complete schema.

**Tables**:
- `questions`: Question metadata
- `diagrams`: CDN URLs linked to questions
- `flashcards`: Generated flashcards
- `concept_gaps`: Identified knowledge gaps

---

## Performance

**100 PDFs** (~2000 questions, ~5000 images):
- Extraction: ~10 minutes
- Upload: ~5 minutes
- Import: ~2 minutes
- **Total**: ~17 minutes

**Cost** (monthly):
- R2 Storage (500MB): ~$0.01
- Database (Supabase free tier): $0
- **Total**: ~$0.01/month

---

## Troubleshooting

### Import Error: "relation does not exist"
Run schema creation:
```bash
python scripts/import_to_db.py --create-schema --db-url "..."
```

### Upload Error: "Access Denied"
Check credentials in `.env` and bucket permissions.

### Extraction produces empty images
Verify PDF has vector graphics (not scanned images).

---

## Next Steps

1. ✅ Extract PDFs → JSON + PNG
2. ✅ Upload to R2/S3
3. ✅ Import to database
4. ⚠️ Automate content generation (Gemini API)
5. ⚠️ Automate formatting (ChatGPT API)
6. ⚠️ Add equation extraction (LaTeX OCR)
