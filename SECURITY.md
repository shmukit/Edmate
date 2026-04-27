# 🔒 Edmate Security Policy

## Responsible Disclosure

If you discover a security vulnerability in Edmate, please **do not open a public GitHub issue**. Instead, email the maintainer directly:

- **Email**: [maintain a private contact — add yours here]
- **Response time**: We aim to respond within 72 hours.

We take security seriously and will work with you to address any valid issues promptly.

---

## 🔑 BYOK (Bring Your Own Key) — Security Guarantee

Edmate is designed with a **"No Custody" key model**:

- Your LLM API keys are **never stored** on the Edmate server.
- Keys passed via `X-API-Key` header or the UI settings panel are used **only for the duration of that single request**.
- Keys passed in the UI are stored in **browser `sessionStorage` only** — they are cleared when the browser tab is closed.
- Edmate does not log, cache, or transmit your key to any third party.

---

## 🛡️ Baseline Security Measures

| Layer | Measure | Status |
| :--- | :--- | :--- |
| **Secrets Management** | `.env` in `.gitignore`; no keys in codebase | ✅ Enforced |
| **Input Validation** | File type and size limits on upload endpoint | ✅ Active |
| **Rate Limiting** | `slowapi` middleware recommended for production deployments | ⚠️ Recommended |
| **CORS** | Configured to restrict cross-origin requests in production | ⚠️ Configure for deployment |
| **Prompt Injection** | Source file content treated as raw user data; LLM context is role-sandboxed | ✅ By design |
| **Dependency Scanning** | Run `pip-audit` on `requirements.txt` before releases | ⚠️ Recommended |

---

## 🔐 MCP Security Guidance

When using Edmate as an MCP Tool in an Agentic IDE (e.g., Cursor, Windsurf):

- **Scope tools narrowly**: Expose only the specific tools needed (e.g., `generate_question`, `get_draft`). Do not expose admin or delete operations.
- **Use read-only MCP tokens** for automated agent pipelines. Reserve write-capable tokens for human-supervised workflows.
- **Review MCP tool outputs** before injection into production question banks.

---

## 🚫 What Edmate Does NOT Do

- Does not store student data or attempt records (out of scope by design).
- Does not retain user-uploaded PDF files beyond the draft lifecycle.
- Does not share generated content with third parties.

---

## ✅ Security Checklist for Self-Hosted Deployments

Before deploying Edmate in a production environment:

- [ ] Set `CORS` `allow_origins` to your specific domain (not `*`).
- [ ] Enable `slowapi` rate limiting on `/api/automate/draft`.
- [ ] Ensure `content_gen/.env` is never committed to version control.
- [ ] Rotate LLM API keys regularly.
- [ ] Add a reverse proxy (nginx/Caddy) with TLS termination.
- [ ] Run `pip-audit` to check for known vulnerabilities in dependencies.
