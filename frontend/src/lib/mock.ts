// src/lib/mock.ts
// A self-contained mock of the agent so the whole UI works before the
// Python backend exists. It mimics the real streaming contract: plan ->
// step updates -> extracted docs -> cost estimate -> token stream -> actual cost.

import type {
  AgentEvents,
  AgentInput,
  CostInfo,
  ExtractedDoc,
  StepStatus,
  ToolName,
  TraceStep,
} from "@/lib/types";
import {
  estimateTokens,
  findUrl,
  isYouTube,
  sleep,
  uid,
} from "@/lib/utils";

// Rough Gemini 2.0 Flash pricing (USD per 1M tokens) for the estimator.
const PRICE = { model: "gemini-2.0-flash", in: 0.075, out: 0.3 };

type Intent =
  | "summarize"
  | "sentiment"
  | "code_explain"
  | "structured_extract"
  | "answer";

function detectIntent(query: string): Intent {
  const q = query.toLowerCase();
  if (/(summar|tl;?dr|gist|recap)/.test(q)) return "summarize";
  if (/(sentiment|tone|feel|positive|negative|emotion)/.test(q)) return "sentiment";
  if (/(explain|bug|complexity|code|function|refactor)/.test(q)) return "code_explain";
  if (/(action item|extract|table|entit|key points|fields)/.test(q))
    return "structured_extract";
  return "answer";
}

function step(tool: ToolName, label: string, rationale: string): TraceStep {
  return { id: uid("step"), tool, label, rationale, status: "pending" };
}

// Build extracted docs for the attachments (simulated OCR/parse/transcription).
function buildExtracted(input: AgentInput): ExtractedDoc[] {
  const docs: ExtractedDoc[] = [];
  for (const a of input.attachments) {
    if (a.kind === "image") {
      docs.push({
        source: a.name,
        kind: "image",
        ocrConfidence: 0.93,
        content:
          "def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i\n# (OCR-extracted from screenshot — mock)",
      });
    } else if (a.kind === "pdf") {
      docs.push({
        source: a.name,
        kind: "pdf",
        content:
          "Meeting notes — Q3 planning.\nAttendees: A. Sonawane, team.\nDiscussion covered roadmap and a demo video: https://youtu.be/dQw4w9WgXcQ\nAction items:\n- Aryan to finalize the agent design by Friday\n- Team to review the deployment plan\n- Schedule follow-up next week\n(parsed from PDF — mock)",
      });
    } else if (a.kind === "audio") {
      docs.push({
        source: a.name,
        kind: "audio",
        content:
          "Welcome to today's lecture on retrieval-augmented generation. We'll cover embeddings, vector stores, and how agents chain tools to answer multi-step questions… (transcribed — mock)",
      });
    }
  }
  return docs;
}

