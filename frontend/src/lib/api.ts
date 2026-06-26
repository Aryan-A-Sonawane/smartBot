// src/lib/api.ts
// Single entry point the UI uses to run the agent. If NEXT_PUBLIC_API_URL is
// set we stream from the FastAPI backend (SSE); otherwise we fall back to the
// in-browser mock so the app is fully usable during frontend development.

import type { AgentEvents, AgentInput, CostInfo, ExtractedDoc, TraceStep } from "@/lib/types";
import { runAgentMock } from "@/lib/mock";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export function isMock(): boolean {
  return !API_URL;
}

export async function runAgent(
  input: AgentInput,
  ev: AgentEvents,
  signal?: AbortSignal,
): Promise<void> {
  if (!API_URL) return runAgentMock(input, ev, signal);
  return runAgentReal(API_URL, input, ev, signal);
}

// ---- Real backend: POST multipart, read an SSE stream of typed events ----
// Backend contract (to implement in FastAPI): POST {API_URL}/chat with
// FormData { query, files[] } returning text/event-stream of lines:
//   data: {"type":"plan","steps":[...]}
//   data: {"type":"step","step":{...}}
//   data: {"type":"extracted","docs":[...]}
//   data: {"type":"cost_estimate","cost":{...}}
//   data: {"type":"token","text":"..."}
//   data: {"type":"clarify","question":"..."}
//   data: {"type":"cost_actual","cost":{...}}
//   data: {"type":"done"}
//   data: {"type":"error","message":"..."}

type ServerEvent =
  | { type: "plan"; steps: TraceStep[] }
  | { type: "step"; step: TraceStep }
  | { type: "extracted"; docs: ExtractedDoc[] }
  | { type: "cost_estimate"; cost: CostInfo }
  | { type: "cost_actual"; cost: CostInfo }
  | { type: "token"; text: string }
  | { type: "clarify"; question: string }
  | { type: "done" }
  | { type: "error"; message: string };

async function runAgentReal(
  baseUrl: string,
  input: AgentInput,
  ev: AgentEvents,
  signal?: AbortSignal,
): Promise<void> {
  try {
    const form = new FormData();
    form.append("query", input.query);
    for (const a of input.attachments) {
      if (a.file) form.append("files", a.file, a.name);
    }

    const res = await fetch(`${baseUrl.replace(/\/$/, "")}/chat`, {
      method: "POST",
      body: form,
      signal,
    });

    if (!res.ok || !res.body) {
      throw new Error(`Backend error ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line.
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        const line = frame.split("\n").find((l) => l.startsWith("data:"));
        if (!line) continue;
        const json = line.slice(5).trim();
        if (!json) continue;
        dispatch(JSON.parse(json) as ServerEvent, ev);
      }
    }
    ev.onDone?.();
  } catch (e) {
    if ((e as Error).name === "AbortError") return;
    ev.onError?.(e instanceof Error ? e.message : "Request failed");
  }
}

function dispatch(event: ServerEvent, ev: AgentEvents): void {
  switch (event.type) {
    case "plan":
      ev.onPlan?.(event.steps);
      break;
    case "step":
      ev.onStepUpdate?.(event.step);
      break;
    case "extracted":
      ev.onExtracted?.(event.docs);
      break;
    case "cost_estimate":
      ev.onCostEstimate?.(event.cost);
      break;
    case "cost_actual":
      ev.onCostActual?.(event.cost);
      break;
    case "token":
      ev.onToken?.(event.text);
      break;
    case "clarify":
      ev.onClarify?.(event.question);
      break;
    case "error":
      ev.onError?.(event.message);
      break;
    case "done":
      ev.onDone?.();
      break;
  }
}
