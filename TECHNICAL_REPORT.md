# SmartBot — Technical Report

An honest, end-to-end description of how SmartBot actually works: its architecture,
the libraries and tools it uses to extract data, how it understands user queries,
how it orchestrates work, how it composes output, and the policies/processes the
codebase follows. Where something is an approximation or a deliberate design choice,
this report says so plainly.

---

## 1. What it is

SmartBot is a deployed agentic multimodal assistant. It accepts **text, images, PDFs,
and audio — several at once in one request**, extracts their content, works out the
user's goal, and autonomously runs the right task (including multi-step chains such as
"read the PDF → follow the YouTube link in it → summarise the video"). If the request
is ambiguous it asks a follow-up instead of guessing. All final output is text.

The system is split into two deployables:

- **Frontend** — Next.js (React) chat UI, intended for Vercel.
- **Backend** — FastAPI (Python) agent, containerised with Docker, intended for Render.

The LLM is **Google Gemini**. There is no other model provider.

---

## 2. Technology stack (what we actually use)

### Frontend
| Concern | Library |
|---|---|
| Framework | Next.js 16 (App Router) + React 19 + TypeScript |
| Styling | Tailwind CSS v4 + shadcn/ui (Radix primitives) |
| Icons / markdown | `lucide-react`, `react-markdown` + `remark-gfm` |
| Tool-chain graph | `reactflow` |
| Streaming | native `fetch` + `ReadableStream` reader parsing SSE frames |
| Theme | `next-themes` (light/dark) |
| Persistence | browser `localStorage` |

### Backend
| Layer | Library / tool | Role |
|---|---|---|
| API + async server | FastAPI + Uvicorn | routes, DI via `Depends`, SSE streaming |
| Config | `pydantic-settings` | env-driven settings, typed |
| LLM SDK | `google-generativeai` | Gemini text + vision + **embeddings** (for RAG) |
| RAG index | `numpy` | in-memory cosine vector store (chunk → embed → top-k) |
| PDF | **PyMuPDF (`fitz`)** | digital text extraction + page rasterisation |
| Image / scanned-PDF OCR | **Gemini Vision** (primary) + **Tesseract** (`pytesseract` + `Pillow`, fallback + confidence) | text from images and scanned pages |
| Audio STT | **faster-whisper** | speech-to-text + clip duration |
| YouTube | `youtube-transcript-api` (primary) + **`yt-dlp` + faster-whisper** (fallback) | transcript fetching |
| Generic URL | `httpx` (async) + `BeautifulSoup` (`lxml`) | fetch + readable-text extraction |
| Tests / lint | `pytest`, `pytest-asyncio`, `ruff` | offline test suite + linting |
| Container | Docker (`ffmpeg`, `tesseract-ocr`) | reproducible runtime |

### Models & model policy
- Default: **`gemini-2.5-flash`** for every call.
- **`gemini-2.5-pro`** is available but **off by default** — enabled only with `GEMINI_USE_PRO=true`. When off, the app is flash-only and never escalates to pro (pro has far lower rate limits). This is a deliberate cost/limits decision.

---

## 3. End-to-end request lifecycle

A single request flows through these stages. The backend streams the whole thing to the
UI as Server-Sent Events, so the user watches it happen live.

```
POST /chat (multipart: query + files[] + optional prior_context)
        │
        ▼
1. INPUT PIPELINE  — extract every input in parallel (asyncio.gather)
        │            text · image OCR · PDF parse · audio STT
        ▼
2. ROUTE + PLAN    — an LLM router decides intent + which documents are relevant
        │            (deterministic keyword planner as the offline fallback):
        │            clarify-gate → intent → relevant-doc selection → tool chain
        ▼
   (if ambiguous)  → emit clarify question, stop, wait for the user
        │
        ▼
3. EXECUTE         — run each stage, streaming a live trace with per-step detail
        │            Understand → Extract → (Fetch) → Generate → Refine → Compose
        ▼
4. REFINE          — self-correcting critic validates/repairs the output format
        ▼
5. COMPOSE         — stream the final text answer token-by-token
        ▼
6. SUGGEST + COST  — emit follow-up questions + reconcile estimated vs actual cost
        ▼
   done
```

The SSE event types on the wire: `plan` (carries the detected intent + a plain-English
"understood goal"), `step` (each stage, with a runtime `detail`), `extracted`,
`cost_estimate`, `token`, `clarify`, `suggestions`, `cost_actual`, `done`, `error`.

