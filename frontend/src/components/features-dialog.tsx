"use client";

import { useEffect } from "react";
import {
  Activity,
  CheckCircle2,
  Compass,
  GitCompare,
  Layers,
  MessagesSquare,
  Search,
  Sparkles,
  X,
  Zap,
} from "lucide-react";

type Feature = { icon: typeof Layers; title: string; desc: string };

const FEATURES: Feature[] = [
  {
    icon: Layers,
    title: "True multimodal",
    desc: "Text, images, PDFs and audio — several at once — extracted in parallel with OCR, Gemini vision, and speech-to-text.",
  },
  {
    icon: Compass,
    title: "Autonomous agent",
    desc: "An LLM understands your intent and which inputs matter, then plans and chains the right tools — not brittle keyword rules.",
  },
  {
    icon: Search,
    title: "RAG with citations",
    desc: "Ask questions over long documents: dense-vector retrieval pulls the relevant passages and cites the exact page.",
  },
  {
    icon: GitCompare,
    title: "Cross-input reasoning",
    desc: "Compare a PDF against an audio clip, or follow a YouTube link found inside a document — it reasons across everything.",
  },
  {
    icon: CheckCircle2,
    title: "Self-correcting",
    desc: "A critic checks each answer against its format contract and repairs it once — consistent, reliable output.",
  },
  {
    icon: Activity,
    title: "Full transparency",
    desc: "Watch every stage live — plan trace, tool graph, extracted text, and token cost. Nothing is a black box.",
  },
  {
    icon: MessagesSquare,
    title: "Memory & suggestions",
    desc: "Keeps your documents in context across follow-ups and proposes smart next questions, like a modern assistant.",
  },
  {
    icon: Zap,
    title: "Streaming & robust",
    desc: "Answers stream token-by-token, degrade gracefully on bad inputs, and even work offline with heuristic fallbacks.",
  },
];

export function FeaturesDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-label="Features"
    >
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div className="relative flex max-h-[88dvh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-border bg-background shadow-2xl">
        <div className="flex items-start justify-between gap-3 border-b border-border px-4 py-4 sm:px-6 sm:py-5">
          <div className="flex min-w-0 items-start gap-3">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Sparkles className="size-5" />
            </span>
            <div className="min-w-0">
              <h2 className="text-base font-semibold leading-snug sm:text-lg">
                What makes SmartBot special
              </h2>
              <p className="mt-0.5 text-xs text-muted-foreground sm:text-sm">
                A deployed, agentic multimodal assistant.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="-mr-1 shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <X className="size-5" />
          </button>
        </div>

        <div className="grid gap-3 overflow-y-auto p-4 sm:grid-cols-2 sm:p-5">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/40"
              >
                <div className="flex items-center gap-2.5">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="size-5" />
                  </span>
                  <h3 className="font-medium">{f.title}</h3>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
