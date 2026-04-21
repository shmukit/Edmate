# Contributor's Guide: Modular Edmate Architecture

This guide is for developers who want to extend Edmate by adding new model providers, storage adapters, or agentic tools.

---

## 🏗️ The Three Pillars

The Edmate core is built on three decoupled components:

1.  **The Routing Engine (`core/model_router.py`)**: Manages LLM task distribution, costs, and safety.
2.  **The Adapter Layer (`adapters/`)**: Manages data persistence and schema mapping.
3.  **The Config System (`core/config.py`)**: Manages budget and provider settings via YAML.

---

## 💾 Adding a New Storage Adapter

To support a new database (e.g., MongoDB, SQLite, or a specific proprietary schema):

1.  **Define the Interface**: Create a new file in `content_gen/adapters/` (e.g., `sqlite_adapter.py`).
2.  **Inherit from Base**: Your class must inherit from `BaseStorageAdapter`.
3.  **Implement Methods**:
    - `save_question(question: ProcessedQuestion)`: Map the Pydantic model to your SQL/NoSQL schema.
    - `save_flashcards(flashcards: List[Flashcard], context: Dict)`: Bulk persist flashcards.
    - `initialize_schema()`: Static method to create your tables/collections.

```python
from .base import BaseStorageAdapter

class SQLiteAdapter(BaseStorageAdapter):
    def save_question(self, question):
        # Your custom mapping logic here
        pass
```

---

## 🤖 Customizing Model Routing

Routing is handled via `edmate_config.yaml`. Profiles allow you to optimize for different outcomes:

- **Cost-Optimized**: Use GPT-4o-mini or Claude Haiku.
- **Quality-Optimized**: Use GPT-4o or Claude Opus.
- **Multimodal-Heavy**: Use Gemini 1.5 Pro.

To add a new profile, update the `model_routing` section in your YAML:
```yaml
model_routing:
  extraction: "gemini/gemini-1.5-pro"
  generation: "openai/gpt-4o-mini"
  qc_check: "openai/gpt-4o"
```

---

## 🔌 Extending the MCP Server

The MCP (Model Context Protocol) server (`mcp_server.py`) allows Edmate to act as a tool for other AI agents.

To add a new tool:
1.  Add the tool definition to the `tools/list` response.
2.  Add the execution logic to the `tools/call` handler.
3.  The tool should preferably interact with the `ModelRoutingEngine` or a `StorageAdapter`.

---

## 🧪 Testing Your Changes

We use **Pytest** with mocks for all modular components. Always ensure your changes don't break existing routing or budget logic:

```bash
# Set up Python path
export PYTHONPATH=$PYTHONPATH:.

# Run all tests
python3 -m pytest content_gen/tests/
```

---

## 📦 Maintenance Rules
- **No Monoliths**: Keep file lengths under 500 lines.
- **Pydantic First**: Always use the models in `core/schemas.py` for data transfer.
- **Cost Aware**: Every LLM call must be routed through the `ModelRoutingEngine` to ensure budget tracking and the kill-switch function.

**Thank you for building the future of automated education!**
