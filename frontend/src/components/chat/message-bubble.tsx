"use client";

import {
  AlertTriangle,
  ArrowUpRight,
  AudioLines,
  Bot,
  FileText,
  HelpCircle,
  ImageIcon,
  Loader2,
  File as FileIcon,
} from "lucide-react";
import { Markdown } from "@/components/chat/markdown";
import { cn } from "@/lib/utils";
import type { Attachment, AttachmentKind, Message, TraceStep } from "@/lib/types";

const KIND_ICON: Record<AttachmentKind, typeof FileIcon> = {
  image: ImageIcon,
  pdf: FileText,
  audio: AudioLines,
  other: FileIcon,
};

function AttachmentChips({ items }: { items: Attachment[] }) {
  return (
    <div className="mt-2 flex flex-wrap justify-end gap-2">
      {items.map((a) => {
        const Icon = KIND_ICON[a.kind];
        return (
          <div
            key={a.id}
            className="flex items-center gap-1.5 rounded-lg border border-border bg-background px-2 py-1 text-xs"
          >
            <Icon className="size-3.5 text-muted-foreground" />
            <span className="max-w-[160px] truncate">{a.name}</span>
          </div>
        );
      })}
    </div>
  );
}

export function MessageBubble({
  message,
  onPickSuggestion,
}: {
  message: Message;
  onPickSuggestion?: (q: string) => void;
}) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex flex-col items-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-primary-foreground">
          {message.content && (
            <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed">
              {message.content}
            </p>
          )}
        </div>
        {message.attachments && message.attachments.length > 0 && (
          <AttachmentChips items={message.attachments} />
        )}
      </div>
    );
  }

  // Assistant
  const thinking = message.streaming && !message.content;

  return (
    <div className="flex gap-3">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted">
        <Bot className="size-4 text-primary" />
      </div>

      <div className="min-w-0 flex-1 pt-1">
        {message.error ? (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <span>{message.error}</span>
          </div>
        ) : message.needsClarification ? (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2">
            <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-amber-600 dark:text-amber-400">
              <HelpCircle className="size-3.5" />
              Needs clarification
            </div>
            <Markdown>{message.content}</Markdown>
          </div>
        ) : thinking ? (
          <StatusLine step={currentStage(message)} />
        ) : (
          <>
            <Markdown>{message.content}</Markdown>
            {message.streaming && (
              <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse rounded-sm bg-foreground/60 align-middle" />
            )}
          </>
        )}

        {!message.streaming &&
          !message.error &&
          message.suggestions &&
          message.suggestions.length > 0 && (
            <div className="mt-3 flex flex-col items-start gap-1.5">
              <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Suggested follow-ups
              </span>
              {message.suggestions.map((q) => (
                <button
                  key={q}
                  onClick={() => onPickSuggestion?.(q)}
                  className="group flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1 text-left text-xs text-foreground/80 transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
                >
                  <ArrowUpRight className="size-3.5 shrink-0 text-muted-foreground group-hover:text-primary" />
                  {q}
                </button>
              ))}
            </div>
          )}
      </div>
    </div>
  );
}

// The stage the agent is currently on (or the last one), for the live status.
function currentStage(message: Message): TraceStep | undefined {
  const trace = message.trace ?? [];
  return [...trace].reverse().find((s) => s.status === "running") ?? trace[trace.length - 1];
}

// A live "thinking" line that names the actual pipeline stage in progress —
// e.g. "Running pdf_extract…", "Refine / self-check…" — instead of a spinner.
function StatusLine({ step }: { step?: TraceStep }) {
  const label = !step
    ? "Working…"
    : step.status === "running"
      ? `Running ${step.tool}…`
      : `${step.label}…`;
  return (
    <div className="flex items-center gap-2 py-1 text-sm text-muted-foreground">
      <Loader2 className="size-4 shrink-0 animate-spin text-primary" />
      <span className="font-medium">{label}</span>
      {step?.detail && (
        <span className="hidden truncate text-xs opacity-70 sm:inline">· {step.detail}</span>
      )}
    </div>
  );
}
