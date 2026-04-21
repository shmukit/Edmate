# Edmate 🎓

**The Modular AI Factory for Educational Content Generation**

Edmate is an open-source, vendor-agnostic pipeline designed to transform unstructured educational materials (PDFs, images, documents) into high-fidelity learning modules, flashcards, and MCQ banks. 

Built with **modularity** and **multi-modality** at its core, Edmate allows organizations to bring their own intelligence (LLMs), their own storage (S3/R2), and their own database schemas.

---

## 🏗️ Modular Architecture

Edmate is designed to be "Intelligence-Blind" and "Database-Agnostic," adhering to the **Adapter Pattern**.

### 1. Intelligence Layer (LLM Agnostic)
Powered by **LiteLLM**, Edmate supports 100+ model providers (OpenAI, Gemini, Anthropic, Ollama, etc.). Users can route specific tasks to different models via the `ModelRoutingEngine` to optimize for cost and capability:
- **Extraction:** Recommended model `gemini-1.5-pro` for massive multimodal context.
- **Generation:** Recommended model `claude-3-haiku` or `gpt-4o-mini` for speed.
- **Verification:** Recommended model `gpt-4o` for high-reasoning logic.

### 2. Persistence Layer (BYO-Database)
Edmate produces standardized Pydantic models. Use **Storage Adapters** to map this data to any schema:
- **PostgresStorageAdapter:** Ready-to-use adapter for PostgreSQL.
- **BaseStorageAdapter:** Extend this to support MySQL, MongoDB, or Vector DBs.

### 3. Execution Interfaces
- **Automation Hub (UI):** A user-friendly dashboard for non-coders to manage drafts, observe real-time cost analytics, and configure model profiles.
- **CLI Orchestrator:** For batch processing from the terminal.
- **MCP Server:** Plug Edmate directly into Agentic IDEs (Cursor/Windsurf) as a native tool.

---

## 🛡️ Economic Safeties (AI Budgeting)
Edmate includes an automatic **Economic Kill-Switch**:
- **Real-time Metrics:** Tracks every cent and token spent in `session_metrics.json`.
- **Budget Caps:** Define your `max_daily_usd` in `edmate_config.yaml`. The pipeline halts automatically if the limit is reached.

---

## 🚀 Getting Started

### 1. Installation
```bash
git clone https://github.com/shmukit/Edmate.git
cd Edmate
pip install -r requirements.txt
```

### 2. Configuration
Copy the template and set your API keys in `.env` and routing in `edmate_config.yaml`:
```yaml
model_routing:
  extraction: "gemini/gemini-1.5-pro"
  generation: "anthropic/claude-3-haiku"
budget:
  max_daily_usd: 5.0
```

### 3. Launch
```bash
# Run the UI (FastAPI + Vanilla JS)
python3 qc_viewer/main.py

# Run the CLI
python3 content_gen/scripts/pipeline/pipeline_orchestrator.py --single-pdf my_paper.pdf
```

---

## 📂 Repository Structure

- `content_gen/core/`: Intelligence, Metrics, and Config logic.
- `content_gen/adapters/`: Storage interfaces (Postgres, etc.).
- `content_gen/scripts/`: Extraction and pipeline orchestration.
- `qc_viewer/`: The Automation Hub frontend and API.
- `content_gen/tests/`: Comprehensive unit and integration tests.

---

## 🤝 Contributing
Interested in adding a new adapter or a custom extraction prompt? Check our **[CONTRIBUTING_MODULAR.md](content_gen/docs/CONTRIBUTING_MODULAR.md)** guide.

---

## 📄 License
MIT License - Open Source

**Built with ❤️ for an accessible, AI-powered education system.**
