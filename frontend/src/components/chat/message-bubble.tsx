"use client";

import {
  AlertTriangle,
  AudioLines,
  Bot,
  FileText,
  HelpCircle,
  ImageIcon,
  File as FileIcon,
} from "lucide-react";
import { Markdown } from "@/components/chat/markdown";
import { cn } from "@/lib/utils";
import type { Attachment, AttachmentKind, Message } from "@/lib/types";

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

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex flex-col items-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-primary-foreground">
          {message.content && (
            <p className="whitespace-pre-wrap text-[15px] leading-relaxed">
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
          <ThinkingDots />
        ) : (
          <>
            <Markdown>{message.content}</Markdown>
            {message.streaming && (
              <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse rounded-sm bg-foreground/60 align-middle" />
            )}
          </>
        )}
      </div>
    </div>
  );
}

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1 py-1 text-muted-foreground">
      <span className="size-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.3s]" />
      <span className="size-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.15s]" />
      <span className="size-1.5 animate-bounce rounded-full bg-current" />
      <span className="ml-2 text-xs">Working…</span>
    </div>
  );
}
