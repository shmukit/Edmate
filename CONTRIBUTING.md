# Contributing to Edmate 🎓

First off, thank you for considering contributing to Edmate! It's people like you that make Edmate such a great tool for the global education community.

## 🌈 Our Mission
To build an intelligence-blind, budget-safe content factory that makes high-quality educational materials accessible to everyone.

## 📜 Code of Conduct
By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## 🚀 How Can I Contribute?

### Reporting Bugs
- Check the [Issues](https://github.com/shmukit/Edmate/issues) to see if the bug has already been reported.
- If not, use the **Bug Report** template to create a new issue.
- Include a clear description, reproduction steps, and your environment info.

### Suggesting Enhancements
- Use the **Feature Request** template.
- Explain why this feature would be useful and how it should work.

### Pull Requests
1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. Ensure the test suite passes (`pytest content_gen/tests`).
4. Make sure your code follows the style guidelines (we use `flake8`).
5. Open a Pull Request with a clear description of your changes.

## 🏗️ Technical Architecture
Edmate follows a modular **Adapter Pattern**. For deep technical details on extending the system, please see:
- [Extending Storage Adapters](docs/contributing/CONTRIBUTING_MODULAR.md#adding-a-new-storage-adapter)
- [Customizing Model Routing](docs/contributing/CONTRIBUTING_MODULAR.md#customizing-model-routing)
- [Extending MCP Server](docs/contributing/CONTRIBUTING_MODULAR.md#extending-the-mcp-server)

## 🧪 Testing Guidelines
Always run the test suite before submitting a PR:
```bash
export PYTHONPATH=$PYTHONPATH:.
pytest content_gen/tests/
```

## 📦 Style & Standards
- **Pydantic Models**: Always use schemas from `content_gen/core/schemas.py`.
- **Cost Safety**: Every LLM call MUST be routed through the `ModelRoutingEngine`.
- **Keep it Lean**: Aim for small, focused files (under 500 lines).

**Happy coding!**
