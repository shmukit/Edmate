# DB Import Pipeline

This document describes the end-to-end process for importing extracted Cambridge exam question data into the production database (`mukit_edmate_frontend`).

---

## Overview

```
PDF Papers
   │
   ▼
[Extraction]  ──► JSON files (content_gen/data/extracted/)
   │
   ▼
[Upload]      ──► CDN URLs (Cloudflare R2 / Azure Blob)
   │
   ▼
[Import]      ──► PostgreSQL (192.168.19.30 / mukit_edmate_frontend)
```

The import step is handled by:

```
content_gen/scripts/processing/import_to_db.py
```

---

## Database Connection

| Field    | Value                              |
|----------|------------------------------------|
| Host     | `192.168.19.30`                    |
| Port     | `5432`                             |
| Database | `mukit_edmate_frontend`            |
| User     | `kobo`                             |
| Password | `DB@mPower@786`                    |

> **⚠️ Network requirement**: This is a private LAN IP. You must be on the office network (192.168.19.x subnet) or connected via VPN to reach it.

The connection string is set in `content_gen/.env`:

```env
DATABASE_URL=postgresql://kobo:DB%40mPower%40786@192.168.19.30:5432/mukit_edmate_frontend
```

> Note: `@` in the password is URL-encoded as `%40` in the connection string.

---

## Target Tables

Questions are routed to subject-specific tables based on **subject** and **grade level**:

| Subject   | Grade   | Table                       |
|-----------|---------|-----------------------------|
| Biology   | A-Level | `biology_questions`         |
| Chemistry | A-Level | `chemistry_questions`       |
| Physics   | A-Level | `physics_questions`         |
| Biology   | IGCSE   | `igcse_biology_questions`   |
| Chemistry | IGCSE   | `igcse_chemistry_questions` |
| Physics   | IGCSE   | `igcse_physics_questions`   |

All tables share an identical column structure:

| Column               | Type      | Notes                                        |
|----------------------|-----------|----------------------------------------------|
| `id`                 | varchar   | UUID, primary key                            |
| `title`              | text      | Question text (raw extracted text)           |
| `type`               | text      | Always `"MCQ"` for now                       |
| `difficulty_level`   | text      | `Easy` / `Medium` / `Hard`                  |
| `source`             | text      | Always `"PastPaper"`                         |
| `subject_id`         | varchar   | FK → `subjects.id`                           |
| `topic_id`           | varchar   | FK → `topics.id` (defaults to `unknown-topic`) |
| `subtopic_id`        | varchar   | Optional FK → `subtopics.id`                 |
| `options`            | text[]    | `[A, B, C, D]` option texts                  |
| `correct_options`    | text[]    | Correct answer(s) — filled in QC step        |
| `option_explanations`| text[]    | AI-generated explanations — filled in QC step |
| `other_contents`     | text      | CDN URLs for attached images (newline-joined) |
| `year`               | varchar   | e.g. `"2025"`                                |
| `session`            | varchar   | `"M/J"` (May/June) or `"O/N"` (Oct/Nov)     |
| `variant`            | varchar   | Paper variant, e.g. `"11"`                   |
| `question_identifier`| varchar   | Unique key: `<paper_code>/Q<n>`              |
| `grade`              | varchar   | `"A-Level"` or `"IGCSE"`                    |
| `exam_board`         | varchar   | `"Cambridge"`                                |
| `is_active`          | boolean   | Always `true` on import                      |
| `is_verified`        | boolean   | `false` until QC passes                      |
| `created_at`         | timestamp |                                              |
| `updated_at`         | timestamp |                                              |

### Known Subject IDs

| Subject     | UUID                                   |
|-------------|----------------------------------------|
| Biology     | `f9232f73-7e92-4f86-823f-7c510629b79c` |
| Chemistry   | `426d220e-0020-4f6d-a523-72a8d389b5b0` |
| Physics     | `cd3e2279-3f0c-4737-9209-ddf4d2547854` |
| Mathematics | `3a90ec58-a85b-43a9-84d0-249452988545` |

---

## Paper Code Convention

Paper codes follow the Cambridge naming scheme:

```
<syllabus>_<session><year>_qp_<variant>
```

| Example            | Syllabus | Session | Year | Variant |
|--------------------|----------|---------|------|---------|
| `9701_w25_qp_11`   | Chem A-Level | O/N (Oct/Nov) | 2025 | 11 |
| `9700_s24_qp_12`   | Bio A-Level  | M/J (May/Jun) | 2024 | 12 |
| `0610_m25_qp_11`   | IGCSE Bio    | M/J           | 2025 | 11 |

The script auto-detects **year**, **session**, and **variant** from the paper code. IGCSE vs A-Level is inferred from the syllabus code prefix, but can be overridden with `--grade`.

---

## Running the Import

### 1. Activate the virtual environment and load env vars

```bash
cd /Users/mukit_10ms/Documents/GitHub/Edmate
source .venv/bin/activate
export $(grep -v '^#' content_gen/.env | xargs)
```

### 2. Run the importer

```bash
python3 content_gen/scripts/processing/import_to_db.py \
  <path_to_extracted_json> \
  --paper-code <paper_code> \
  --subject <Biology|Chemistry|Physics> \
  --grade <A-Level|IGCSE> \
  [--difficulty <Easy|Medium|Hard>] \
  [--topic-id <uuid>] \
  [--subtopic-id <uuid>] \
  [--cdn-mapping <path_to_cdn_mapping.json>]
```

