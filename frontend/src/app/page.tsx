"use client";

import { useEffect, useRef, useState } from "react";
import { Activity, Bot, Menu, PanelRightOpen, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ModeToggle } from "@/components/mode-toggle";
import { Sidebar } from "@/components/sidebar";
import { Inspector } from "@/components/inspector";
import { FeaturesDialog } from "@/components/features-dialog";
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
  const [featuresOpen, setFeaturesOpen] = useState(false);
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

  const openInspector = () => {
    setRightOpen(true);
    if (isMobile()) setLeftOpen(false);
  };

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
        onOpenFeatures={() => setFeaturesOpen(true)}
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
            {/* Mobile: quick access to the Features showcase */}
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              aria-label="Features"
              onClick={() => setFeaturesOpen(true)}
            >
              <Sparkles className="size-4 text-primary" />
            </Button>
            <ModeToggle />
            {!rightOpen && (
              <Button
                variant="ghost"
                size="icon"
                className="hidden md:inline-flex"
                aria-label="Open agent activity"
                onClick={openInspector}
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

      {/* Mobile: sticky tab so testers discover the agent-activity panel */}
      {!rightOpen && (
        <button
          onClick={openInspector}
          aria-label="Open agent activity"
          className="fixed right-0 top-1/3 z-30 flex items-center gap-1 rounded-l-lg bg-primary py-3 pl-1 pr-1.5 text-[11px] font-semibold tracking-wide text-primary-foreground shadow-lg md:hidden"
        >
          <span className="[writing-mode:vertical-rl]">Agent activity</span>
          <Activity className="size-3.5 rotate-90" />
        </button>
      )}

      {/* RIGHT: agent transparency */}
      <Inspector messages={messages} open={rightOpen} onClose={() => setRightOpen(false)} />

      <FeaturesDialog open={featuresOpen} onClose={() => setFeaturesOpen(false)} />
    </div>
  );
}
