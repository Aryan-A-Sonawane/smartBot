# SmartBot — Implementation Audit

> Audited against `PLAN.md` and `instructions.md` criteria on 2026-07-10.

---

## ✅ What Is Fully Implemented

### Backend — Core

| Module | File | Status |
|--------|------|--------|
| FastAPI app + CORS + health | [`main.py`](file:///e:/z.code/smartBot/smartBot/backend/app/main.py) | ✅ Complete |
| Settings / env / price table | [`config.py`](file:///e:/z.code/smartBot/smartBot/backend/app/config.py) | ✅ Complete |
| DI providers | [`deps.py`](file:///e:/z.code/smartBot/smartBot/backend/app/deps.py) | ✅ Complete |
| Gemini client (retry + flash→pro fallback) | [`gemini_client.py`](file:///e:/z.code/smartBot/smartBot/backend/app/gemini_client.py) | ✅ Complete |
| SSE frame helpers | [`sse.py`](file:///e:/z.code/smartBot/smartBot/backend/app/sse.py) | ✅ Complete |
| Pydantic schemas | [`schemas.py`](file:///e:/z.code/smartBot/smartBot/backend/app/schemas.py) | ✅ Complete |

### Backend — Pipeline (Extractors)

| Extractor | File | Status |
|-----------|------|--------|
| Parallel dispatch | [`pipeline/dispatch.py`](file:///e:/z.code/smartBot/smartBot/backend/app/pipeline/dispatch.py) | ✅ Complete (asyncio.gather) |
| Image OCR (Gemini vision + pytesseract fallback) | [`pipeline/image_ocr.py`](file:///e:/z.code/smartBot/smartBot/backend/app/pipeline/image_ocr.py) | ✅ Complete |
| PDF extraction (PyMuPDF + OCR fallback) | [`pipeline/pdf.py`](file:///e:/z.code/smartBot/smartBot/backend/app/pipeline/pdf.py) | ✅ Complete |
| Audio transcription (faster-whisper) | [`pipeline/audio_stt.py`](file:///e:/z.code/smartBot/smartBot/backend/app/pipeline/audio_stt.py) | ✅ Complete |
| Plain text pass-through | [`pipeline/text.py`](file:///e:/z.code/smartBot/smartBot/backend/app/pipeline/text.py) | ✅ Complete |

### Backend — Agent Core

| Component | File | Status |
|-----------|------|--------|
| Planner (intent, clarify-gate, routing, minimal plan) | [`agent/planner.py`](file:///e:/z.code/smartBot/smartBot/backend/app/agent/planner.py) | ✅ Complete |
| Executor (SSE orchestration, graceful degradation) | [`agent/executor.py`](file:///e:/z.code/smartBot/smartBot/backend/app/agent/executor.py) | ✅ Complete |
| Critic (self-correct loop for summarize) | [`agent/critic.py`](file:///e:/z.code/smartBot/smartBot/backend/app/agent/critic.py) | ✅ Complete |
| Cost estimate + actual | [`agent/cost.py`](file:///e:/z.code/smartBot/smartBot/backend/app/agent/cost.py) | ✅ Complete |

### Backend — Tools

| Tool | File | Status |
|------|------|--------|
| Tool registry (DI) | [`tools/registry.py`](file:///e:/z.code/smartBot/smartBot/backend/app/tools/registry.py) | ✅ Complete |
| Summarize (1-line + 3 bullets + 5-sentences) | [`tools/summarize.py`](file:///e:/z.code/smartBot/smartBot/backend/app/tools/summarize.py) | ✅ Complete |
| Sentiment analysis | [`tools/sentiment.py`](file:///e:/z.code/smartBot/smartBot/backend/app/tools/sentiment.py) | ✅ Complete |
| Code explain | [`tools/code_explain.py`](file:///e:/z.code/smartBot/smartBot/backend/app/tools/code_explain.py) | ✅ Complete |
| Structured extraction | [`tools/structured_extract.py`](file:///e:/z.code/smartBot/smartBot/backend/app/tools/structured_extract.py) | ✅ Complete |
| Answer / QA | [`tools/answer.py`](file:///e:/z.code/smartBot/smartBot/backend/app/tools/answer.py) | ✅ Complete |
| YouTube transcript | [`tools/youtube.py`](file:///e:/z.code/smartBot/smartBot/backend/app/tools/youtube.py) | ✅ Complete |
| URL fetch | [`tools/urlfetch.py`](file:///e:/z.code/smartBot/smartBot/backend/app/tools/urlfetch.py) | ✅ Complete |

### Backend — Infrastructure

| Item | File | Status |
|------|------|--------|
| Dockerfile | [`Dockerfile`](file:///e:/z.code/smartBot/smartBot/backend/Dockerfile) | ✅ Present |
| Render deployment | [`render.yaml`](file:///e:/z.code/smartBot/smartBot/backend/render.yaml) | ✅ Present |
| `requirements.txt` | [`requirements.txt`](file:///e:/z.code/smartBot/smartBot/backend/requirements.txt) | ✅ Complete |
| `pyproject.toml` (ruff) | [`pyproject.toml`](file:///e:/z.code/smartBot/smartBot/backend/pyproject.toml) | ✅ Present |
| `.env` with real API key | [`.env`](file:///e:/z.code/smartBot/smartBot/backend/.env) | ✅ Present |

### Backend — Tests

| Test | File | Status |
|------|------|--------|
| Health endpoint | [`tests/test_api.py`](file:///e:/z.code/smartBot/smartBot/backend/tests/test_api.py) | ✅ Written |
| Clarify gate (file + no query) | same | ✅ Written |
| Test case 2 — PDF action items | same | ✅ Written |
| Test case 4 — PDF + YouTube chain | same | ✅ Written |
| Cost panel fields | same | ✅ Written |
| Unit tests | [`tests/test_unit.py`](file:///e:/z.code/smartBot/smartBot/backend/tests/test_unit.py) | ✅ Written |

### Frontend — Core

| Component | File | Status |
|-----------|------|--------|
| Next.js App Router + layout | [`app/layout.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/app/layout.tsx) | ✅ Complete |
| Main chat page (3-panel layout) | [`app/page.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/app/page.tsx) | ✅ Complete |
| SSE/REST API client | [`lib/api.ts`](file:///e:/z.code/smartBot/smartBot/frontend/src/lib/api.ts) | ✅ Complete |
| Mock agent (frontend-only mode) | [`lib/mock.ts`](file:///e:/z.code/smartBot/smartBot/frontend/src/lib/mock.ts) | ✅ Complete |
| Type definitions | [`lib/types.ts`](file:///e:/z.code/smartBot/smartBot/frontend/src/lib/types.ts) | ✅ Complete |
| Utilities | [`lib/utils.ts`](file:///e:/z.code/smartBot/smartBot/frontend/src/lib/utils.ts) | ✅ Complete |
| Chat state hook (sessions, SSE events) | [`hooks/use-chat.ts`](file:///e:/z.code/smartBot/smartBot/frontend/src/hooks/use-chat.ts) | ✅ Complete |

### Frontend — Components

| Component | File | Status |
|-----------|------|--------|
| Composer (textarea + drag-drop upload + file chips) | [`chat/composer.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/components/chat/composer.tsx) | ✅ Complete |
| Message list + bubbles + markdown | [`chat/message-list.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/components/chat/message-list.tsx) | ✅ Complete |
| Empty state / sample gallery | [`chat/empty-state.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/components/chat/empty-state.tsx) | ✅ Complete |
| Sidebar (session history) | [`components/sidebar.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/components/sidebar.tsx) | ✅ Complete |
| Inspector (right panel host) | [`components/inspector.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/components/inspector.tsx) | ✅ Complete |
| Trace panel | [`panels/trace-panel.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/components/panels/trace-panel.tsx) | ✅ Complete |
| Tool graph (React Flow) | [`panels/tool-graph.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/components/panels/tool-graph.tsx) | ✅ Complete |
| Extracted text panel | [`panels/extracted-panel.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/components/panels/extracted-panel.tsx) | ✅ Complete |
| Cost panel | [`panels/cost-panel.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/components/panels/cost-panel.tsx) | ✅ Complete |
| Sample gallery | [`chat/sample-gallery.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/components/chat/sample-gallery.tsx) | ✅ Complete |
| Dark mode toggle | [`components/mode-toggle.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/components/mode-toggle.tsx) | ✅ Complete |

---

## ⚠️ What Is Partially Implemented / Needs Attention

### 1. Critic only covers `summarize` — other intents unvalidated
- **Where:** [`agent/critic.py`](file:///e:/z.code/smartBot/smartBot/backend/app/agent/critic.py) — `critique()` returns immediately for non-`summarize` intents.
- **Gap:** `sentiment`, `code_explain`, `structured_extract`, `answer` outputs have no format-validation or repair pass.
- **Fix needed:** Add lightweight format checkers for each intent (e.g. sentiment must contain a label + confidence; structured_extract must have bullet items).

### 2. PDF Q&A with citations — not implemented (groundwork present)
- **Where:** [`tools/answer.py`](file:///e:/z.code/smartBot/smartBot/backend/app/tools/answer.py) — answers the question but does not cite page/line numbers.
- **Gap:** PLAN.md §3 says: *"PDF Q&A with citations: answers cite the page/line they came from."*
- **Verified:** page markers (`[Page N]`) are **already embedded** in the extracted text by [`pipeline/pdf.py`](file:///e:/z.code/smartBot/smartBot/backend/app/pipeline/pdf.py) (line 61), so no schema change is required — the page context already reaches the LLM.
- **Fix needed:** instruct `answer.py` (and `structured_extract.py`) to cite the `[Page N]` markers already in context. Purely a prompt change.

### 3. Test cases 1, 3, 5 missing
- **Where:** [`tests/test_api.py`](file:///e:/z.code/smartBot/smartBot/backend/tests/test_api.py) covers cases 2, 4 and some basics. Cases 1 (image OCR + code explain), 3 (audio STT + summary), 5 (multi-input cross-reasoning) have no tests.
- **Fix needed:** Add `test_case1_image_code_explain`, `test_case3_audio_summary`, `test_case5_multi_input` with `conftest` fixtures for image/audio bytes.

### 4. In-session memory (follow-up without re-upload)
- **Where:** [`hooks/use-chat.ts`](file:///e:/z.code/smartBot/smartBot/frontend/src/hooks/use-chat.ts) keeps messages in React state but does **not** send previous extracted docs back to the backend on follow-up turns.
- **Gap:** PLAN.md §3 says: *"remembers extracted docs for follow-ups without re-upload."*
- **Fix needed:** On follow-up sends, attach the `extracted` docs from the previous assistant message into the `FormData` (or a new `context` field), and have the backend accept an optional `prior_context` field.

### 5. Export feature (`.md`/`.json` download)
- **Where:** No export button exists in any component.
- **Gap:** PLAN.md §3 says: *"download full run (inputs, extracted text, plan, result, cost) as `.md`/`.json`."*
- **Fix needed:** Add a download button in the `Inspector` or message bubble that serialises the assistant message data to JSON/markdown.

### 6. `samples/` directory is empty
- **Where:** [`backend/samples/`](file:///e:/z.code/smartBot/smartBot/backend/samples/) has no sample files.
- **Gap:** PLAN.md says sample inputs for the 5 test cases should be bundled.
- **Fix needed:** Add at least one sample PDF, one image, and one audio clip. Also wire the frontend's sample-gallery to load these from a `/samples` endpoint or static directory.

### 7. `README.md` — Architecture diagram ✅ present (audit was wrong)
- **Re-verified:** [`README.md`](file:///e:/z.code/smartBot/smartBot/README.md) lines 55–72 already contain a full ```mermaid``` flowchart of the FE → pipeline → agent core → tool registry → Gemini flow.
- **No action needed.** (Earlier audit entry was inaccurate.)

### 8. `NEXT_PUBLIC_API_URL` points to `localhost` — production value not set
- **Where:** [`frontend/.env.local`](file:///e:/z.code/smartBot/smartBot/frontend/.env.local).
- **Gap:** This is fine for dev, but must be updated to the Render backend URL before Vercel deploy.
- **Action:** Set `NEXT_PUBLIC_API_URL` as a Vercel environment variable (not committed to repo).

---

## ❌ What Is Missing / Not Yet Started

### 1. RAG / Vector Store — ❌ intentionally not implemented (decision, not a gap)
- **Re-assessed against the actual assignment PDF:** the word "RAG" appears **nowhere** in the assignment, and the 100-point rubric allocates it **zero** weight. Every test-case input is small (≤ 3-page PDF / 5-min audio) and fits inside Gemini 2.5's 1M-token window; there is no corpus to index and nothing exceeding the window — the only condition RAG exists to solve. Top-k retrieval would also *degrade* the cross-input compare task (TC5), which needs both docs in full.
- **Decision (recorded in PLAN.md §2):** pass all extracted text **in full** into the tool prompt; invest in robust extraction instead. Map-reduce condensation is the escalation path if an input ever nears the context limit — no vector store.
- **This also removes the "unlisted dependency" conflict with instructions.md §4** (no `chromadb`/`faiss`).

### 2. `yt-dlp` fallback for YouTube — Not implemented
- **Where:** [`tools/youtube.py`](file:///e:/z.code/smartBot/smartBot/backend/app/tools/youtube.py) — only uses `youtube-transcript-api`; no `yt-dlp` fallback.
- **Gap:** PLAN.md says *"`yt-dlp` fallback"* when transcript API fails.
- **Fix needed:** In the `except` block, attempt `yt-dlp` audio download + Whisper transcription as fallback.

### 3. Sentiment majority-vote (3× runs) — ✅ already implemented (audit was wrong)
- **Re-verified:** [`tools/sentiment.py`](file:///e:/z.code/smartBot/smartBot/backend/app/tools/sentiment.py) lines 52–62 run **three** concurrent Gemini calls (`asyncio.gather`, temp 0.4), take the majority label via `Counter`, and return the first response matching the winner. A lexicon heuristic covers the LLM-unavailable path.
- **No action needed.** Optional: add a unit test asserting three calls happen.

### 4. Scanned-PDF OCR fallback — ✅ wired (via PyMuPDF pixmap, not `pdf2image`)
- **Re-verified:** [`pipeline/pdf.py`](file:///e:/z.code/smartBot/smartBot/backend/app/pipeline/pdf.py) lines 50–60 rasterise low-text pages with `page.get_pixmap(dpi=200)` and OCR them with `pytesseract`, averaging confidence. This is a valid (arguably cleaner, poppler-free) scanned-PDF path — a justified deviation from PLAN.md's `pdf2image`.
- **Cleanup:** `pdf2image` is listed in `requirements.txt` but **never imported** — an unused dependency that violates instructions.md §4 ("avoid unnecessary dependencies"). Remove it, or switch the fallback to use it.
- **Optional:** add a unit test with an image-only PDF to exercise this path.

### 5. Vercel + Render deployment — Not done
- **Gap:** No public URLs, no CI/CD pipeline. Required for final submission.
- **Action needed:** Deploy after remaining gaps are closed.

---

## 📊 Summary

| Category | Done | Partial | Missing |
|----------|------|---------|---------|
| Backend core (FastAPI, config, SSE) | 6/6 | 0 | 0 |
| Pipeline extractors | 5/5 (incl. scanned-PDF OCR fallback) | 0 | 0 |
| Agent core (planner, executor, critic, cost) | 4/4 | 1 (critic covers only `summarize`) | 0 |
| Tools (8 tasks + url + youtube) | 7/7 registered; sentiment 3×-vote ✅ | 1 (no citations in `answer`) | 1 (no yt-dlp fallback) |
| Tests | 6 cases | 3 cases missing (1, 3, 5) | 0 |
| Frontend (components, hook, API client) | All present | 2 (memory resend, export) | 0 |
| RAG pipeline | 0 | 0 | **Not started** |
| Samples / README diagram | README Mermaid ✅ | 0 | `samples/` empty |
| Deployment | 0 | 0 | Not done |

---

## 🎯 Recommended Priority Order (revised after re-verification 2026-07-10)

Items struck through were found already implemented during verification. **All items below were completed 2026-07-10** (backend: 17/17 pytest green + ruff clean; frontend: `tsc` clean + `next build` succeeds).

1. ~~**RAG pipeline**~~ — ✅ resolved: intentionally omitted (see Missing #1 + PLAN.md §2). Replaced by **robust extraction**: [`pipeline/pdf.py`](file:///e:/z.code/smartBot/smartBot/backend/app/pipeline/pdf.py) OCRs scanned pages Gemini-vision-first (Tesseract fallback) and never silently drops a page (`failed_pages` metadata + inline marker). Fixes the observed partial-PDF-extraction bug; verified end-to-end on a mixed digital+scanned PDF.
2. ✅ **PDF citations** — `answer.py` now cites `[Page N]` markers (structured_extract already did).
3. ~~**Sentiment 3× majority-vote**~~ — ✅ already implemented.
4. ✅ **Critic for all intents** — [`agent/critic.py`](file:///e:/z.code/smartBot/smartBot/backend/app/agent/critic.py) now validates + one-shot-repairs summarize / sentiment / code_explain / structured_extract (answer has no fixed contract, intentionally exempt).
5. ✅ **In-session memory** — `/chat` accepts `prior_context`; the hook replays session-wide extracted docs on follow-ups (`test_followup_uses_prior_context`).
6. ✅ **Missing test cases (1, 3, 5)** — added as offline e2e SSE tests (audio/image extraction stubbed to avoid Whisper download).
7. ✅ **Export button** — Inspector exports a run as `.md`/`.json` ([`lib/export.ts`](file:///e:/z.code/smartBot/smartBot/frontend/src/lib/export.ts)).
8. ✅ **yt-dlp fallback** — [`tools/youtube.py`](file:///e:/z.code/smartBot/smartBot/backend/app/tools/youtube.py) falls back to yt-dlp audio download + Whisper when the captions API fails.
9. ✅ **Samples** — real demo files generated to **`frontend/public/samples/`** (served statically by Vercel — a justified deviation from PLAN's `backend/samples/`, avoids a backend round-trip/CORS); gallery loads them one-click. Unused `pdf2image` removed. Audio sample stays prompt-only (no offline TTS).
10. ✅ **Deploy prep** — Dockerfile slimmed (dropped `poppler-utils`), `render.yaml` + `.env.example` verified, `next build` passes. **Remaining (needs owner):** run the actual Vercel + Render deploys with `GEMINI_API_KEY`, then fill the live URLs into the README.

### Extra fix found during the work
- **Deploy-blocking TypeScript error** in [`panels/tool-graph.tsx`](file:///e:/z.code/smartBot/smartBot/frontend/src/components/panels/tool-graph.tsx) (`sourcePosition: "bottom"` not assignable to reactflow's `Position`) — would have failed `next build` / Vercel. Fixed to use `Position.Bottom/Top`.
