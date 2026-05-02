# Pipeline Settings: What Actually Changes Output

This page is the source of truth for which settings in the Automation Hub are currently wired to runtime behavior.

## End-to-end settings flow

```mermaid
flowchart LR
ui[SettingsUI] --> api[DraftAPI]
api --> runtime[PipelineRuntime]
runtime --> extraction[Extraction]
runtime --> generation[Generation]
generation --> draft[DraftOutput]
draft --> review[ReviewAndPublish]
```

## Effective settings (active today)

| UI Label | Transport | Runtime Consumer | Observable Effect |
| --- | --- | --- | --- |
| Curriculum | multipart form `curriculum` | `PedagogyEngine` + draft metadata | Changes curriculum context in generated pedagogy profile metadata. |
| Learning Science Profile | multipart form `ls_profile` | `PedagogyEngine` + draft metadata | Changes Bloom/retrieval/cognitive-load profile used for prompt composition. |
| HIA Resilience Target | multipart form `hia_mode` | `PedagogyEngine` + draft metadata | Changes HIA guidance intensity (Low/Medium/High/Very High). |
| Detection Mode | multipart form `question_detection_mode` | router extraction config | Alters question-number detection strictness in extraction. |
| Minimum Question Number | multipart form `min_question_number` | router extraction config | Filters out questions below threshold. |
| Maximum Question Number | multipart form `max_question_number` | router extraction config | Filters out questions above threshold. |
| API Key (BYOK) | header `X-API-Key` | LiteLLM auth env for request | Uses caller key for LLM billing/quota during the run. |
| BYOK Provider | header `X-LLM-Provider` | runtime model override resolver | Changes provider-family model defaults if model id not supplied. |
| BYOK Model ID | header `X-Model-ID` | runtime model override resolver | Forces explicit model for extraction/generation/validation. |
| Target Table (Injection) | review publish payload `table_name` | publish API / DB service | Changes publish destination table only (not extraction/generation). |

## Display-only or pending settings

| UI Label | Current State | Notes |
| --- | --- | --- |
| Routing Profile | Not wired | Currently a UX placeholder for future policy bundles (cost/quality presets). |
| Target Language | Not wired | Currently shown in UI only; output language control not yet enforced in runtime prompts. |

## API contract used by local UI

### Form fields (`POST /api/automate/draft`)
- `subject`
- `paper_code`
- `file`
- `curriculum`
- `ls_profile`
- `hia_mode`
- `question_detection_mode` (optional)
- `min_question_number` (optional)
- `max_question_number` (optional)

### Optional headers
- `X-API-Key`
- `X-LLM-Provider`
- `X-Model-ID`

## Defaults and fallback behavior

- If extraction guardrail overrides are omitted, defaults come from `edmate_config.yaml` (`extraction_settings` block).
- If `X-LLM-Provider` is omitted, runtime uses config-routed models.
- If `X-LLM-Provider` is provided and `X-Model-ID` is omitted, provider-family defaults are applied.
- If `X-Model-ID` is provided, it has highest precedence for all task types in the request.

## Draft export endpoint

Download a processed draft from disk **without** publishing to the database. Implemented in [`qc_viewer/services/draft_export.py`](../../qc_viewer/services/draft_export.py); HTTP route in [`qc_viewer/routers/automation.py`](../../qc_viewer/routers/automation.py).

### Route

`GET /api/automate/draft/{draft_id}/export?format={json|csv|md|markdown|mdzip|docx}`

Response: binary body with `Content-Disposition: attachment; filename="..."` and a format-specific `Content-Type`.

### Format summary

| `format` | File | Diagrams / images |
| --- | --- | --- |
| `json` | `.json` | Full metadata including `diagram_base64` data URIs unchanged. |
| `csv` | `.csv` | Full `diagram_data_uri` column per row (quoted). |
| `md`, `markdown` | `.md` | **No** inline base64; blockquote per question points to `mdzip`, JSON, or DOCX for images. |
| `mdzip` | `.zip` | `questions.md` with `![](images/Qn.png)` links; `images/` folder for PNG/JPEG only; `README.txt`. |
| `docx` | `.docx` | Embedded PNG/JPEG where decodable; otherwise a short note in the document. |

Non-PNG/JPEG data URIs (e.g. WebP) are not embedded in Word or the ZIP; the Markdown note or JSON/CSV still holds the original URI.

### Notes

- Works for any draft that has `qc_viewer/drafts/{draft_id}/metadata.json` (or legacy `{draft_id}.json`).
- No Postgres or `DATABASE_URL` required for export-only workflows.
