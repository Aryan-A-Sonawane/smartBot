"use client";

import { useMemo, useRef, useState } from "react";
import { Bot, PanelRightOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ModeToggle } from "@/components/mode-toggle";
import { Sidebar } from "@/components/sidebar";
import { Inspector } from "@/components/inspector";
import { MessageList } from "@/components/chat/message-list";
import { EmptyState } from "@/components/chat/empty-state";
import { Composer, type ComposerHandle } from "@/components/chat/composer";
import { useChat } from "@/hooks/use-chat";

export default function Home() {
  const { sessions, activeId, active, isRunning, send, stop, newChat, selectChat } =
    useChat();
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const composerRef = useRef<ComposerHandle>(null);

  const messages = active.messages;
  const hasMessages = messages.length > 0;

  // The most recent assistant message drives the inspector panels.
  const latestAssistant = useMemo(
    () => [...messages].reverse().find((m) => m.role === "assistant"),
    [messages],
  );

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      {/* LEFT: chat history */}
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        open={leftOpen}
        onToggle={() => setLeftOpen((v) => !v)}
        onSelect={selectChat}
        onNew={newChat}
      />

      {/* MIDDLE: chat window */}
      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <Bot className="size-5 text-primary" />
            <span className="text-sm font-semibold">SmartBot</span>
            <span className="hidden text-xs text-muted-foreground sm:inline">
              Multimodal agentic assistant
            </span>
          </div>
          <div className="flex items-center gap-1">
            <ModeToggle />
            {!rightOpen && (
              <Button
                variant="ghost"
                size="icon"
                aria-label="Open panels"
                onClick={() => setRightOpen(true)}
              >
                <PanelRightOpen className="size-4" />
              </Button>
            )}
          </div>
        </header>

        <div className="min-h-0 flex-1">
          {hasMessages ? (
            <MessageList messages={messages} />
          ) : (
            <EmptyState onPick={(q) => composerRef.current?.setText(q)} />
          )}
        </div>

        <div className="border-t border-border p-3">
          <Composer
            ref={composerRef}
            onSend={send}
            isRunning={isRunning}
            onStop={stop}
          />
        </div>
      </main>

      {/* RIGHT: agent transparency */}
      <Inspector
        message={latestAssistant}
        open={rightOpen}
        onClose={() => setRightOpen(false)}
      />
    </div>
  );
}
