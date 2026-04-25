# Edmate Product Roadmap

> **Status**: Living Document · Last Updated: April 2026 · [Discuss on GitHub](https://github.com/shmukit/Edmate/discussions)

> [!NOTE]
> This roadmap communicates **intent, not iron-clad promises**. It is a community document — open for discussion, contribution, and revision. If you want to shape the direction of Edmate, open a GitHub Discussion or submit a Pull Request to this file.

---

## 🌟 Vision & Mission

### Mission
> **Make world-class educational content infrastructure open, free, and accessible for every teacher and EdTech platform on Earth.**

Today, a teacher with a brilliant curriculum — or a developer building the next great EdTech platform — cannot easily produce high-quality, research-backed assessment content at scale without expensive tools, editorial teams, or months of engineering. Edmate fixes that.

### The Northstar
Any teacher or platform developer, with **any curriculum** and **any AI key**, can transform raw educational material into a complete set of pedagogically-structured, machine-readable assessments in minutes — and publish them anywhere.

### What Edmate Is (and Is NOT)

| **Edmate IS** | **Edmate is NOT** |
|---|---|
| A headless content factory (API + CLI) | A finished student-facing app |
| LLM-agnostic (BYOK, 100+ providers) | Tied to any single AI vendor |
| Curriculum-agnostic by design | Only for Cambridge A/O-Level |
| Open-source, community-driven | A proprietary SaaS product |
| A platform for *teachers & platforms* | A replacement for teacher judgment |
| Open Core (Free engine + Studio tier) | Completely proprietary |

---

## 🏢 Open Core & Tiers

To ensure long-term sustainability while keeping the core engine free for the global teaching community, Edmate uses an **Open Core** model.

*   **[Community]**: Free and open-source forever. Essential tools for individual teachers and developers.
*   **[Studio/Enterprise]**: Advanced features for institutions, publishers, and high-scale platforms.

---

---

## 👩‍🏫 Who Is This For?

### Persona 1: The Content Creator (Teacher/Author)
A subject-matter expert who wants to turn their expertise and materials into structured, digital assessments without being a programmer. They use the **Automation Hub UI**.

### Persona 2: The Developer / EdTech Integrator
A developer building an EdTech platform (like Alopoth, Moodle, or a national LMS) who wants to plug in a battle-tested content generation engine. They use the **CLI or API**.

### Persona 3: The Open-Source Contributor
A developer who wants to add a new storage adapter, a new input format, a new assessment type, or a learning science feature. They use the **CONTRIBUTING.md** guide.

---

## 📍 Current Status — v0.x (The Foundation)

The core pipeline is working. You can clone this repo, configure your keys, and process a PDF today.

| Capability | Status |
|---|---|
| PDF Extraction (Text + Diagrams) | ✅ Working |
| MCQ Generation (Explanation + Flashcards) | ✅ Working |
| Automation Hub UI (Drafts, Review, Analytics) | ✅ Working |
| Multi-Provider LLM Support (via LiteLLM) | ✅ Working |
| PostgreSQL Storage Adapter | ✅ Working |
| Economic Kill-Switch (Budget Caps) | ✅ Working |
| MCP Server (Cursor/Windsurf integration) | ✅ Working |
| CI/CD Pipeline (GitHub Actions) | ✅ Working |

---

## 📚 Assessment Content Taxonomy

This is what Edmate can generate — and what the community will systematically build towards. Every item below is a potential contribution opportunity.

### 🟢 Tier 1: Closed-Response (Objective)
These are machine-gradable, high-throughput assessment formats.

| Type | Description | Learning Science Basis | Status |
|---|---|---|---|
| **MCQ (Multiple Choice)** | 4-option question with option-wise explanations | Retrieval Practice + Elaborative Interrogation | ✅ Done |
| **True / False** | Binary assertion with justification | Retrieval Practice | 🗺️ Planned |
| **Matching** | Connect items in two columns | Pattern Recognition | 🗺️ Planned |
| **Fill-in-the-Blank (Cloze)** | Sentence with key term removed | Retrieval Practice | 🗺️ Planned |
| **Drag & Drop Ordering** | Sequence steps or events correctly | Procedural Memory | 🗺️ Planned |

### 🟡 Tier 2: Open-Response (Subjective)
These require structured rubrics and AI scoring criteria.

| Type | Description | Learning Science Basis | Status |
|---|---|---|---|
| **Short Answer** | 1–3 sentence factual response (2–4 marks) | Retrieval + Elaboration | 🗺️ Planned |
| **Structured / Data-Response** | Multi-part question with graphs or tables | Cognitive Load Management | 🗺️ Planned |
| **Long Answer / Essay** | Extended response with mark scheme rubric | Higher-Order Bloom's (Analyze/Evaluate/Create) | 🔭 Exploratory |
| **Case Study** | Applied scenario with multi-sub-question | Transfer Learning | 🔭 Exploratory |
| **"Spot the Error"** | Student finds and corrects a mistake | Metacognition + Error Analysis | 🗺️ Planned |

### 🔵 Tier 3: Study Aids (Derived Assets)
These are generated *from* questions, not standalone formats.

| Type | Description | Learning Science Basis | Status |
|---|---|---|---|
| **Recall Flashcards** | Concept definition cards | Spaced Repetition (SM-2) | ✅ Done (basic) |
| **Problem-Solving Flashcards** | "How to approach X" cards | Procedural Practice | ✅ Done (basic) |
| **Concept Map Entry** | A node + connections for a topic concept | Elaborative Encoding | 🗺️ Planned |
| **Summary / Study Notes** | Condensed topic overview from questions | Interleaving Recap | 🗺️ Planned |
| **Glossary Entry** | Term + definition + example | Vocabulary Acquisition | 🗺️ Planned |
| **"Cheat Sheet" Generator** | 1-page summary of a topic's key formulas | Cognitive Load Offloading | 🔭 Exploratory |

### 🟣 Tier 4: Teacher & Platform Tooling (Diagnostic Layer)
These are **content types that platforms consume** to build diagnostic and adaptive features — Edmate generates the structured data, the platform decides how to present it.

| Type | Description | What the Platform Can Do With It | Status |
|---|---|---|---|
| **Bloom's Level Tag** | Every question tagged with cognitive level (Remember → Create) | Compose balanced assessments; enforce level coverage per topic | ✅ Schema Ready |
| **Misconception Profile** | Per-wrong-option misconception description + concept gap label | Feed adaptive quiz engines; highlight weak concepts per student | 🗺️ Planned |
| **Difficulty Metadata** | 3-tier difficulty label + justification text | Enable adaptive difficulty engines; build difficulty ladders | 🗺️ Planned |
| **Worked Example** | Step-by-step solution with scaffold levels | Display as hints, or as a separate scaffolded resource | 🗺️ Planned |
| **Self-Assessment Rubric** | Machine-readable rubric for essay/open-response questions | Power teacher-grading UIs and peer-review workflows | 🔭 Exploratory |
| **Interleaving Tags** | Cross-topic links in question metadata | Let platforms build mixed-topic quiz sets programmatically | 🗺️ Planned |

### 🔴 Tier 5: High-Integrity Assessments (HIA)
This is the **"AI-Resilient" category**. These formats are specifically designed to make AI-induced cheating difficult and to ensure students demonstrate genuine human understanding.

| Type | Description | AI Resilience Strategy | Status |
|---|---|---|---|
| **AI Critique Exercise** | Student identifies errors in a deliberately flawed AI answer | Critical Evaluation | 🗺️ Planned (H1) |
| **Isomorphic Variants** | Generate math/STEM questions with parametric variations | Randomization | 🗺️ Planned (H1) |
| **Scaffolded Sequence** | A concept broken into a mandatory step-by-step process | Process-over-Product | 🗺️ Planned (H2) |
| **Contextualizable Template** | Question frames with slots for local/personal context | Personalization | 🗺️ Planned (H2) |
| **Viva (Oral) Prompt Set** | Structured probing questions for verbal defense | Human Performance | 🗺️ Planned (H2) |
| **Metacognitive Reflection** | Prompts asking "how" the student arrived at an answer | Self-Reflection | 🗺️ Planned (H2) |
| **Integrity Analytics** | AI Resilience Score + Vulnerability tags for each item | Transparency | 🗺️ Planned (H1) |

---

## 🧠 Learning Science Framework

> [!IMPORTANT]
> **Edmate is a content factory, not a student app.** This framework defines how Edmate **encodes pedagogy into the content it produces** — the structured metadata, schema fields, and content structures that allow consuming platforms, LMS systems, and apps to implement learning science techniques *without re-inventing them*.

Think of it this way: Edmate is the layer that answers the question **"What does this content need to contain?"** so that the downstream app can answer **"When and how should the student see it?"**

---

### 🏷️ The Pedagogy Label: Learning Science by Default

**Core Design Decision: Default ON. Teacher-Tweakable.**

The most important design choice in Edmate's learning science system is this:

> Learning science techniques are **baked in by default**. Teachers and platforms do not need to opt in to good pedagogy — they get it automatically. They can, however, adjust the *profile* to fit their specific context.

This follows the **"nutrition label" model**:
- The food is already nutritious — you don’t choose the vitamins
- But the label tells you exactly what’s in it
- And you can request a specific diet (e.g., high-protein, low-sodium)

Every output Edmate generates includes a `learning_science_applied` block that acts as a **pedagogy label** — declaring exactly which techniques were used to produce the content:

```json
{
  "learning_science_applied": {
    "profile": "default",
    "techniques": [
      {
        "name": "Bloom's Taxonomy",
        "level": "Apply",
        "description": "Question requires applying a concept to a new context"
      },
      {
        "name": "Elaborative Interrogation",
        "description": "All 4 options include 'why is this wrong' explanations with concept gaps"
      },
      {
        "name": "Cognitive Load Layering",
        "description": "Explanation structured in 3 layers: Core Concept, Step-by-Step, Final Answer"
      },
      {
        "name": "Spaced Repetition (SM-2)",
        "description": "Flashcards include SM-2 scheduling metadata (ease_factor, interval)"
      }
    ],
    "schema_version": "1.1.0"
  }
}
```

This label:
- **Builds trust**: Teachers can audit that content was generated with rigorous pedagogy
- **Is a differentiator**: No other AI content tool declares its pedagogical provenance
- **Enables compliance**: Institutions can verify content meets pedagogical standards

#### Learning Science Profiles (in `edmate_config.yaml`)

Teachers and platforms configure their profile once. All content generation inherits it:

```yaml
# edmate_config.yaml
learning_science:
  profile: "default"  # "default" | "exam_prep" | "beginner" | "custom"

  # All techniques are ON by default
  bloom_taxonomy:
    enabled: true
    target_levels: ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]

  spaced_repetition:
    enabled: true       # Adds SM-2 metadata to all flashcards
    algorithm: "sm2"    # "sm2" | "anki" | "custom"

  elaborative_interrogation:
    enabled: true       # Option-wise explanations + concept_gap for every wrong option

  cognitive_load:
    enabled: true
    explanation_depth: "full"  # "full" | "core_only" | "steps_only"

  retrieval_practice:
    enabled: true
    generate_variants: true    # Generate MCQ + True/False + Cloze for the same concept

  interleaving:
    enabled: true              # Add concept_links and interleaving_tags to metadata

  formative_summative_tagging:
    enabled: true
    default_role: "formative"  # "formative" | "summative" | "practice"

  assessment_role_tagging:
    enabled: true
```

#### Preset Profiles

| Profile | Who it’s for | Key differences from default |
|---|---|---|
| `default` | General teacher / platform | All techniques ON, all Bloom’s levels, full explanations |
| `exam_prep` | Exam-focused platforms | Summative role, higher Bloom’s levels (Apply–Evaluate), difficulty = Hard |
| `beginner` | Foundation courses / young learners | Bloom’s L1-L2 only, explanation_depth = core_only, scaffold_level = Foundation |
| `flashcard_only` | Platforms with their own quiz engine | Disables question generation, outputs flashcards + glossary only |
| `custom` | Full control | Every flag configurable individually |

---

### Principle 1: Retrieval Practice
> *Generating content designed to be actively recalled, not passively re-read.*

**What Edmate produces**: Multiple low-stakes question variants (MCQ, True/False, Cloze, Short Answer) from the same source material. Each is tagged `"retrieval_mode": "low_stakes"` or `"summative"`, so the consuming platform can choose when and how to surface them.

**Schema output**: `content.retrieval_mode`, `content.question_variant_group_id` (groups variants of the same concept for platforms to manage)

**Config key**: `learning_science.retrieval_practice.enabled`

---

### Principle 2: Spaced Repetition
> *Content metadata that enables scheduling — not the scheduling itself.*

**What Edmate produces**: Flashcards with SM-2 algorithm fields pre-populated (`ease_factor: 2.5`, `interval: 1`, `next_review_date: null`). Anki export (`.apkg`) carries this data natively. The platform or teacher's tool runs the scheduling; Edmate provides the card.

**Schema output**: `flashcard_bridge[].ease_factor`, `flashcard_bridge[].interval`, `flashcard_bridge[].next_review_date`

**Config key**: `learning_science.spaced_repetition.enabled`

---

### Principle 3: Interleaving
> *Tagging content with enough metadata for platforms to mix topics programmatically.*

**What Edmate produces**: Every question is tagged with `topic`, `subtopic`, and `concept_links[]` (related topics this question touches). A platform can use these tags to compose interleaved quiz sets without any additional work.

**Schema output**: `metadata.topic`, `metadata.subtopic`, `metadata.concept_links[]`, `metadata.interleaving_tags[]`

**Config key**: `learning_science.interleaving.enabled`

---

### Principle 4: Bloom's Taxonomy
> *Every question is labelled with the cognitive level it targets.*

**What Edmate produces**: Every generated question is tagged with a validated Bloom's level (`Remember`, `Understand`, `Apply`, `Analyze`, `Evaluate`, `Create`). A platform or teacher can filter by level to build assessments that target the right cognitive depth — and verify they have full coverage across a topic.

**Schema output**: `content.explanations.bloom_taxonomy` — already in schema v1.1.0. Roadmap: **Bloom's Enforcer** validates LLM output matches the declared level.

**Config key**: `learning_science.bloom_taxonomy.enabled`, `learning_science.bloom_taxonomy.target_levels[]`

---

### Principle 5: Elaborative Interrogation
> *Every distractor (wrong option) comes with a "why is this wrong" explanation.*

**What Edmate produces**: Option-wise explanations for all wrong answers — not just the correct one. Each includes a `concept_gap` label identifying the specific misconception. Platforms can use this to build "here’s what you misunderstood" feedback without any extra AI calls.

**Schema output**: `content.options[].explanation`, `content.options[].concept_gap`, `content.options[].is_correct`

**Config key**: `learning_science.elaborative_interrogation.enabled`

---

### Principle 6: Cognitive Load Theory
> *Producing content in layers — not as one monolithic block.*

**What Edmate produces**: Explanations are structured into three layers — `core_concept` (one sentence), `detailed_logic` (step-by-step), and `final_answer_display` (verdict). Worked examples are generated as a separate content type. Difficulty metadata allows platforms to select the right scaffold level for the learner.

**Schema output**: `content.explanations.core_concept`, `content.explanations.detailed_logic`, `content.explanations.final_answer_display`, `metadata.difficulty`, `metadata.scaffold_level`

**Config key**: `learning_science.cognitive_load.enabled`, `learning_science.cognitive_load.explanation_depth`

---

### Principle 7: Formative vs. Summative Assessment Design
> *Content is tagged by its pedagogical role, not just its format.*

**What Edmate produces**: Each generated item is tagged with its intended use — `formative` (practice, feedback-oriented) or `summative` (evaluation-oriented). Teachers and platforms can use this to build appropriate assessment experiences without manual curation.

**Schema output**: `metadata.assessment_role: enum["formative", "summative", "diagnostic", "practice"]`

**Config key**: `learning_science.formative_summative_tagging.enabled`, `learning_science.formative_summative_tagging.default_role`

---

## 🛣️ Development Roadmap

### Horizon 1: Foundation *(Now → 6 Months)*
> **Goal**: Make Edmate production-ready, contributor-friendly, and trusted by teachers.

These items are **concrete and actionable**. They are good starting points for new contributors.

#### 🔒 Security Hardening
- [ ] Enable **GitHub Secret Scanning** on the repository
- [ ] Add a `.env.example` with all required keys documented
- [ ] Add a `SECURITY.md` with responsible disclosure policy
- [ ] Audit and harden `.gitignore` — ensure no credentials, no `data/inputs/` PDFs
- [ ] Implement **input sanitization** for uploaded PDF filenames (path traversal prevention)
- [ ] Document the BYOK threat model: what data leaves the user's machine and when

#### ⚡ Pipeline Efficiency
- [ ] **Response Caching**: Cache LLM API responses keyed by `(paper_code, question_number, prompt_hash)` — avoid redundant re-generation
- [ ] **Async Batch Processing**: Replace sequential API calls with `asyncio.gather()` for 10x throughput
- [ ] **`--resume` flag**: Skip already-processed PDFs on re-run (idempotent pipeline)
- [ ] **Rate Limiter**: Token-bucket rate limiter per provider to avoid API quota errors
- [ ] **Structured Logging**: Replace `print()` with `logging` module; write per-run `summary.json`

#### 🧠 Learning Science Profile System
- [ ] **`learning_science_applied` block**: Every generated JSON output includes the pedagogy label declaring which techniques and config were applied
- [ ] **Profile loader in `edmate_config.yaml`**: Read `learning_science.profile` and apply preset configurations (`default`, `exam_prep`, `beginner`, `flashcard_only`, `custom`)
- [ ] **Config validation**: Validate the `learning_science` config block on startup with clear error messages for invalid combinations
- [ ] **SM-2 metadata in all flashcards**: `ease_factor`, `interval`, `next_review_date` fields populated by default
- [ ] **Assessment role tagging**: Every output tagged with `metadata.assessment_role` based on config

#### 🧠 High-Integrity Assessment (HIA) Foundation
- [ ] **AI Resilience Scoring Engine**: Implement the logic to tag every question with a Resilience Score (Low/Med/High) and vulnerability notes
- [ ] **AI Critique Exercise Generator**: Prompt template for generating "deliberately flawed" answers + error keys
- [ ] **Isomorphic Variant Engine (v1)**: Extract numerical parameters from STEM questions and generate 3 variants
- [ ] **Integrity Metadata in Schema**: Add `ai_resilience_metadata` block to all JSON outputs

#### 📦 Modularity (Input)
- [ ] **Excel/CSV Ingestion Adapter**: Teachers upload question banks in spreadsheet format
- [ ] **Docx Ingestion Adapter**: Microsoft Word document support

#### 📦 Modularity (Output)
- [ ] **Anki Export (`.apkg`)**: Direct export to Anki deck format with SM-2 scheduling
- [ ] **Markdown Export**: Clean, portable markdown of all generated content
- [ ] **JSON Schema Validation**: Enforce `v1.1.0` schema on all outputs with `pydantic` models

#### 🧪 Testing
- [ ] Increase test coverage to > 70% for all core modules
- [ ] Add integration test with a sample 5-question PDF fixture
- [ ] Add schema validation tests for JSON output
- [ ] Add tests that verify `learning_science_applied` block is present and accurate in all outputs

---

### Horizon 2: Intelligence *(6–12 Months)*
> **Goal**: Make Edmate *smarter* about content quality and *cheaper* to run.

These items require more architectural discussion. They are flagged **`🏗️ Discussion Needed`** on the GitHub board.

#### 🔒 Security (Advanced)
- [ ] **MCP Server Auth**: Add Bearer token authentication to the MCP server endpoints
- [ ] **BYOK Key Isolation**: Ensure each user's API key is scoped to their session only; never logged
- [ ] **PDF Sandbox**: Run PDF extraction in a sandboxed subprocess to prevent malicious PDF attacks

#### 🧠 Inference Efficiency
- [ ] **Model Tiering**: Route cheap/fast models (GPT-4o-mini, Haiku) to formatting; strong models to reasoning
- [ ] **Prompt Compression**: Compress repeated context (syllabus preamble) using techniques like LLMLingua
- [ ] **Streaming Output**: Support streaming API responses in the Automation Hub for faster perceived feedback
- [ ] **Prompt Versioning**: Version-control all prompts in `prompts.py` with semantic versions (`v2.1.0`)
- [ ] **LLM-as-Judge (QC)**: Implement automated quality control — a second LLM scores generated content against the QC rubric; flag scores < 8/10 for human review

#### 📚 Assessment Content
- [ ] **"Spot the Error"** question type: AI generates a worked solution with a deliberate error
- [ ] **Structured / Data-Response**: Multi-part question with sub-questions (a), (b), (c)
- [ ] **Bloom's Level Enforcer**: Validate and label each generated question's Bloom's level
- [ ] **Concept Map Generator**: Output a node-edge JSON for concept map visualization
- [ ] **Cross-Topic Quiz Mode**: Generate interleaved question sets from a topic library
- [ ] **Difficulty Ladder**: Generate the same concept at 3 scaffold levels (Easy/Medium/Hard)

#### 📦 Modularity (Input)
- [ ] **YouTube Transcript Adapter**: Extract content from video transcripts (teachers record lectures)
- [ ] **Web Page Adapter**: Scrape and chunk a textbook URL for content generation

#### 📦 Modularity (Output)
- [ ] **QTI Export**: IMS Question and Test Interoperability format for LMS compatibility
- [ ] **SCORM Package**: Deployable package for Moodle, Canvas, and corporate LMS platforms
- [ ] **Google Classroom API Export**: Direct push to a teacher's Google Classroom

---

### Horizon 3: Ecosystem *(12–24 Months)*
> **Goal**: Edmate becomes the *infrastructure layer* for global education platforms.

These are visionary items. They are open for community input and may evolve significantly.

#### 🔒 Security (Enterprise-Grade)
- [ ] **[Studio] SOC2-style checklist** for institutional users: documented controls for data handling
- [ ] **[Studio] RBAC (Role-Based Access Control)** for team/studio instances
- [ ] **[Studio] Audit logs**: Full traceability of who generated what and when

#### 🤝 Ecosystem
- [ ] **[Community] Prompt Marketplace**: A community-curated library of subject/curriculum-specific prompt templates
- [ ] **[Community] Plugin SDK**: A formal Python SDK for building input adapters and output exporters
- [ ] **[Community] "Curriculum Packs"**: Pre-configured bundles (syllabus prompts + schema mappings) for NCTB, CIE, Edexcel, CBSE, etc.

#### 🌍 Intelligence (Long-Term)
- [ ] **[Studio] Difficulty Calibration API**: Accept aggregated performance data from platforms (not individual students) and suggest difficulty label corrections for Edmate-generated content
- [ ] **[Community] Misconception Knowledge Graph**: A community-maintained, open graph of common misconceptions per topic/curriculum
- [ ] **[Community] Self-Hosted Inference (Ollama)**: Full offline operation with local LLMs — no data leaves the institution
- [ ] **[Community] Content Quality Benchmark**: Public dataset of human-rated Edmate output

#### 📱 Access & Scale
- [ ] **[Studio] Managed SaaS Tier**: Hosted version with included AI tokens for non-technical teachers
- [ ] **[Studio] Mobile Companion App**: Review and approve generated content on-the-go
- [ ] **[Studio] Institutional API**: High-throughput, authenticated API for platforms with 1M+ students

---

## 🏛️ Technical Pillars

### 🔒 Security Philosophy
Edmate is a BYOK platform. This means the user's API keys are the highest-value asset. Our commitment:

1. **Keys never leave `.env`** — no key logging, no key transmission to any Edmate infrastructure
2. **Secrets are never committed** — enforced by `.gitignore` + GitHub Secret Scanning
3. **PDF inputs are untrusted** — all filenames sanitized; future sandboxed processing
4. **Transparency** — every network call the pipeline makes is documented

### ⚡ Pipeline Efficiency Philosophy
> "Don't call the model if you already have the answer."

1. **Cache first** — every LLM response is cached by content hash
2. **Async always** — no blocking sequential API calls in batch mode
3. **Fail gracefully** — retry with exponential backoff; partial failures don't kill the run
4. **Measure everything** — `session_metrics.json` tracks every token and cent

### 🧠 Inference Efficiency Philosophy
> "Use the cheapest model that achieves the required quality level."

| Task | Recommended Tier | Rationale |
|---|---|---|
| PDF text structuring | Fast (GPT-4o-mini) | Low reasoning needed |
| MCQ explanation generation | Mid (Claude Haiku) | Moderate reasoning |
| LLM-as-Judge QC | Strong (GPT-4o / Claude Opus) | High reasoning required |
| Worked example generation | Strong | Multi-step logical chains |
| LaTeX → Unicode formatting | Fast | Simple transformation |

### 🧩 Modularity Philosophy
> "Every stage of the pipeline is a hotswappable plugin."

| Stage | Current | Target |
|---|---|---|
| **Input** | PDF | PDF, Excel, Docx, YouTube, Web |
| **Extraction** | PyMuPDF, PDF-Extract-Kit | + LaTeX-OCR, Table Parser |
| **Inference** | LiteLLM (100+ providers) | + Self-hosted (Ollama) |
| **Output** | JSON, Postgres | + Anki, Markdown, QTI, SCORM, Google Classroom |

---

## 🤝 How to Contribute to the Roadmap

### As a Teacher or Educator
- 📣 Open a **GitHub Discussion** describing an assessment format or learning science technique you need
- ⭐ Upvote existing feature requests to signal community priority

### As a Developer
- 🏗️ Pick any unchecked item in **Horizon 1** — these are all "good first contributions"
- 💬 For **Horizon 2** items, comment on the related GitHub Issue to discuss approach before coding
- 📖 Read [CONTRIBUTING.md](../CONTRIBUTING.md) before submitting a PR

### As a Researcher / Learning Scientist
- 📝 Open a PR to update the **Learning Science Framework** section with newer evidence or techniques
- 🔬 Review our prompt templates in `content_gen/scripts/prompts.py` and suggest improvements

### Tagging Convention
When opening issues related to the roadmap, use these labels:

| Label | Meaning |
|---|---|
| `roadmap:h1` | Horizon 1 — Foundation |
| `roadmap:h2` | Horizon 2 — Intelligence |
| `roadmap:h3` | Horizon 3 — Ecosystem |
| `good first issue` | Great for new contributors |
| `learning-science` | Relates to pedagogical framework |
| `help wanted` | Core team is seeking contributions |

---

## 🔗 Related Documents

| Document | Purpose |
|---|---|
| [SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) | Technical architecture deep-dive |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute code |
| [EDMATE_JSON_SCHEMA.md](docs/EDMATE_JSON_SCHEMA.md) | The standard output schema |
| [PEDAGOGY.md](docs/PEDAGOGY.md) | Deep dive into learning science & HIA |
| [SKILLS_CATALOG.md](content_gen/docs/SKILLS_CATALOG.md) | Discrete pipeline skill definitions |
| [QC_RUBRIC.md](content_gen/docs/QC_RUBRIC.md) | Content quality standards |

---

*This roadmap is maintained by the Edmate core team and community. To propose changes, open a Pull Request targeting this file.*
