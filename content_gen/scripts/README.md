# Content generation scripts

This directory contains the **PDF → structured questions → explanations** pipeline used by Edmate.

## Layout (actual tree)

| Path | Role |
|------|------|
| `extraction/` | `pdf_extract_kit_wrapper.py` — adapter around [PDF-Extract-Kit](https://github.com/opendatalab/PDF-Extract-Kit) (must be cloned to `content_gen/tools/PDF-Extract-Kit`; see repo `scripts/setup_pdf_extract_kit.sh`). |
| `adapters/` (package root `content_gen/adapters/`) | `PyMuPDFAdapter`, `KitExtractionAdapter`, `VisionExtractionAdapter` — selected by `extraction_settings.engine` in `edmate_config.yaml`. |
| `pipeline/` | `pipeline_orchestrator.py` — main CLI orchestrator; `national_exam_processor.py` — optional standalone path with `--extraction-engine`. |
| `processing/` | `content_generator.py`, import/upload helpers. |
| `prompts.py` | Shared prompt templates (use `[Curriculum]` / `[Subject]` placeholders). |

## Quick start

1. Install deps: `pip install -r content_gen/requirements.txt`
2. Configure keys: `content_gen/.env` from `.env.example`
3. Configure routing: `edmate_config.yaml` (see `edmate_config.yaml.example` in repo root — **plain YAML**, no `!!python/object` tags)
4. If using **`pdf_extract_kit`**: run `./scripts/setup_pdf_extract_kit.sh` from the repo root, then install kit deps per upstream docs.

## CLI orchestrator

```bash
python3 content_gen/scripts/pipeline/pipeline_orchestrator.py \
  --input-dir content_gen/data/inputs \
  --output-dir content_gen/data/extracted \
  --single-pdf path/to/file.pdf
```

`--subject` is optional (defaults to `workspace.default_subject` in `edmate_config.yaml`).  
`--storage-provider` is **deprecated** and ignored (kept only for backward-compatible argument parsing).

## National exam processor (optional)

```bash
python3 content_gen/scripts/pipeline/national_exam_processor.py --pdf path/to/file.pdf --curriculum "General"
```

Use `--extraction-engine legacy` for text + regex only; omit the flag to follow `edmate_config.yaml` (`vision`, `pdf_extract_kit`, `pymupdf`, etc.).

## Import to Postgres

See `content_gen/scripts/processing/import_to_db.py`. Use `--target-table` to force a table id, or define `workspace.target_tables` in `edmate_config.yaml` so the importer picks the first configured table.
