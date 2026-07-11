# SmartBot — Execution Plan & Tech Stack

**Assignment:** Deployed agentic multimodal app (Text + Image + PDF + Audio → autonomous task execution)
**Decisions locked:**
- LLM = **Google Gemini** (`gemini-2.0-flash` default, `gemini-1.5-pro` for hard/ambiguous)
- Frontend = **Next.js** (modern UI) → deploy on **Vercel**
- Backend = **FastAPI / Python** → deploy on **Render (Docker)**
- OCR/STT = **Hybrid** (Gemini vision + Tesseract fallback w/ confidence; faster-whisper for audio)
- **Pass mark:** 75/100 · target ~95+

---

## 1. Technology Stack

### Frontend (Next.js)
| Piece | Choice | Purpose |
|---|---|---|
| Framework | **Next.js (App Router) + TypeScript** | Modern web app, fast DX, easy Vercel deploy |
| Styling | **Tailwind CSS + shadcn/ui** | Clean, polished chat UI quickly |
| Icons / markdown | `lucide-react`, `react-markdown` | Output panel + status chips |
| Tool-chain graph | **React Flow** (or Mermaid) | Animated live tool-call graph |
| Streaming | **SSE via fetch stream / EventSource** | Token-by-token output + live trace events |
| Deploy | **Vercel** (free, native Next.js) | Public URL (primary app URL) |

### Backend (FastAPI / Python 3.11)
| Layer | Choice | Why |
|---|---|---|
| API | **FastAPI + Uvicorn** | Async, DI via `Depends`, required by assignment |
| LLM | **Google Gemini** (`google-generativeai`) | Native multimodal, function-calling, free tier |
| Agent core | **Custom orchestrator** (Planner → Tool Registry → Executor → Critic) | Full control of plan trace, cost, tool-viz, self-correction |
| Image OCR | **Gemini vision (primary) + Tesseract/`pytesseract` (fallback + confidence)** | Meets "OCR confidence" requirement |
| PDF | **PyMuPDF (`fitz`)** + `pdf2image` → OCR fallback | Text + scanned PDFs |
| Audio STT | **`faster-whisper`** + LLM cleanup; `ffprobe`/`pydub` for duration | Free transcription + duration |
| YouTube | **`youtube-transcript-api`** + `yt-dlp` fallback | Transcript task |
| URL fetch | **`httpx` + BeautifulSoup/readability-lxml** | Cross-input URL resolution (base req §2A) |
| Testing | **pytest** + FastAPI `TestClient` | Rubric: tests |
| Lint/format | **ruff + black** (+ optional mypy) | Rubric: code quality |
| Container | **Docker** (`ffmpeg`, `tesseract-ocr`, `poppler-utils`) + `render.yaml` | "Docker encouraged"; reproducible |

### Communication
REST (`POST /chat` multipart) + **SSE** (`GET /stream`) · CORS enabled · frontend reads `NEXT_PUBLIC_API_URL`.

---

## 2. Architecture

```
┌──────────────────────── Next.js Frontend (Vercel) ─────────────────────────┐
│  Chat UI · multi-file drag-drop upload · text-only output panel             │
│  extracted-text panel · ANIMATED plan trace + tool graph (React Flow)       │
│  estimate-vs-actual cost panel · sample test-case gallery · export report   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                       REST /chat (multipart)  +  SSE /stream  (CORS)
┌────────────────────────────────────▼────────────────────────────────────┐
│                       FastAPI Backend (Render · Docker)                   │
│  ┌──────────────┐   ┌──────────────────────┐   ┌────────────────────┐    │
│  │Input Pipeline │→ │     Agent Core         │→ │   Tool Registry    │    │
│  │(parallel      │   │ Planner → Executor →   │   │ (DI-injected)     │    │
│  │ extractors)   │   │ Critic (self-correct)  │   │                   │    │
│  └──────────────┘   └──────────────────────┘   └────────────────────┘    │
│  text/img(OCR)/pdf/   intent · clarify-gate ·     ocr · pdf · stt ·       │
│  audio(STT) →         minimal plan · routing ·    youtube · urlfetch ·    │
│  normalized + meta    cost estimate · trace       summarize · sentiment · │
│  (graceful partial)   · retry/fallback            code-explain · extract  │
└───────────────────────────────────┬────────────────────────────────────┘
                                     ▼   Gemini API (reason · vision · summaries · critic)
```

Pipeline-first design: extract/transcribe **everything in parallel**, then the agent plans the minimal tool chain over the combined context, executes with a trace, and a **critic pass** validates the output before returning.

### RAG — gated dense retrieval (optimized for accuracy, relevance, latency)

Question-answering over documents uses retrieval-augmented generation (`app/rag/`):
**chunk → embed → index → retrieve top-k**. Documents are split into overlapping,
page-aware chunks (`chunker.py`), embedded with **Gemini embeddings**
(`gemini-embedding-001`), and indexed in an **in-memory cosine vector store**
(`store.py`, numpy — exact nearest-neighbour, no heavy vector DB, no index-build
latency). The `answer` tool retrieves the top-k relevant chunks and answers from them,
citing the page each fact came from.

Retrieval is **gated by document size** to serve all three sub-criteria:
- **Latency** — small docs (below ~6k chars) skip retrieval entirely and use full
  context; no embedding round-trip, no overhead.
- **Accuracy / relevance** — large docs are answered from the top-k semantically
  relevant chunks (with page citations) instead of a diluted full-text dump.
- **Cross-input** — retrieval only replaces context for single-document Q&A on large
  inputs; comparisons/summaries still see the whole content, so nothing is dropped.

