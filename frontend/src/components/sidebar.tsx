"use client";

import {
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
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
};

export function Sidebar({
  sessions,
  activeId,
  open,
  onToggle,
  onSelect,
  onNew,
}: Props) {
  return (
    <aside
      className={cn(
        "flex shrink-0 flex-col border-r border-border transition-all duration-300",
        open ? "w-64" : "w-12",
      )}
    >
      <div className="flex items-center justify-between p-2">
        {open && (
          <span className="px-2 text-xs font-semibold text-muted-foreground">
            Chats
          </span>
        )}
        <Button
          variant="ghost"
          size="icon"
          aria-label={open ? "Collapse chat list" : "Expand chat list"}
          onClick={onToggle}
        >
          {open ? (
            <PanelLeftClose className="size-4" />
          ) : (
            <PanelLeftOpen className="size-4" />
          )}
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
            {sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => onSelect(s.id)}
                className={cn(
                  "flex items-center gap-2 truncate rounded-md px-2 py-2 text-left text-sm hover:bg-muted",
                  s.id === activeId && "bg-muted",
                )}
              >
                <MessageSquare className="size-4 shrink-0 text-muted-foreground" />
                <span className="truncate">{s.title}</span>
              </button>
            ))}
          </div>
        </ScrollArea>
      )}
    </aside>
  );
}
