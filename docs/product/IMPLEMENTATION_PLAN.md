# Implementation Plan: Edmate Lab_QA Service Readiness

This plan outlines the steps required to transform the current codebase into a production-ready **"Headless AI Service"** that can immediately serve external platforms.

---

## 1. Goal: Immediate Service Readiness
The objective is to allow an external platform to send a document and curriculum type via API and receive a validated JSON response following the `EDMATE_JSON_SCHEMA v1.0.0`.

---

## 2. Technical Milestones

### A. API Gateway & Orchestration
- [x] **Standardize FastAPI Endpoints:**
    - [x] `POST /api/v1/extract`: Accept file + metadata (curriculum, subject).
    - [x] `GET /api/v1/jobs/{job_id}`: Poll for status and retrieve final JSON.
- [x] **BYOK (Bring Your Own Key) Support:** 
    - [x] Implement middleware to extract provider-agnostic `X-API-Key` (with legacy compatibility for provider-specific headers) and pass it to the `LiteLLM` adapter dynamically.

### B. Schema Enforcement (Pydantic Models)
- [x] **Data Validation:** Create a robust Pydantic model for `EDMATE_JSON_SCHEMA`.
- [ ] **Correction Layer:** If an LLM returns slightly malformed JSON, implement a "repair" function to force it into the schema before returning it to the external platform.

### C. Pipeline Optimization
- [x] **Headless Execution:** Ensure the `pipeline_orchestrator.py` can run without the `qc_viewer` UI, outputting raw structured data directly to the API caller.
- [ ] **Modular Prompt Injection:** Allow external platforms to send their own `base_prompt` or select from our pre-defined library (Cambridge, NCTB, etc.).

---

## 3. GitHub Readiness (Experimental Run)

To prepare the repository for external developers:
1.  **API Documentation:** Auto-generate Swagger/OpenAPI docs at `/docs` (Available at `/docs` when server runs).
2.  **Environment Setup:** Add a `fastapi.dockerfile` for easy deployment.
3.  **Client Examples:** [x] Added `examples/client_request.py`.
4.  **Mock Mode:** Implement a `--mock` flag that returns standard valid JSON without calling expensive AI APIs.

---

## 4. Immediate Execution Steps

1.  **Refactor `qc_viewer/main.py`** to include the `/api/v1/process` endpoint.
2.  **Expose `content_gen` logic** as an importable service module.
3.  **Update `edmate_config.yaml`** to support "Service Mode" (disabling local file writing if desired).

---

## 5. Success Metrics for the Experimental Run
- **Zero-Error Schema:** 100% of API responses must pass the JSON Schema validation.
- **Latency:** Under 30 seconds for a full 5-question extraction & explanation cycle.
- **Isolation:** Verify that Platform A's API key is never used for Platform B's request.