### Example: A-Level Chemistry past paper

```bash
python3 content_gen/scripts/processing/import_to_db.py \
  content_gen/data/extracted/9701_w25_qp_11_extracted.json \
  --paper-code 9701_w25_qp_11 \
  --subject Chemistry \
  --grade A-Level \
  --difficulty Medium
```

### Example: IGCSE Biology with CDN image mapping

```bash
python3 content_gen/scripts/processing/import_to_db.py \
  content_gen/data/extracted/0610_m25_qp_11_extracted.json \
  --paper-code 0610_m25_qp_11 \
  --subject Biology \
  --grade IGCSE \
  --cdn-mapping content_gen/data/extracted/0610_m25_qp_11_cdn.json
```

---

## CLI Reference

| Argument        | Required | Description                                                    |
|-----------------|----------|----------------------------------------------------------------|
| `json_path`     | ✅        | Path to the extracted JSON file                                |
| `--paper-code`  | ✅        | Paper code, e.g. `9701_w25_qp_11`                             |
| `--subject`     | ✅        | `Biology`, `Chemistry`, `Physics`, or `Mathematics`            |
| `--grade`       |           | `A-Level` (default) or `IGCSE`                                 |
| `--difficulty`  |           | `Easy`, `Medium` (default), or `Hard`                          |
| `--topic-id`    |           | Override topic UUID (auto-resolves to `unknown-topic` if blank)|
| `--subtopic-id` |           | Override subtopic UUID                                         |
| `--cdn-mapping` |           | Path to CDN mapping JSON (`{filename: cdn_url, ...}`)          |
| `--db-url`      |           | Override `DATABASE_URL` env var                                |

---

## Deduplication

The importer checks `question_identifier` (`<paper_code>/Q<n>`) before every insert. If a row with that identifier already exists in the target table, the question is **skipped** (not duplicated).

This makes re-runs of the same paper fully idempotent — safe to run multiple times.

```
✅ Done: 0 inserted, 42 skipped, 0 errors.   ← safe re-run output
```

---

## Extracted JSON Format

The extraction pipeline produces JSON files like:

```json
{
  "source": "content_gen/data/inputs/9701_w25_qp_11.pdf",
  "base_name": "9701_w25_qp_11",
  "questions": [
    {
      "question_number": 1,
      "page": 2,
      "question_text": "What is the electronic configuration for Al+?",
      "options": {
        "A": "1s²2s²2p⁶3s¹3p¹",
        "B": "1s²2s²2p⁶3s²",
        "C": "1s²2s²2p⁶3s²3p²",
        "D": "1s²2s²2p⁶3s²3p⁶3d⁷4s¹"
      },
      "stem_images": ["content_gen/data/extracted/images/.../q1_figure.png"],
      "option_images": {}
    }
  ]
}
```

| Field             | Description                                          |
|-------------------|------------------------------------------------------|
| `question_number` | 1-indexed question number within the paper           |
| `question_text`   | Raw extracted question stem text                     |
| `options`         | Dict `{A, B, C, D}` of option texts                 |
| `stem_images`     | List of image paths for figures in the question stem |
| `option_images`   | Dict of images per option (e.g. `{"A": [...]}`)      |

---

## Post-Import Steps (QC)

After import, questions land with:
- `is_verified = false`
- `correct_options = null`
- `option_explanations = null`
- `summary_explanation = null`
- `detailed_explanation = null`

These fields are populated by the **QC / content generation pipeline** (see `PROCESS_GUIDE.md` and `AGENTIC_WORKFLOW.md`), which uses AI to generate explanations and mark answers, then sets `is_verified = true`.

---

## Flashcards Table

Flashcards are stored in the shared `flashcards` table (13,810+ rows as of March 2026):

| Column       | Type      | Notes                          |
|--------------|-----------|--------------------------------|
| `id`         | text      | UUID                           |
| `subjectId`  | text      | FK → `subjects.id`             |
| `topicId`    | text      | FK → `topics.id`               |
| `subtopicId` | text      | FK → `subtopics.id`            |
| `frontText`  | text      | Flashcard front (question)     |
| `backText`   | text      | Flashcard back (answer)        |
| `isActive`   | boolean   |                                |
| `createdAt`  | timestamp |                                |

To insert flashcards programmatically:

```python
from scripts.processing.import_to_db import DatabaseImporter

with DatabaseImporter(db_url) as importer:
    importer.insert_flashcards(
        subject_id="426d220e-...",
        topic_id="f648c2fa-...",
        subtopic_id="...",
        flashcards=[
            {"front_text": "What is the charge of an electron?", "back_text": "-1"},
        ]
    )
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `Connection timeout` | Not on office network | Connect to office Wi-Fi / VPN |
| `Unknown subject` | Typo in `--subject` | Use exact spelling: `Biology`, `Chemistry`, `Physics` |
| `No table mapping` | Wrong grade for syllabus | Pass `--grade IGCSE` or `--grade A-Level` explicitly |
| Questions skipped unexpectedly | Already imported | Normal — deduplication by `question_identifier` |
| `question_identifier already exists` in errors | Duplicate in same run | Check whether the JSON has duplicate `question_number` values |