---

## 4. Input pipeline — how we extract data

All uploads are extracted **concurrently** (`asyncio.gather`); one bad file does not
abort the others (graceful partial results). Each extractor returns a normalized
`ExtractedDoc` plus metadata (timing, engine used, confidence).

- **Text** — passed through as-is.
- **Image OCR** (`pipeline/image_ocr.py`) — runs **Tesseract** for a real confidence
  score, and **Gemini Vision** for a clean, layout-aware transcript; prefers the Gemini
  transcript when available, falls back to Tesseract, and degrades to an error only if
  both are unavailable.
- **PDF** (`pipeline/pdf.py`) — **PyMuPDF** reads digital text directly. A page with too
  little text but an embedded image (a scan) is rasterised (`get_pixmap`) and sent to OCR
  — **Gemini Vision first** (needs only an API key, no local binary), **Tesseract** as
  fallback. Every page is tagged `[Page N]` so downstream tools can cite pages, and a page
  that genuinely can't be read is labelled `[unreadable page…]` and recorded in metadata —
  **it is never silently dropped**. (This robustness was a direct response to real
  partial-extraction bugs.)
- **Audio** (`pipeline/audio_stt.py`) — **faster-whisper** transcription with the clip
  duration reported. The model is cached under `backend/.models` and the temp clip is
  written there too (not `~/.cache` or `C:\Temp`), to avoid Windows permission issues; the
  file handle is closed before Whisper reads it (Windows reopen constraint).

Cross-input links are resolved after extraction: a **YouTube** URL found in any input is
fetched via `youtube-transcript-api`, falling back to **`yt-dlp` audio download + Whisper**;
any other URL is fetched with **`httpx`** and reduced to readable text with **BeautifulSoup**
(scripts/style/nav stripped, capped at 12k chars).

---

## 5. Agent core — how we understand queries and orchestrate

