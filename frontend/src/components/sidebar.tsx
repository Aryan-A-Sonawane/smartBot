"use client";

import { useState } from "react";
import {
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { Session } from "@/lib/types";

type Props = {
  sessions: Session[];
  activeId: string;
  open: boolean;
  onToggle: () => void;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
};

export function Sidebar({
  sessions,
  activeId,
  open,
  onToggle,
  onSelect,
  onNew,
  onDelete,
}: Props) {
  // Which chat is currently showing its "Delete this chat?" confirmation.
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  return (
    <aside
      className={cn(
        "z-40 flex shrink-0 flex-col border-r border-border bg-background",
        // Mobile: off-canvas drawer that slides in.
        "fixed inset-y-0 left-0 w-72 max-w-[80%] transition-transform duration-300",
        // Desktop: inline column that toggles between full and collapsed width.
        "md:static md:z-auto md:max-w-none md:translate-x-0 md:transition-[width]",
        open ? "translate-x-0 md:w-64" : "-translate-x-full md:w-12",
      )}
    >
      <div className="flex items-center justify-between p-2">
        {open && (
          <span className="px-2 text-xs font-semibold text-muted-foreground">Chats</span>
        )}
        <Button
          variant="ghost"
          size="icon"
          aria-label={open ? "Collapse chat list" : "Expand chat list"}
          onClick={onToggle}
        >
          {open ? <PanelLeftClose className="size-4" /> : <PanelLeftOpen className="size-4" />}
        </Button>
      </div>

      <div className="px-2">
        <Button
          variant="outline"
          onClick={onNew}
          className={open ? "w-full justify-start gap-2" : "w-8 px-0"}
          size={open ? "default" : "icon"}
          aria-label="New chat"
        >
          <Plus className="size-4" />
          {open && "New chat"}
        </Button>
      </div>

      {open && (
        <ScrollArea className="mt-2 flex-1 px-2">
          <div className="flex flex-col gap-1 pb-2">
            {sessions.map((s) => {
              const confirming = confirmingId === s.id;
              return (
                <div
                  key={s.id}
                  className={cn(
                    "group flex items-center rounded-md pr-1 hover:bg-muted",
                    s.id === activeId && "bg-muted",
                  )}
                >
                  {confirming ? (
                    <div className="flex flex-1 items-center gap-1 px-2 py-1.5">
                      <span className="flex-1 truncate text-xs text-muted-foreground">
                        Delete this chat?
                      </span>
                      <button
                        onClick={() => {
                          onDelete(s.id);
                          setConfirmingId(null);
                        }}
                        className="rounded px-1.5 py-0.5 text-xs font-medium text-destructive hover:bg-destructive/10"
                      >
                        Delete
                      </button>
                      <button
                        onClick={() => setConfirmingId(null)}
                        className="rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-foreground/10"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={() => onSelect(s.id)}
                        className="flex min-w-0 flex-1 items-center gap-2 px-2 py-2 text-left text-sm"
                      >
                        <MessageSquare className="size-4 shrink-0 text-muted-foreground" />
                        <span className="min-w-0 flex-1 truncate">{s.title}</span>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setConfirmingId(s.id);
                        }}
                        aria-label={`Delete chat: ${s.title}`}
                        title="Delete chat"
                        className="shrink-0 rounded p-1 text-muted-foreground/60 transition-colors hover:bg-destructive/10 hover:text-destructive"
                      >
                        <Trash2 className="size-4" />
                      </button>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </ScrollArea>
      )}
    </aside>
  );
}
