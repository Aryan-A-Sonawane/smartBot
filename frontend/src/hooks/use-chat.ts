"use client";

// Central chat state: sessions (left rail), the active conversation, sending a
// message, and applying the agent's streamed events to the assistant message.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  AgentEvents,
  Attachment,
  ExtractedDoc,
  Message,
  Session,
  TraceStep,
} from "@/lib/types";
import { runAgent } from "@/lib/api";
import { uid } from "@/lib/utils";

const STORAGE_KEY = "smartbot.chats.v1";

function newSession(): Session {
  return { id: uid("sess"), title: "New chat", messages: [], createdAt: Date.now() };
}

// Strip fields that can't (or shouldn't) be persisted: raw File blobs and the
// transient streaming flag. Everything else round-trips through localStorage.
function serializeSessions(sessions: Session[]) {
  return sessions.map((s) => ({
    ...s,
    messages: s.messages.map((m) => ({
      ...m,
      streaming: false,
      attachments: m.attachments?.map((a) => ({
        id: a.id,
        name: a.name,
        size: a.size,
        kind: a.kind,
      })),
    })),
  }));
}

// Every document extracted so far this session, latest content per source.
// Replayed to the backend on follow-ups so the user need not re-upload.
function collectExtracted(messages: Message[]): ExtractedDoc[] {
  const bySource = new Map<string, ExtractedDoc>();
  for (const m of messages) {
    for (const d of m.extracted ?? []) {
      if (d.source !== "Text query") bySource.set(d.source, d);
    }
  }
  return [...bySource.values()];
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
  const [hydrated, setHydrated] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const active = useMemo(
    () => sessions.find((s) => s.id === activeId) ?? sessions[0],
    [sessions, activeId],
  );

  // Load persisted chats once on mount (client only). Gating the save effect on
  // `hydrated` avoids clobbering stored chats with the initial default.
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const saved = raw ? (JSON.parse(raw) as { sessions?: Session[]; activeId?: string }) : null;
      if (saved?.sessions?.length) {
        const restored = saved.sessions.map((s) => ({
          ...s,
          messages: (s.messages ?? []).map((m) => ({ ...m, streaming: false })),
        }));
        setSessions(restored);
        setActiveId(
          saved.activeId && restored.some((s) => s.id === saved.activeId)
            ? saved.activeId
            : restored[0].id,
        );
      }
    } catch {
      // corrupt storage — fall back to a fresh chat
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ activeId, sessions: serializeSessions(sessions) }),
      );
    } catch {
      // ignore quota / serialization errors
    }
  }, [sessions, activeId, hydrated]);

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

  const deleteChat = useCallback(
    (id: string) => {
      // Abort a run in progress if we're deleting the chat it belongs to.
      if (id === activeId && isRunning) {
        abortRef.current?.abort();
        abortRef.current = null;
        setIsRunning(false);
      }
      const remaining = sessions.filter((s) => s.id !== id);
      const next = remaining.length ? remaining : [newSession()];
      setSessions(next);
      if (id === activeId) setActiveId(next[0].id);
    },
    [sessions, activeId, isRunning],
  );

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

      // A clarify question is about the file(s) just provided. If the user
      // answers it with text but no new attachment, re-use those file(s) so the
      // answer applies to them — not to some earlier document in the chat.
      let effective = attachments;
      if (attachments.length === 0) {
        const msgs = active.messages;
        const lastAssistant = [...msgs].reverse().find((m) => m.role === "assistant");
        if (lastAssistant?.needsClarification) {
          const idx = msgs.findIndex((m) => m.id === lastAssistant.id);
          for (let i = idx - 1; i >= 0; i--) {
            const held = msgs[i].role === "user" ? msgs[i].attachments?.filter((a) => a.file) : undefined;
            if (held?.length) {
              effective = held;
              break;
            }
          }
        }
      }

      const priorContext = collectExtracted(active.messages);
      const userMsg: Message = {
        id: uid("msg"),
        role: "user",
        content: query,
        attachments: effective,
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
                title: s.messages.length === 0 ? deriveTitle(query, effective) : s.title,
                messages: [...s.messages, userMsg, assistantMsg],
              },
        ),
      );

      setIsRunning(true);
      const controller = new AbortController();
      abortRef.current = controller;
      const upd = (fn: (m: Message) => Message) => updateMessage(sid, assistantId, fn);

      const events: AgentEvents = {
        onPlan: (steps, intent, goal) =>
          upd((m) => ({ ...m, trace: steps, intent, goal })),
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
        onSuggestions: (questions) => upd((m) => ({ ...m, suggestions: questions })),
        onError: (message) => upd((m) => ({ ...m, error: message, streaming: false })),
        onDone: () => {
          upd((m) => ({ ...m, streaming: false }));
          setIsRunning(false);
          abortRef.current = null;
        },
      };

      await runAgent({ query, attachments: effective, priorContext }, events, controller.signal);
    },
    [active, activeId, isRunning, updateMessage],
  );

  return { sessions, activeId, active, isRunning, send, stop, newChat, selectChat, deleteChat };
}
