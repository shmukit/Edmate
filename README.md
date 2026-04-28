<p align="center">
  <img src="docs/brand/assets/banner.png" alt="Edmate Banner" width="100%">
</p>

<p align="center">
  <b>The Modular Automation Engine for Academic Assessments, Powered by Learning Science.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/github/license/shmukit/edmate?style=flat-square&color=fbbf24" alt="License">
  <img src="https://img.shields.io/github/issues/shmukit/edmate?style=flat-square&color=fbbf24" alt="Issues">
  <img src="https://img.shields.io/github/stars/shmukit/edmate?style=flat-square&color=fbbf24" alt="Stars">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square&color=1e1b4b" alt="Python">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square&color=fbbf24" alt="PRs Welcome">
</p>

---

Edmate Lab_QA is a **headless, open-source service platform** designed to transform unstructured educational materials (**PDF, Excel, Docx**) into high-fidelity, curriculum-aligned **Q&A, explanations, and 3D flashcards**.

Built on a "Plug & Play" architecture, it empowers teachers, publishers, and developers to serve external platforms using their own AI logic and API keys.

---

## 🔍 Project Scope & Boundaries

Edmate is a **Content Factory Infrastructure**. Its mission ends where the learner's experience begins.

- **✅ IN-SCOPE**: Source ingestion, AI generation (Q&A/Explanations), human-in-the-loop review, and DB/File persistence.
- **❌ OUT-OF-SCOPE**: Learner test-taking UI, live grading, student progress tracking, or proctoring.

---

## ✨ Key Features

- 🛡️ **Economic Kill-Switch**: Real-time token tracking with automatic pipeline halts when daily USD budgets are reached.
- 🧩 **Intelligence-Blind & BYOK**: LLM-agnostic routing via LiteLLM. Support for 100+ providers. External platforms can **Bring Your Own Key (BYOK)** to dictate their own model selection and billing.
- 💾 **Adapter-Driven Persistence**: Swap between Postgres, Vector DBs, or JSON exports with zero changes to core logic.
- ⚡ **MCP Ready**: Plug Edmate directly into Agentic IDEs (Cursor/Windsurf) as a native tool for instant content generation.
- 📊 **Automation Hub**: A sleek, dark-mode dashboard for managing drafts, review workflows, and cost analytics.
- 🛡️ **High-Integrity (HIA) First**: Specialized engine for generating AI-resilient assessments (AI Critique, Isomorphic Variants, Viva Prompts) that combat AI cheating.

---

## 🚀 30-Second Quick Start

Get Edmate running locally in seconds.

```bash
# 1. Clone & Install
git clone https://github.com/shmukit/Edmate.git
cd Edmate
pip install -r content_gen/requirements.txt

# 2. Configure (Set your keys)
cp content_gen/.env.example content_gen/.env
```

### ⚠️ Note on PDFs and Git
> By default, large PDF files are ignored by git (`.gitignore` excludes `*.pdf` except for `sample.pdf`) to prevent repository bloat. Please keep your heavy exam papers local to your machine!

### Option A: Use the Visual Automation Hub (UI)
Start the FastAPI backend to access the drag-and-drop dashboard:
```bash
uvicorn qc_viewer.main:app --host 0.0.0.0 --port 8000
```
Navigate to `http://localhost:8000/automate` in your browser.

### Option B: Use the CLI Orchestrator (Headless)
Process a PDF headlessly via terminal:
```bash
python3 content_gen/scripts/pipeline/pipeline_orchestrator.py --single-pdf path/to/your_paper.pdf
```

---

## 🔌 API Integration & BYOK

If you are a developer looking to integrate Edmate directly into your own platform using our **Bring Your Own Key (BYOK)** architecture, you can interact with the API directly.

1. **Start the API Server**: `uvicorn qc_viewer.main:app --host 0.0.0.0 --port 8000`
2. **Interactive API Docs**: Navigate to `http://localhost:8000/docs` to view the auto-generated Swagger UI which interactively documents all available endpoints.
3. **Python Example**: Check out the fully runnable Python example at [`examples/client_request.py`](examples/client_request.py). It demonstrates how to hit the `/api/v1/extract` endpoint, pass your LLM API keys via HTTP headers, and poll the job status until completion.

---

## 🏗️ Modular Architecture

Edmate is built for extreme extensibility. It uses the **Adapter Pattern** to remain decoupled across all layers of the platform, from data ingestion to database schemas.

