"use client";

import { CheckCircle2, Circle, Loader2, Target, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Markdown } from "@/components/chat/markdown";
import { cn } from "@/lib/utils";
import type { StepStatus, TraceStep } from "@/lib/types";

function StatusIcon({ status }: { status: StepStatus }) {
  if (status === "running")
    return <Loader2 className="size-4 animate-spin text-primary" />;
  if (status === "done")
    return <CheckCircle2 className="size-4 text-emerald-500" />;
  if (status === "error") return <XCircle className="size-4 text-destructive" />;
  return <Circle className="size-4 text-muted-foreground" />;
}

export function TracePanel({ steps, goal }: { steps: TraceStep[]; goal?: string }) {
  if (!steps.length && !goal) {
    return (
      <p className="p-3 text-sm text-muted-foreground">
        The agent&apos;s understood goal and tool steps will appear here as it works.
      </p>
    );
  }

  return (
    <div className="p-1">
      {goal && (
        <div className="mb-2 flex items-start gap-2 rounded-md border border-primary/20 bg-primary/5 px-2.5 py-2">
          <Target className="mt-0.5 size-4 shrink-0 text-primary" />
          <div className="min-w-0 text-xs leading-relaxed">
            <span className="font-medium text-foreground">Understood goal</span>
            <div className="break-words text-muted-foreground [&_p]:m-0 [&_strong]:text-foreground">
              <Markdown>{goal}</Markdown>
            </div>
          </div>
        </div>
      )}
      <ol className="space-y-1">
        {steps.map((s, i) => (
          <li
            key={s.id}
            className={cn("rounded-md p-2", s.status === "running" && "bg-primary/5")}
          >
            <div className="flex items-center gap-2">
              <StatusIcon status={s.status} />
              <span className="text-xs font-medium text-muted-foreground">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="text-sm font-medium">{s.label}</span>
              <code className="text-[11px] text-muted-foreground">{s.tool}</code>
              {s.durationMs != null && (
                <Badge variant="secondary" className="ml-auto text-[10px]">
                  {s.durationMs} ms
                </Badge>
              )}
            </div>
            {s.rationale && (
              <p className="ml-6 mt-0.5 break-words text-xs text-muted-foreground">{s.rationale}</p>
            )}
            {s.detail && (
              <p
                className={cn(
                  "ml-6 mt-0.5 break-words text-xs",
                  s.status === "error" ? "text-destructive" : "text-foreground/70",
                )}
              >
                <span className="text-muted-foreground">→ </span>
                {s.detail}
              </p>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
