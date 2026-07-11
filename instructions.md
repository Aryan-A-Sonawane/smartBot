# ⚠️ AGENT INSTRUCTIONS — READ BEFORE ANY OPERATION

> **This file MUST be read and strictly followed before making any code change, file creation, command execution, or architectural decision in this project.**

---

## 🚨 Disclaimer

A **GPT-based detection system** is active as part of the screening and evaluation process.
**~60% of candidates are currently being rejected** due to AI-generated code being detected.

**Do not blindly generate boilerplate or LLM-typical patterns.**
Write code that is intentional, idiomatic, minimal, and human-like in structure.
Every line must have a clear reason for existing.

---

## 📋 Evaluation Criteria

### 1. Code Quality
- Write clean, readable, and purposeful code — **not auto-generated scaffolding**.
- Avoid overusing LLMs for trivial tasks. Prove craftsmanship through deliberate design choices.
- Follow language-specific idioms (Pythonic code for Python, proper TypeScript typing, etc.).
- No dead code, unnecessary comments, or redundant abstractions.
- Prefer clarity over cleverness. Each function/module should do one thing well.

### 2. Tool Implementation
- Tools must be **properly integrated** — not stubbed or mocked unless clearly isolated for testing.
- Each tool must have:
  - A well-defined input/output contract (typed).
  - Correct and validated usage of the underlying API or SDK.
  - Reliable execution with deterministic behavior where possible.
- Avoid copy-pasting tool code from documentation without understanding and adapting it.

### 3. Orchestration Logic
- Orchestration flows must have **explicit, well-documented conditions** for when each tool is invoked.
- Avoid ambiguous branching — every fork in orchestration must have a clear reason.
- Design for predictability: the same input should follow the same tool path.
- Separate planning logic from execution logic. Do not mix these concerns.
- Include a clear fallback/error path for each tool call in the orchestration graph.

### 4. Adherence to Tech Stack
- **Strictly follow the specified tech stack** — do not introduce unlisted dependencies or frameworks.
- Approved stack (from `PLAN.md`):
  - **Frontend**: Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui
  - **Backend**: FastAPI + Python 3.11 + Uvicorn
  - **LLM**: Google Gemini (`gemini-2.0-flash` / `gemini-1.5-pro`)
  - **OCR/STT**: Gemini Vision + Tesseract fallback; faster-whisper for audio
  - **Deploy**: Vercel (frontend) + Render via Docker (backend)
- Any deviation from the tech stack must be explicitly justified and noted in the relevant file.

### 5. Implementation Architecture
- The architecture must be **robust, scalable, and production-ready** — not a proof-of-concept hack.
- Follow separation of concerns:
  - API layer → Service layer → Tool layer → LLM layer.
  - Each layer should be independently testable.
- Use dependency injection where applicable (FastAPI `Depends`).
- Configuration must be environment-driven (`.env` / environment variables) — no hardcoded secrets.
- All I/O-heavy operations must be **async**.
- Structure the project for horizontal scalability (stateless services where possible).

### 6. RAG Performance
- Retrieval-Augmented Generation must be optimized for:
  - **Accuracy**: Retrieved chunks must be semantically relevant to the query.
  - **Relevance**: Use appropriate chunking strategies and overlap to preserve context.
  - **Latency**: Minimize retrieval time; avoid redundant embedding calls.
- Use a vector store with proper indexing.
- Implement re-ranking or filtering where retrieval alone is insufficient.
- Do not retrieve and dump entire documents — chunk, embed, rank, and trim.

### 7. Application Robustness
- The application must **gracefully handle all edge cases**, including:
  - Empty inputs, malformed files, unsupported formats.
  - Network timeouts, LLM API rate limits, and quota exhaustion.
  - Extremely large inputs (chunking, pagination, or rejection with clear error messages).
- All errors must be:
  - Caught and logged at the appropriate layer.
  - Surfaced to the user with a meaningful, non-technical message.
  - Never allowed to crash the server silently.
- Input validation must happen at the API boundary, not deep inside business logic.

---

## ✅ Before Every Code Change — Checklist

Before writing or modifying any code, confirm:

- [ ] Have I read this file?
- [ ] Does my change align with the approved tech stack?
- [ ] Is the code hand-crafted and intentional — not boilerplate or LLM-generated filler?
- [ ] Are all tool integrations correctly typed and validated?
- [ ] Are orchestration conditions explicit and traceable?
- [ ] Is the architecture designed for production, not just to pass local tests?
- [ ] Are edge cases handled at every I/O boundary?
- [ ] Have I avoided introducing unnecessary dependencies?

---

## 📂 Key Project Files

| File | Purpose |
|------|---------|
| [`PLAN.md`](./PLAN.md) | Full tech stack decisions and execution plan |
| [`README.md`](./README.md) | Project overview and setup instructions |
| [`backend/`](./backend/) | FastAPI backend — all server-side logic |
| [`frontend/`](./frontend/) | Next.js frontend — all UI and client logic |
| [`instructions.md`](./instructions.md) | **This file** — must be read before any operation |

---

> _Last updated: 2026-07-10_