Extraction still gets 100% of the content *out of each file* (Gemini-vision-first OCR,
never silently dropping pages) — retrieval then decides what to *put into the prompt*.

---

## 3. Standout Features (approved) → integrated

### Agent core
- **Self-correcting loop (evaluator-optimizer):** after a tool produces output, a critic LLM pass checks it against the detected goal + format rules (e.g. summary = 1-line + exactly 3 bullets + 5 sentences) and refines once if it fails. → *Correctness*
- **Confidence-aware routing:** easy queries → `gemini-flash`; ambiguous/heavy → `gemini-pro`. → *Autonomy, cost*
- **Parallel extraction + sentiment voting:** all files extracted concurrently (asyncio); sentiment run 3× majority-vote. → *Robustness, Correctness*

### Tools
- **PDF Q&A with citations:** answers cite the page/line they came from. → *Correctness, trust* (elevates Test Case 2)
- **Structured extraction:** tables → clean markdown; action-items / entities as structured output. → *Correctness*
- **Generic URL fetch:** any link in PDF/text fetched + summarized (base req §2A; generalizes YouTube task).

### Transparency & UX
- **Animated plan trace + tool graph:** each step lights up live with status, timing, and a one-line "why this tool" rationale (covers tool-viz bonus). → *Explainability, UX*
- **Sample test-case gallery:** one-click load of the 5 official test cases. → *UX & Demo*
- **Estimate-vs-actual cost panel:** predicted cost before run (token count × price table), actual per-tool cost after (cost-estimator bonus++). → *bonus*
- **In-session memory + export:** remembers extracted docs for follow-ups without re-upload; download full run (inputs, extracted text, plan, result, cost) as `.md`/`.json`.

### Robustness
- **Graceful partial-failure:** one bad file doesn't kill the run — UI shows what failed and why, answer continues from the rest. → *Robustness*
- **Retry + model fallback:** backoff retries and flash→pro fallback on API errors, surfaced in the trace. → *Robustness*

### Base bonuses (§9) — all covered
Cost estimator ✓ (now estimate-vs-actual) · Streaming ✓ (SSE token-by-token) · Tool-call visualization ✓ (animated graph).

---

## 4. Requirement Coverage (quick map)

- **Inputs §1:** multipart `query` + multiple `files[]`, routed by MIME; multi-input combined into one context.
- **Intent §2A:** planner derives goal + constraints + minimal ordered plan; resolves cross-input URLs.
- **Follow-up rule §2B:** planner returns `needs_clarification` + question; backend stops and asks — no guessing.
- **8 tasks §3:** each a registered tool; summaries enforce the strict 3-format output via the critic.
- **Deploy §4:** Vercel (frontend) + Render Docker (backend); README documents env vars.
- **UI §5:** query box · multi-upload · text-only output · extracted-text panel · live plan trace — all present.
- **Deliverables §6:** modular monorepo · Mermaid architecture diagram · FastAPI + Next.js · Dockerfile + render.yaml · live URLs · tests · README.
- **5 test cases §8:** verified end-to-end with bundled sample inputs.

---

## 5. Build Schedule (revised for Next.js + features)

**Phase 0 — Scaffold:** monorepo (`/backend` FastAPI + Docker + ruff/black; `/frontend` Next.js + Tailwind + shadcn), Gemini client + DI, CORS, `/health`.
**Phase 1 — Input pipeline:** parallel extractors (text/image-OCR/pdf/audio-STT) + confidence + duration + graceful partial results.
**Phase 2 — Tool registry:** 8 tasks + URL fetch + structured extraction + citations, each unit-tested.
**Phase 3 — Agent core:** planner (intent, clarify-gate, routing, minimal plan), executor + trace, **critic self-correct loop**, retry/fallback, cost estimate.
**Phase 4 — Next.js chat UI:** chat, multi-upload, output + extracted-text panels, SSE streaming.
**Phase 5 — Standout UX:** animated trace + tool graph, sample gallery, estimate-vs-actual cost, memory + export.
**Phase 6 — Robustness + tests:** pytest for all 5 test cases + unit tests; sample inputs.
**Phase 7 — Deploy + docs:** Vercel + Render deploy, public URLs, README + Mermaid diagram + demo walkthrough.

---

## 6. Repo Structure (monorepo)

```
smartbot/
  backend/
    app/
      main.py            # FastAPI app, routes, SSE
      deps.py            # DI providers
      config.py          # env vars, models + price table
      pipeline/          # parallel extractors: text, image_ocr, pdf, audio_stt
      agent/             # planner.py, executor.py, critic.py, trace.py, cost.py, router.py
      tools/             # registry.py + one file per tool (8 tasks + urlfetch + extract)
      schemas.py         # pydantic models
    tests/               # pytest: one per test case + unit tests
    samples/             # sample pdf/image/audio for the gallery
    Dockerfile
    render.yaml
    requirements.txt
  frontend/              # Next.js app (App Router, TS, Tailwind, shadcn)
    app/                 # chat page + panels
    components/          # ChatBox, UploadDropzone, TracePanel, ToolGraph, CostPanel, SampleGallery
    lib/                 # api client (REST + SSE)
  README.md              # setup, usage, design decisions, architecture diagram
```

---

## 7. Deployment Notes
- **Frontend → Vercel:** connect GitHub repo, root = `/frontend`, set `NEXT_PUBLIC_API_URL` to the Render backend URL. Auto HTTPS + public URL (this is the primary demo URL).
- **Backend → Render (Docker):** `render.yaml` web service from `/backend`, set `GEMINI_API_KEY`. CORS allows the Vercel origin.
- (Alt: dockerize Next.js and host both on Render if a single platform is preferred.)
