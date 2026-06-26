// src/lib/types.ts

// A file the user attaches to a message.
// `file` is the raw browser File object we'll later send to the backend.
export type AttachmentKind = "image" | "pdf" | "audio" | "other";

export type Attachment = {
  id: string;
  name: string;
  size: number;
  kind: AttachmentKind;
  file?: File; // optional so mock/sample messages can omit the real blob
};

// Lifecycle of one step in the agent's plan.
export type StepStatus = "pending" | "running" | "done" | "error";

// Machine names of the tools the agent can chain.
export type ToolName =
  | "image_ocr"
  | "pdf_extract"
  | "audio_transcribe"
  | "youtube_transcript"
  | "url_fetch"
  | "summarize"
  | "sentiment"
  | "code_explain"
  | "structured_extract"
  | "answer"
  | "compose";

// One step in the agent's tool chain — powers the trace list AND the graph.
export type TraceStep = {
  id: string;
  tool: ToolName;
  label: string; // human-readable, e.g. "Extract PDF text"
  rationale?: string; // the "why this tool" one-liner
  status: StepStatus;
  durationMs?: number;
};

// Text pulled from a single input — shown in the Extracted Text panel.
export type ExtractedDoc = {
  source: string; // filename or "Text query"
  kind: AttachmentKind | "text";
  content: string;
  ocrConfidence?: number; // 0..1, only when OCR ran
};

// Cost estimate vs actuals — shown in the Cost panel.
export type CostInfo = {
  estimatedUsd?: number;
  actualUsd?: number;
  inputTokens?: number;
  outputTokens?: number;
  model?: string;
};

// One chat message.
export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string; // markdown
  attachments?: Attachment[];
  extracted?: ExtractedDoc[];
  trace?: TraceStep[];
  cost?: CostInfo;
  needsClarification?: boolean;
  streaming?: boolean; // true while tokens are still arriving
  error?: string;
  createdAt: number;
};

// A chat session (one conversation in the left rail).
export type Session = {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
};

// ---- Streaming contract between UI and agent (mock today, FastAPI later) ----
export type AgentInput = {
  query: string;
  attachments: Attachment[];
};

export type AgentEvents = {
  onPlan?: (steps: TraceStep[]) => void;
  onStepUpdate?: (step: TraceStep) => void;
  onExtracted?: (docs: ExtractedDoc[]) => void;
  onToken?: (text: string) => void;
  onCostEstimate?: (cost: CostInfo) => void;
  onCostActual?: (cost: CostInfo) => void;
  onClarify?: (question: string) => void;
  onDone?: () => void;
  onError?: (message: string) => void;
};
