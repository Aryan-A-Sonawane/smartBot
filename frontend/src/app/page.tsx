"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, Menu, PanelRightOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ModeToggle } from "@/components/mode-toggle";
import { Sidebar } from "@/components/sidebar";
import { Inspector } from "@/components/inspector";
import { MessageList } from "@/components/chat/message-list";
import { EmptyState } from "@/components/chat/empty-state";
import { Composer, type ComposerHandle } from "@/components/chat/composer";
import { useChat } from "@/hooks/use-chat";

const isMobile = () => typeof window !== "undefined" && window.innerWidth < 768;

export default function Home() {
  const { sessions, activeId, active, isRunning, send, stop, newChat, selectChat, deleteChat } =
    useChat();
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const composerRef = useRef<ComposerHandle>(null);

  // Start with both side panels closed on small screens (they're overlays there).
  useEffect(() => {
    if (isMobile()) {
      setLeftOpen(false);
      setRightOpen(false);
    }
  }, []);

  const messages = active.messages;
  const hasMessages = messages.length > 0;

  return (
    <div className="relative flex h-dvh overflow-hidden bg-background text-foreground">
      {/* Mobile backdrop behind an open drawer */}
      {(leftOpen || rightOpen) && (
        <button
          aria-label="Close panels"
          onClick={() => {
            setLeftOpen(false);
            setRightOpen(false);
          }}
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
        />
      )}

      {/* LEFT: chat history */}
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        open={leftOpen}
        onToggle={() => setLeftOpen((v) => !v)}
        onSelect={(id) => {
          selectChat(id);
          if (isMobile()) setLeftOpen(false);
        }}
        onNew={() => {
          newChat();
          if (isMobile()) setLeftOpen(false);
        }}
        onDelete={deleteChat}
      />

      {/* MIDDLE: chat window */}
      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border px-3 py-3 sm:px-4">
          <div className="flex min-w-0 items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              aria-label="Open chat list"
              onClick={() => setLeftOpen(true)}
            >
              <Menu className="size-4" />
            </Button>
            <Bot className="size-5 shrink-0 text-primary" />
            <span className="text-sm font-semibold">SmartBot</span>
            <span className="hidden truncate text-xs text-muted-foreground sm:inline">
              Multimodal agentic assistant
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <ModeToggle />
            {!rightOpen && (
              <Button
                variant="ghost"
                size="icon"
                aria-label="Open agent activity"
                onClick={() => {
                  setRightOpen(true);
                  if (isMobile()) setLeftOpen(false);
                }}
              >
                <PanelRightOpen className="size-4" />
              </Button>
            )}
          </div>
        </header>

        <div className="min-h-0 flex-1">
          {hasMessages ? (
            <MessageList
              messages={messages}
              onPickSuggestion={(q) => composerRef.current?.setText(q)}
            />
          ) : (
            <EmptyState
              onLoad={(q, files) => {
                composerRef.current?.setText(q);
                if (files.length) composerRef.current?.addAttachments(files);
              }}
            />
          )}
        </div>

        <div className="border-t border-border p-3">
          <Composer ref={composerRef} onSend={send} isRunning={isRunning} onStop={stop} />
        </div>
      </main>

      {/* RIGHT: agent transparency */}
      <Inspector
        messages={messages}
        open={rightOpen}
        onClose={() => setRightOpen(false)}
      />
    </div>
  );
}
