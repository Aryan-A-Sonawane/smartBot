# SmartBot — Backend (FastAPI agent)

Agentic multimodal backend. Accepts Text + Image + PDF + Audio in a single
request, extracts/transcribes everything in parallel, plans the minimal tool
chain, executes it with a live trace, self-corrects the output, and streams a
text-only answer over Server-Sent Events.

## Architecture

```
Upload (query + files[])  ─►  Input Pipeline (parallel)
                                 ├─ text          → query doc
                                 ├─ image  (OCR)  → Tesseract conf + Gemini vision
                                 ├─ pdf    (parse)→ PyMuPDF + OCR fallback
                                 └─ audio  (STT)  → faster-whisper + duration
                                          │
                                          ▼
                              Agent Core
                                 Planner  → intent + clarify-gate + URL detection
                                          + minimal ordered plan + model routing
                                 Executor → runs steps, emits trace + timing
                                 Critic   → validates/repairs summary format
                                 Cost     → estimate (pre) vs actual (post)
                                          │
                                          ▼
                              Tool Registry (DI)
                                 summarize · sentiment · code_explain ·
                                 structured_extract · answer ·
                                 youtube_transcript · url_fetch
                                          │
                                          ▼
                              SSE stream → frontend
                              plan · step · extracted · cost_estimate ·
                              token · clarify · cost_actual · done · error
```

## Run locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then set GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Health check: `GET http://localhost:8000/health` · API docs: `/docs`.

System binaries for full functionality (bundled in the Docker image):
`tesseract-ocr` (image/PDF OCR), `poppler-utils`, `ffmpeg` (audio).

## Environment variables

| Var | Required | Default | Purpose |
|---|---|---|---|
| `GEMINI_API_KEY` | yes* | — | Google Gemini key ([AI Studio](https://aistudio.google.com/apikey)) |
| `GEMINI_MODEL_FAST` | no | `gemini-2.0-flash` | Fast model for most calls |
| `GEMINI_MODEL_PRO` | no | `gemini-1.5-pro` | Heavy/ambiguous reasoning + fallback |
| `ALLOWED_ORIGINS` | no | `http://localhost:3000` | Comma-separated CORS origins |
| `WHISPER_MODEL` | no | `base` | faster-whisper size: tiny\|base\|small\|medium |
| `MAX_FILE_MB` | no | `25` | Reject larger uploads |

\* Without a key the API still runs and uses deterministic heuristic fallbacks
(useful for tests/demo), but answer quality is limited.

## API

`POST /chat` — multipart form: `query` (string) + `files` (repeatable file
field). Returns `text/event-stream`. Event types: `plan`, `step`, `extracted`,
`cost_estimate`, `token`, `clarify`, `cost_actual`, `done`, `error`.

## Tests & lint

```bash
pytest          # offline — exercises planner, clarify-gate, and sample cases
ruff check .
```

## Deploy (Render, Docker)

`render.yaml` defines a Docker web service rooted at `backend/`. Create a new
Blueprint in Render pointing at the repo, then set `GEMINI_API_KEY` and
`ALLOWED_ORIGINS` (your Vercel URL) as environment variables. Health check path
is `/health`.
