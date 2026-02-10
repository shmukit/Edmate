# Content Generation Scripts

## Overview
Organized scripts for A/O-level content generation using **PDF-Extract-Kit** as the core extraction engine.

---

## Folder Structure

```
scripts/
├── extraction/          # PDF extraction using PDF-Extract-Kit
│   ├── pdf_extract_kit_wrapper.py
│   └── __init__.py
├── processing/          # Data processing (upload, import)
│   ├── upload_to_storage.py
│   ├── import_to_db.py
│   └── __init__.py
├── pipeline/            # End-to-end orchestration
│   ├── pipeline_orchestrator.py
│   └── __init__.py
├── docx/                # DOCX text extraction
│   ├── extract_text.py
│   └── process_batch.py
├── debug/               # Debugging and testing tools
│   ├── ai_extract_test.py
│   ├── analyze_pdf.py
│   ├── check_spatial.py
│   ├── debug_anchors.py
│   └── debug_drawings.py
└── archive/             # Deprecated scripts (do not use)
    ├── smart_extract.py
    ├── extract_pdf_content.py
    ├── extract_diagram.py
    └── README.md
```

---

## Core Scripts

### 1. PDF Extraction (extraction/)

#### `pdf_extract_kit_wrapper.py`
**Purpose**: Extract questions and diagrams from PDFs using PDF-Extract-Kit AI models

**Features**:
- ✅ AI-powered layout detection (figures, tables, formulas)
- ✅ High-resolution image extraction
- ✅ Question number detection
- ✅ Compatible output format with legacy scripts

**Usage**:
```bash
python extraction/pdf_extract_kit_wrapper.py \
  path/to/exam.pdf \
  --output-dir data/extracted
```

**Output**:
- JSON file: `{pdf_name}_extracted.json`
- PNG images: `images/q{num}_{type}.png`

---

### 2. Processing (processing/)

#### `upload_to_storage.py`
**Purpose**: Upload images to Cloudflare R2 or AWS S3

**Usage**:
```bash
python processing/upload_to_storage.py \
  data/extracted/images \
  --provider r2 \
  --bucket edmate-diagrams \
  --base-path "diagrams/9701_s25_qp_13"
```

#### `import_to_db.py`
**Purpose**: Import questions and diagrams to PostgreSQL/Supabase

**Usage**:
```bash
python processing/import_to_db.py \
  data/extracted/9701_s25_qp_13_extracted.json \
  --cdn-mapping cdn_mapping.json \
  --paper-code 9701_s25_qp_13 \
  --subject Biology \
  --db-url "postgresql://user:pass@host:5432/edmate"
```

---

### 3. Pipeline (pipeline/)

#### `pipeline_orchestrator.py`
**Purpose**: End-to-end pipeline (extract → upload → import)

**Usage**:
```bash
# Single PDF
python pipeline/pipeline_orchestrator.py \
  --single-pdf path/to/exam.pdf \
  --output-dir data/extracted \
  --subject Biology \
  --storage-provider r2 \
  --storage-bucket edmate-diagrams \
  --db-url "postgresql://user:pass@host:5432/edmate"

# Batch processing
python pipeline/pipeline_orchestrator.py \
  --input-dir data/inputs \
  --output-dir data/extracted \
  --subject Chemistry \
  --storage-provider r2 \
  --storage-bucket edmate-diagrams \
  --db-url "postgresql://user:pass@host:5432/edmate" \
  --cleanup-images
```

---

### 4. DOCX Processing (docx/)

#### `extract_text.py`
**Purpose**: Extract text from DOCX files

**Usage**:
```bash
python docx/extract_text.py path/to/document.docx
```

#### `process_batch.py`
**Purpose**: Batch process DOCX files

**Usage**:
```bash
python docx/process_batch.py
```

---

### 5. Debug Tools (debug/)

#### `ai_extract_test.py`
**Purpose**: Test PDF-Extract-Kit on specific pages

#### `analyze_pdf.py`
**Purpose**: Analyze PDF structure (images, text, tables)

**Usage**:
```bash
python debug/analyze_pdf.py path/to/exam.pdf
```

#### `check_spatial.py`, `debug_anchors.py`, `debug_drawings.py`
**Purpose**: Debug spatial layout, anchors, and drawings

---

## Key Changes from Previous Version

### ✅ What Changed

1. **Core Extraction**: Now uses **PDF-Extract-Kit** (AI-powered) instead of custom heuristics
2. **Organized Structure**: Scripts grouped by purpose (extraction/, processing/, pipeline/, etc.)
3. **Archived Old Code**: Redundant scripts moved to `archive/` folder
4. **Updated Pipeline**: `pipeline_orchestrator.py` now uses PDF-Extract-Kit wrapper

### ❌ What Was Removed

- `smart_extract.py` → Replaced by `extraction/pdf_extract_kit_wrapper.py`
- `extract_pdf_content.py` → Replaced by `extraction/pdf_extract_kit_wrapper.py`
- `extract_diagram.py` → Replaced by `extraction/pdf_extract_kit_wrapper.py`

### 📦 Module Structure

All folders are now Python modules with `__init__.py` files, allowing clean imports:

```python
from extraction import PDFExtractKitWrapper
from processing import StorageUploader, DatabaseImporter
from pipeline import PipelineOrchestrator
```

---

## Migration Guide

### If you were using `smart_extract.py`:

**Old**:
```python
from smart_extract import SmartQuestionExtractor

extractor = SmartQuestionExtractor(pdf_path, output_dir)
result = extractor.extract()
```

**New**:
```python
from extraction.pdf_extract_kit_wrapper import PDFExtractKitWrapper

extractor = PDFExtractKitWrapper(pdf_path, output_dir)
result = extractor.extract()
```

**Output format remains the same** - no changes needed to downstream code!

---

## Requirements

See `../requirements.txt` for dependencies. Key additions:
- PDF-Extract-Kit (already installed in `../tools/PDF-Extract-Kit`)
- PyMuPDF (fitz)
- boto3 (for cloud storage)
- psycopg2 (for database)

---

## Next Steps

1. **Test the new extraction**:
   ```bash
   python extraction/pdf_extract_kit_wrapper.py path/to/test.pdf
   ```

2. **Run the full pipeline**:
   ```bash
   python pipeline/pipeline_orchestrator.py --single-pdf path/to/test.pdf --subject Biology
   ```

3. **Review archived scripts** in `archive/` folder (for reference only)

---

## Support

For issues or questions:
- Check `archive/README.md` for migration details
- Review `../docs/AGENTIC_WORKFLOW.md` for system architecture
- See `../docs/SKILLS_CATALOG.md` for skill definitions