export async function runAgentMock(
  input: AgentInput,
  ev: AgentEvents,
  signal?: AbortSignal,
): Promise<void> {
  const aborted = () => signal?.aborted;

  try {
    // ---- Mandatory follow-up rule: ambiguous request -> ask, don't guess ----
    const hasFiles = input.attachments.length > 0;
    const hasQuery = input.query.trim().length > 0;

    if (hasFiles && !hasQuery) {
      await sleep(400);
      ev.onClarify?.(
        "I can see your file(s). What would you like me to do — **summarize**, **analyze sentiment**, **explain code**, or **extract the text**?",
      );
      ev.onDone?.();
      return;
    }

    // ---- Plan the minimal tool chain ----
    const plan: TraceStep[] = [];
    const kinds = new Set(input.attachments.map((a) => a.kind));

    if (kinds.has("image"))
      plan.push(step("image_ocr", "OCR image", "Image attached — extract text via OCR."));
    if (kinds.has("pdf"))
      plan.push(step("pdf_extract", "Parse PDF", "PDF attached — extract text (OCR fallback if scanned)."));
    if (kinds.has("audio"))
      plan.push(step("audio_transcribe", "Transcribe audio", "Audio attached — run speech-to-text."));

    // URL detection across query + (simulated) extracted content.
    const extracted = buildExtracted(input);
    const haystack = input.query + "\n" + extracted.map((d) => d.content).join("\n");
    const url = findUrl(haystack);
    if (url && isYouTube(url)) {
      plan.push(step("youtube_transcript", "Fetch YouTube transcript", `Detected a YouTube link (${url}) — fetch its transcript.`));
    } else if (url) {
      plan.push(step("url_fetch", "Fetch URL", `Detected a link (${url}) — fetch and read the page.`));
    }

    const intent = detectIntent(input.query);
    const intentStep: Record<Intent, TraceStep> = {
      summarize: step("summarize", "Summarize", "User asked for a summary — produce 1-line + 3 bullets + 5 sentences."),
      sentiment: step("sentiment", "Analyze sentiment", "User asked for sentiment — label + confidence + justification."),
      code_explain: step("code_explain", "Explain code", "Code detected — explain, flag bugs, note time complexity."),
      structured_extract: step("structured_extract", "Extract structured data", "User asked for structured items — pull action items / tables."),
      answer: step("answer", "Answer", "Answer the question using the combined context."),
    };
    plan.push(intentStep[intent]);
    plan.push(step("compose", "Compose response", "Format the final text-only answer."));

    ev.onPlan?.(plan);

    // ---- Cost estimate (before execution) ----
    const inputTokens = estimateTokens(haystack) + 400; // + system/tool overhead
    const estCost: CostInfo = {
      model: PRICE.model,
      inputTokens,
      outputTokens: 350,
      estimatedUsd: (inputTokens * PRICE.in + 350 * PRICE.out) / 1_000_000,
    };
    ev.onCostEstimate?.(estCost);

    // ---- Execute steps with live status + timing ----
    let extractedEmitted = false;
    for (const s of plan) {
      if (aborted()) return;
      const started = Date.now();
      ev.onStepUpdate?.({ ...s, status: "running" as StepStatus });
      await sleep(450 + Math.random() * 500);
      if (aborted()) return;
      ev.onStepUpdate?.({ ...s, status: "done", durationMs: Date.now() - started });

      // Reveal extracted text once extraction-type steps have run.
      const extractionTools: ToolName[] = [
        "image_ocr",
        "pdf_extract",
        "audio_transcribe",
        "youtube_transcript",
        "url_fetch",
      ];
      if (!extractedEmitted && extractionTools.includes(s.tool) && extracted.length) {
        ev.onExtracted?.(extracted);
        extractedEmitted = true;
      }
    }
    if (extracted.length && !extractedEmitted) ev.onExtracted?.(extracted);

    // ---- Stream the answer token-by-token ----
    const answer = composeAnswer(intent, input, !!url && isYouTube(url));
    const tokens = answer.match(/\S+\s*/g) ?? [answer];
    for (const t of tokens) {
      if (aborted()) return;
      ev.onToken?.(t);
      await sleep(18 + Math.random() * 22);
    }

    // ---- Actual cost (after execution) ----
    const outputTokens = estimateTokens(answer);
    ev.onCostActual?.({
      model: PRICE.model,
      inputTokens,
      outputTokens,
      actualUsd: (inputTokens * PRICE.in + outputTokens * PRICE.out) / 1_000_000,
    });

    ev.onDone?.();
  } catch (e) {
    ev.onError?.(e instanceof Error ? e.message : "Mock agent failed");
  }
}

function composeAnswer(
  intent: Intent,
  input: AgentInput,
  youtube: boolean,
): string {
  const subject =
    input.attachments[0]?.name ??
    (input.query.length > 40 ? input.query.slice(0, 40) + "…" : input.query);

  if (intent === "summarize" || youtube) {
    return [
      `**One-line summary:** ${youtube ? "The linked video" : `"${subject}"`} explains how agentic systems chain tools to answer multi-step questions.`,
      ``,
      `**Key points**`,
      `- Inputs are extracted/transcribed first, then reasoned over together.`,
      `- A planner picks the minimal sequence of tools for the goal.`,
      `- Outputs are formatted as a clean, text-only response.`,
      ``,
      `**5-sentence summary**`,
      `The content introduces the idea of an agent that accepts multiple input types at once. It extracts text from images and PDFs and transcribes audio before reasoning. A planning step decides which tools to chain for the user's actual goal. Cross-input references, such as a URL inside a PDF, are resolved automatically. The result is a single, coherent answer assembled from every source.`,
    ].join("\n");
  }

  if (intent === "sentiment") {
    return [
      `**Sentiment:** Positive`,
      `**Confidence:** 0.88`,
      ``,
      `**Why:** The language leans optimistic and solution-oriented, with few negative markers.`,
    ].join("\n");
  }

  if (intent === "code_explain") {
    return [
      `**What it does:** This is a classic two-sum — it returns the indices of the two numbers that add up to \`target\` using a hash map for O(1) lookups.`,
      ``,
      `**Walkthrough**`,
      `- It iterates once, storing each value's index in \`seen\`.`,
      `- For each number it checks whether \`target - n\` was already seen.`,
      ``,
      `**Bugs / edge cases:** Returns nothing if no pair exists (caller should handle \`None\`); assumes exactly one valid answer.`,
      ``,
      `**Time complexity:** O(n) time, O(n) space.`,
    ].join("\n");
  }

  if (intent === "structured_extract") {
    return [
      `**Action items**`,
      `- Aryan to finalize the agent design by **Friday**.`,
      `- Team to review the deployment plan.`,
      `- Schedule a follow-up next week.`,
    ].join("\n");
  }

  return [
    `Here's what I found across your input${input.attachments.length ? "s" : ""}: ${
      input.query || "your request"
    }.`,
    ``,
    `I combined the available context and produced this text-only answer. Ask a follow-up and I'll build on what's already extracted.`,
  ].join("\n");
}
