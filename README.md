# Edmate 🎓

**The Modular AI Factory for Educational Content Generation**

Edmate is an open-source, vendor-agnostic pipeline designed to transform unstructured educational materials (PDFs, images, documents) into high-fidelity learning modules, flashcards, and MCQ banks. 

Built with **modularity** and **modality** at its core, Edmate allows organizations to bring their own intelligence (LLMs), their own storage, and their own database schemas.

---

## 🏗️ Modular Architecture

Edmate is designed to be "Intelligence-Blind" and "Database-Agnostic."

### 1. Intelligence Layer (LLM Agnostic)
Powered by **LiteLLM**, Edmate supports 100+ model providers (OpenAI, Gemini, Anthropic, Ollama, etc.). Users can route specific tasks to different models to optimize for cost and capability:
- **Extraction:** Use Gemini 1.5 Pro for its massive multimodal context.
- **Generation:** Use Claude 3 Haiku or GPT-4o-mini for fast, structured output.
- **Verification:** Use GPT-4o for high-reasoning quality control.

### 2. Persistence Layer (BYO-Database)
Edmate uses the **Adapter Pattern** for data storage. The core pipeline produces standardized Pydantic JSON objects, which you can map to any schema:
- **PostgreSQL / MySQL / MongoDB**
- **Vector DBs for RAG**
- **Flat files (JSON/Markdown)**

### 3. Execution Interfaces
- **The Dashboard:** A user-friendly UI for non-coders to manage providers and view analytics.
- **CLI & Python Library:** For developers to integrate Edmate into their own applications.
- **MCP Server:** Plug Edmate directly into Agentic IDEs like **Cursor** or **Windsurf** as a native tool.

---

## 🛡️ Security & Governance (OWASP Top 10 for LLMs)
Edmate implements budget-friendly "AI Safety" guardrails out of the box:
- **Prompt Isolation:** XML-delimited inputs to prevent prompt injection.
- **Output Sanitization:** Middleware to strip executable code/tags from AI responses.
- **Economic Kill-Switch:** Self-pausing pipelines when cost thresholds are met.
- **PII Scrubbing:** Automatic masking of sensitive info before it reaches cloud providers.

---

## 📊 Hybrid Observability
- **Native Analytics:** Real-time tracking of Cost (USD), Tokens, and Latency in the Edmate UI.
- **Deep Tracing:** One-click integration with **Opik, Arize Phoenix, and Langfuse** for scientific evaluation and debugging.

---

## 🚀 Quick Start (Visionary)

### Installation
```bash
# Clone and install
git clone https://github.com/shmukit/Edmate.git
pip install -r requirements.txt
```

### Modular Configuration
Assign specific models to specific tasks in your `edmate.yaml`:
```yaml
model_routing:
  extraction: "gemini/gemini-1.5-pro"
  generation: "anthropic/claude-3-haiku"
  qc_check: "openai/gpt-4o"

storage:
  type: "postgres"
  endpoint: ${DATABASE_URL}
```

### Run the Pipeline
```bash
python -m edmate.pipeline --input biology_paper.pdf --config edmate.yaml
```

---

## 📁 Repository Structure

```
Edmate/
├── content_gen/          # Core Python engine & processing
│   ├── adapters/         # DB & Storage interfaces
│   ├── agents/           # LLM logic & Model Routing
│   ├── scripts/          # Extraction & ingestion logic
│   └── security/         # Sanitization & Safety middleware
├── qc_viewer/            # Next.js/Vanilla Dashboard
└── README.md             # This file
```

---

## 🤝 Contributing & Community
Edmate is evolving into a community-driven educational standard. Whether you are adding a new model provider or a custom database adapter, we welcome your contributions!

---

## 📄 License
MIT License - Open Source

**Built with ❤️ for a more accessible, AI-powered education system.**