```mermaid
graph TD
    %% 1. Ingestion
    subgraph Input ["1. Multi-Modal Ingestion"]
        A[PDF / Docx / Excel]
        M[Modality Extractor: Text, Image, Table]
        A --> M
    end

    %% 2. Intelligence
    subgraph Intelligence ["2. Intelligence & Pedagogy"]
        C[Curriculum Config: GCSE, National, Custom]
        P[Pedagogy Rules: Learning Science, HIA]
        R{LLM Router: BYOK}
        
        M --> C
        C --> P
        P --> R
        
        R -.->|Provider A| E[Extraction Agent]
        R -.->|Provider B| E
        R -.->|Self-Hosted/Local| E
    end

    %% 3. Output
    subgraph Output ["3. Output Generation"]
        O1[Simple Output: Q&A, Diagrams, Tables]
        O2[Enriched Output: Explanations, Flashcards, Concept Gaps]
        
        E --> O1
        E --> O2
        
        O1 --> S[Standardized Edmate JSON Schema]
        O2 --> S
    end

    %% 4. Storage
    subgraph Persistence ["4. Persistence Layer"]
        SA{Storage Adapters}
        S --> SA
        SA -->|Relational| DB1[(Postgres)]
        SA -->|Semantic| DB2[(Vector DB)]
        SA -->|Headless| DB3[JSON Export]
    end

    style R fill:#fbbf24,stroke:#111827,color:#111827
    style SA fill:#1e1b4b,stroke:#fbbf24,color:#fff
```

### 🧩 Dimensions of Modularity
1. **Multi-Modal Ingestion (Input):** Accepts Unstructured PDFs, Docx, and Excel/CSV files.
2. **Modality Extraction:** Intelligently separates and processes Text, Tables, and Images/Diagrams independently.
3. **Pedagogical Engine:** Applies Learning Science techniques (like our HIA engine) dynamically during the extraction stage.
4. **Curriculum Agnostic:** Plug and play your specific curriculum format (e.g., GCSE A/O level, or any National Curriculum).
5. **Model Router (BYOK):** Bring Your Own Key. Route tasks to any LLM of your choice (OpenAI, Gemini, Anthropic, or Local models).
6. **Multi-Tier Output Generation:** Extracts simple raw content (Q/A, Diagrams, Tables as-is) alongside enriched metadata (rationales for right/wrong answers, concept gaps, and 3D flashcards).

---

## 📂 Repository Layout

- `content_gen/core/`: The "Brain"—Routing, Budgeting, and Schema logic.
- `content_gen/adapters/`: The "Connectors"—Postgres and Base storage interfaces.
- `qc_viewer/`: The "Heart"—FastAPI backend and Vanilla JS Automation Hub.
- `docs/`: Deep-dive documentation on system design and database schemas.

---

## 🏛️ Edmate "Open Core" Model

Edmate is committed to keeping its core engine free and open-source forever. We follow an **Open Core** model where the essential tools are free, while advanced institutional features are part of our Studio/Enterprise offerings.

| Feature | Community (Free) | Studio / Enterprise |
| :--- | :---: | :---: |
| **Core AI Pipeline** | ✅ | ✅ |
| **PDF/Excel Ingestion** | ✅ | ✅ |
| **Standard Assessment (MCQ/TF)** | ✅ | ✅ |
| **High-Integrity Assessments (HIA)** | ✅ (Basic) | ✅ (Advanced) |
| **Custom Prompts** | ✅ | ✅ |
| **Collaboration & Teams** | ❌ | ✅ |
| **Advanced Institutional Analytics** | ❌ | ✅ |
| **Managed Cloud Hosting** | ❌ | ✅ |
| **SSO & RBAC** | ❌ | ✅ |

---

## 🛡️ Why High-Integrity Assessments (HIA)?

In the era of Generative AI, traditional "recall-based" homework is becoming obsolete. Edmate's mission is to help teachers and platforms move toward **Authentic Assessment** — content designed to ensure students "lift the weights" of their own education.

Edmate's HIA engine generates:
*   **AI Critique Exercises**: Students must find errors in deliberately flawed AI answers.
*   **Isomorphic Variants**: Unique numerical/contextual versions of the same concept per student.
*   **Viva Defense Prompts**: Structured probing questions for verbal reasoning verification.
*   **Scaffolded Sequences**: Breaking single tasks into mandatory intellectual process steps.

---

---

## 🤝 Community & Contributing

We welcome contributions of all kinds! Whether it's a new Storage Adapter, an extraction prompt, or a bug fix.

- 🗺️ **[Product Roadmap](ROADMAP.md)**: Where we're going and how to help get there.
- 🎯 **[Use Cases](docs/product/USE_CASES.md)**: How different users (Platforms vs. Teachers) adopt Edmate.
- 📖 **[Contributing Guide](CONTRIBUTING.md)**: How to get started.
- 📜 **[Code of Conduct](CODE_OF_CONDUCT.md)**: Our community standards.
- 🏗️ **[Modular Architecture Guide](docs/contributing/CONTRIBUTING_MODULAR.md)**: Deep dive for developers.
- 🧠 **[Pedagogy & Learning Science](docs/pedagogy/PEDAGOGY.md)**: The "How It Works" behind our content generation.

---

## 📄 License
MIT License - Open Source

**Built with ❤️ for an accessible, AI-powered education system.**
