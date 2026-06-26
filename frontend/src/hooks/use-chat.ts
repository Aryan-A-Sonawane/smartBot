"use client";

// Central chat state: sessions (left rail), the active conversation, sending a
// message, and applying the agent's streamed events to the assistant message.

import { useCallback, useMemo, useRef, useState } from "react";
import type {
  AgentEvents,
  Attachment,
  Message,
  Session,
  TraceStep,
} from "@/lib/types";
import { runAgent } from "@/lib/api";
import { uid } from "@/lib/utils";

function newSession(): Session {
  return { id: uid("sess"), title: "New chat", messages: [], createdAt: Date.now() };
}

function deriveTitle(query: string, attachments: Attachment[]): string {
  const q = query.trim();
  if (q) return q.length > 40 ? q.slice(0, 40) + "…" : q;
  if (attachments[0]) return attachments[0].name;
  return "New chat";
}

function mergeStep(steps: TraceStep[], step: TraceStep): TraceStep[] {
  const idx = steps.findIndex((s) => s.id === step.id);
  if (idx === -1) return [...steps, step];
  const next = steps.slice();
  next[idx] = { ...next[idx], ...step };
  return next;
}

export function useChat() {
  const [sessions, setSessions] = useState<Session[]>(() => [newSession()]);
  const [activeId, setActiveId] = useState<string>(() => sessions[0].id);
  const [isRunning, setIsRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const active = useMemo(
    () => sessions.find((s) => s.id === activeId) ?? sessions[0],
    [sessions, activeId],
  );

  const updateMessage = useCallback(
    (sid: string, mid: string, updater: (m: Message) => Message) => {
      setSessions((prev) =>
        prev.map((s) =>
          s.id !== sid
            ? s
            : { ...s, messages: s.messages.map((m) => (m.id === mid ? updater(m) : m)) },
        ),
      );
    },
    [],
  );

  const newChat = useCallback(() => {
    const s = newSession();
    setSessions((prev) => [s, ...prev]);
    setActiveId(s.id);
  }, []);

  const selectChat = useCallback((id: string) => setActiveId(id), []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsRunning(false);
    setSessions((prev) =>
      prev.map((s) => ({
        ...s,
        messages: s.messages.map((m) =>
          m.streaming ? { ...m, streaming: false } : m,
        ),
      })),
    );
  }, []);

  const send = useCallback(
    async (query: string, attachments: Attachment[]) => {
      if (isRunning) return;
      if (!query.trim() && attachments.length === 0) return;

      const sid = activeId;
      const userMsg: Message = {
        id: uid("msg"),
        role: "user",
        content: query,
        attachments,
        createdAt: Date.now(),
      };
      const assistantId = uid("msg");
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        trace: [],
        streaming: true,
        createdAt: Date.now(),
      };

      setSessions((prev) =>
        prev.map((s) =>
          s.id !== sid
            ? s
            : {
                ...s,
                title: s.messages.length === 0 ? deriveTitle(query, attachments) : s.title,
                messages: [...s.messages, userMsg, assistantMsg],
              },
        ),
      );

      setIsRunning(true);
      const controller = new AbortController();
      abortRef.current = controller;
      const upd = (fn: (m: Message) => Message) => updateMessage(sid, assistantId, fn);

      const events: AgentEvents = {
        onPlan: (steps) => upd((m) => ({ ...m, trace: steps })),
        onStepUpdate: (step) =>
          upd((m) => ({ ...m, trace: mergeStep(m.trace ?? [], step) })),
        onExtracted: (docs) => upd((m) => ({ ...m, extracted: docs })),
        onToken: (text) => upd((m) => ({ ...m, content: m.content + text })),
        onCostEstimate: (cost) => upd((m) => ({ ...m, cost: { ...m.cost, ...cost } })),
        onCostActual: (cost) => upd((m) => ({ ...m, cost: { ...m.cost, ...cost } })),
        onClarify: (question) =>
          upd((m) => ({
            ...m,
            content: question,
            needsClarification: true,
            streaming: false,
          })),
        onError: (message) => upd((m) => ({ ...m, error: message, streaming: false })),
        onDone: () => {
          upd((m) => ({ ...m, streaming: false }));
          setIsRunning(false);
          abortRef.current = null;
        },
      };

      await runAgent({ query, attachments }, events, controller.signal);
    },
    [activeId, isRunning, updateMessage],
  );

  return { sessions, activeId, active, isRunning, send, stop, newChat, selectChat };
}
