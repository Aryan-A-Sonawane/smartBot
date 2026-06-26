"use client";

import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
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

export function TracePanel({ steps }: { steps: TraceStep[] }) {
  if (!steps.length) {
    return (
      <p className="p-3 text-sm text-muted-foreground">
        The agent&apos;s plan and tool steps will appear here as it works.
      </p>
    );
  }

  return (
    <ol className="space-y-1 p-1">
      {steps.map((s, i) => (
        <li
          key={s.id}
          className={cn(
            "rounded-md p-2",
            s.status === "running" && "bg-primary/5",
          )}
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
            <p className="ml-6 mt-0.5 text-xs text-muted-foreground">
              {s.rationale}
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}
