"use client";

import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "@/components/chat/message-bubble";
import type { Message } from "@/lib/types";

export function MessageList({
  messages,
  onPickSuggestion,
}: {
  messages: Message[];
  onPickSuggestion?: (q: string) => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the latest content as tokens stream in.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} onPickSuggestion={onPickSuggestion} />
        ))}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