### Router + Planner (`agent/router.py`, `agent/planner.py`)
Intent and document relevance are decided by an **LLM router** ([`router.py`](backend/app/agent/router.py))
when a key is available: it reads the message + the conversation's documents and returns the
task, whether to clarify, and which document(s) this message refers to (so "summarize the
sentiment" → sentiment, "how was that calculated?" → answer, "compare A and B" → both docs).
Offline it falls back to the **deterministic keyword planner** so behaviour stays predictable and
unit-testable without an API key. The planner also builds the tool chain in both paths. It:

1. **Estimates tokens** and **detects intent** from the query via keyword rules:
   `summarize | sentiment | code_explain | structured_extract | answer`.
   *(Honest note: "tokenize" here is a ~4-chars-per-token estimate, not a true BPE
   tokenizer; it drives the cost estimate and the trace, not model input.)*
2. **Clarify-gate (mandatory follow-up rule):** if there's a file but no actionable
   query, or the request is ambiguous, it returns a short clarifying question and **stops**
   — it does not guess.
3. **Follow-up routing:** on a follow-up turn (context already in memory, no new file this
   turn) a specific question is routed to conversational **answer** rather than re-running a
   rigid task tool — unless the user explicitly re-requests a formatted deliverable. This
   fixed a real "repeated canned response" problem.
4. **Cross-input detection:** finds URLs across the query + extracted content and adds a
   `youtube_transcript` or `url_fetch` step.
5. **Builds the minimal ordered pipeline** and a one-line **understood-goal** statement.

### Executor (`agent/executor.py`) — orchestration + streaming
Runs the plan end-to-end and yields SSE frames. It emits the plan, a **pre-run cost
estimate**, then executes each stage with **live timing and a runtime `detail`** describing
what actually happened (engine used, fallback taken, model, critic verdict, chars streamed).
Any single step failing is marked `error` and the run continues (graceful degradation). The
visible pipeline stages are: **Understand → Extract → Fetch → Generate → Refine → Compose.**

### Critic / self-correct (`agent/critic.py`) — evaluator-optimizer
After generation, a **critic** validates the output against that intent's format contract
(e.g. summary = 1-line + exactly 3 bullets + 5-sentence; sentiment = label + confidence;
code = bugs + time complexity; extraction = a bullet list/table). If it fails, the critic
asks the LLM to **reformat once**, preserving facts. `answer` has no fixed contract and is
intentionally exempt.

### Tool registry (`tools/registry.py`) — dependency injection
A registry maps tool names to async `run(ctx)` callables, injected into the executor. This
decouples the agent core from individual tools and keeps each tool independently testable.

---

## 6. Tool layer — the tasks and their techniques

Each tool builds a **task-specific prompt** (system instruction + labelled context + the
query) — i.e. the app does prompt engineering, not raw pass-through.

| Tool | Technique used |
|---|---|
| `summarize` | format-constrained prompt (strict 1-line / 3-bullet / 5-sentence contract) |
| `sentiment` | **3-vote ensemble** (3 concurrent calls, majority label) + label/confidence contract; lexicon heuristic when offline |
| `code_explain` | structured code-analysis prompt (language, walkthrough, bugs/edge-cases, Big-O) |
| `structured_extract` | extraction prompt that cites `[Page N]` markers; regex heuristic when offline |
| `answer` | context-grounded reasoning prompt + **RAG** (top-k page-cited chunks for large docs, full context for small); brings in general knowledge/estimation and states assumptions |
| `youtube_transcript` | transcript API → `yt-dlp` + Whisper fallback |
| `url_fetch` | `httpx` + BeautifulSoup readable-text extraction |

---

## 7. LLM layer — the Gemini client (`gemini_client.py`)

A thin, resilient wrapper around the Gemini SDK:

- **Lazy configuration** from settings; supports multimodal `parts` (image bytes) alongside text.
- **Retry with exponential backoff** on transient API errors.
- **Model selection** via `settings.model_for()` — flash by default; pro only when
  `GEMINI_USE_PRO` is on (and only then is flash→pro fallback enabled).
- **Token accounting** — reads `usage_metadata` when the API returns it, otherwise falls
  back to the ~4-chars/token estimate.
- **Offline degradation** — if no API key is set it raises `LLMUnavailable`, and tools fall
  back to deterministic heuristics so the app (and the test suite) still respond. This is
  why the whole backend test suite runs with no key.

**Cost** (`agent/cost.py`): a `PRICE_TABLE` of published per-model USD rates drives an
estimate *before* the run (input token estimate + expected output) and the **actual** cost
*after* (from accumulated real usage). Both are shown in the UI (estimate-vs-actual panel).

---

## 8. Output — how we compose and stream

The final text is streamed **token-by-token** over SSE (`token` events); the compose stage
also appends the audio clip duration when relevant. Output is always plain text/markdown
(no files), per requirement. After the answer, the backend makes one more small LLM call to
propose **3 follow-up questions**, streamed as a `suggestions` event.

---

## 9. Frontend — UI and UX features

- **Chat UI** with multi-file drag-drop upload and streaming responses.
- **Agent-activity inspector** (per chat, per question, newest→oldest boxes):
  - **Plan Trace** — each question's stages with the detected **intent**, the
    **understood goal**, and a live per-stage **detail** line (engine, fallback, model,
    critic verdict).
  - **Tool Graph** — the tool chain of each question rendered with ReactFlow.
  - **Extracted Text** — the raw text pulled from each input, with OCR confidence.
  - **Cost** — estimated vs actual.
- **In-session memory** — previously extracted docs are replayed to the backend on
  follow-ups, so the user doesn't re-upload.
- **Follow-up suggestion chips** — click to load into the composer.
- **Export** — download a run as `.md` or `.json`.
- **Sample gallery** — one-click load of bundled demo inputs (`/public/samples`).
- **Chat management** — create, select, **delete (with confirmation)**, and **persist chats
  in `localStorage`** across reloads (raw file blobs are stripped before saving).
- **Mock mode** — with no backend URL set, the UI runs an in-browser mock so it's usable
  during frontend development.

---

## 10. Policies & processes the codebase follows

- **Configuration is environment-driven** (`pydantic-settings`); no secrets in code. The
  `.env` is loaded by **absolute path** so it works regardless of the launch directory.
  `.env.example` is a committed, secret-free template; `.env` is gitignored.
- **Separation of concerns:** API layer (`main.py`) → orchestration (`executor`) → tool
  layer (`tools/*`) → LLM layer (`gemini_client`). Extraction is its own pipeline package.
- **Dependency injection:** Gemini client and tool registry are lazily-cached singletons
  provided via FastAPI `Depends` / the executor.
- **All I/O is async;** CPU/blocking work (PyMuPDF, Tesseract, Whisper) runs in threads via
  `asyncio.to_thread` so the event loop stays responsive.
- **Robustness by default:** parallel extraction with graceful partial failure; retries +
  offline heuristic fallbacks; upload size guard; extraction that surfaces unreadable pages
  instead of dropping them; writable project-local dirs for model cache and temp files.
- **Testing & quality:** `pytest` suite (21 tests) covering URL/intent detection, the
  clarify-gate, the summary-format validator, follow-up routing, the full pipeline shape,
  and the assignment's sample cases — **all offline, no API key**. `ruff` for linting.
- **Deployment:** Dockerfile bundles `ffmpeg` + `tesseract-ocr`; `render.yaml` blueprint for
  the backend; Vercel for the frontend; CORS restricted to configured origins.
- **CORS / security:** allowed origins are configurable; the API key lives only in `.env`
  (local) and the host's secret store (prod).

---

## 11. Deliberate design decisions (stated honestly)

- **RAG via gated dense retrieval.** Document Q&A uses retrieval-augmented generation
  (`app/rag/`: chunk → embed with `gemini-embedding-001` → in-memory cosine vector index →
  top-k). It is **gated by document size** to optimize the three sub-criteria at once:
  *latency* (small docs skip retrieval and use full context — no embedding round-trip),
  *accuracy/relevance* (large docs are answered from the top-k relevant, page-cited chunks
  rather than a diluted full-text dump), and *cross-input* (comparisons/summaries still see
  the whole content, so nothing is dropped). An in-memory numpy index (exact nearest-neighbour)
  is used instead of a heavy vector DB — no index-build latency for these corpus sizes.
- **LLM router with a deterministic fallback.** Intent + document-relevance are decided by an
  LLM (with full conversation context) because keyword rules are brittle ("summarize the
  sentiment" is a sentiment task, not a summary). When no key is present, a rule-based keyword
  planner takes over so the app — and the whole test suite — still work offline and predictably.
- **Flash-only by default.** Pro is gated behind a flag because of its low rate limits.

---

## 12. Honest limitations / not-yet-done

- **Not deployed yet** — no live public URLs at time of writing; all config is in place
  (Docker, `render.yaml`, Vercel-ready build) but the actual deploy + URL fill-in is pending.
- **"Tokenization" is an estimate** (~4 chars/token), not a real tokenizer; it feeds the
  cost estimate and the trace, not the model.
- **Intent detection is keyword rules**, so unusual phrasings can mis-route (mitigated by the
  clarify-gate and follow-up→answer routing, but not eliminated).
- **The critic is a format validator + single repair**, not a full evaluation framework.
- **No bundled audio sample** (offline TTS isn't available); the audio gallery cards are
  prompt-only and expect the user to attach a clip.
- **YouTube `yt-dlp` fallback** is best-effort — datacenter IPs (e.g. on a cloud host) are
  frequently blocked by YouTube, so the transcript API remains the reliable path.

---

## 13. Repository structure

```
smartBot/
  backend/
    app/
      main.py            # FastAPI app, CORS, /health, POST /chat (SSE)
      config.py          # env settings + model/price table
      deps.py            # DI providers (cached singletons)
      gemini_client.py   # resilient Gemini wrapper (retry, model policy, tokens)
      sse.py             # SSE event encoders (the wire contract)
      schemas.py         # pydantic models (camelCase aliases matching the frontend)
      utils.py           # URL detection, token estimate
      pipeline/          # parallel extractors: text, image_ocr, pdf, audio_stt, dispatch
      agent/             # planner, executor, critic, cost
      tools/             # registry + one module per tool
    tests/               # pytest (offline)
    Dockerfile · render.yaml · requirements.txt · .env.example
  frontend/
    src/
      app/               # chat page
      components/        # sidebar, inspector, chat/*, panels/* (trace, graph, extracted, cost)
      hooks/use-chat.ts  # chat state, streaming events, persistence
      lib/               # api client (REST + SSE), types, export, mock, utils
    public/samples/      # bundled demo inputs
  PLAN.md · README.md · TECHNICAL_REPORT.md (this file)
```

---

*This report reflects the codebase as implemented. Claims are grounded in the actual
modules named above; approximations and pending items are called out rather than glossed.*
