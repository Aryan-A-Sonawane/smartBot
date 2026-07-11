"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  Position,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { StepStatus, TraceStep } from "@/lib/types";

// Map a step status to node colors (uses theme CSS variables).
function nodeStyle(status: StepStatus): React.CSSProperties {
  const base: React.CSSProperties = {
    borderRadius: 10,
    padding: "8px 10px",
    fontSize: 12,
    border: "1px solid var(--border)",
    background: "var(--card)",
    color: "var(--card-foreground)",
    width: 220,
    textAlign: "left",
  };
  if (status === "running")
    return { ...base, border: "1px solid var(--primary)", background: "color-mix(in oklab, var(--primary) 12%, var(--card))" };
  if (status === "done") return { ...base, border: "1px solid #10b981" };
  if (status === "error") return { ...base, border: "1px solid var(--destructive)" };
  return { ...base, opacity: 0.6 };
}

const DOT: Record<StepStatus, string> = {
  pending: "#9ca3af",
  running: "var(--primary)",
  done: "#10b981",
  error: "var(--destructive)",
};

// A node reads: "running <tool>…" while active, then the label + what it did.
function NodeLabel({ step }: { step: TraceStep }) {
  const running = step.status === "running";
  const head = running ? `running ${step.tool}…` : step.label;
  const body = running ? step.rationale ?? "working…" : step.detail ?? step.tool;
  return (
    <div>
      <div className="flex items-center gap-1.5">
        <span
          className={"inline-block size-2 shrink-0 rounded-full" + (running ? " animate-pulse" : "")}
          style={{ background: DOT[step.status] }}
        />
        <span className="font-medium">{head}</span>
      </div>
      {body && (
        <div className="mt-1 line-clamp-3 text-[10px] font-normal leading-snug opacity-70">
          {body}
        </div>
      )}
    </div>
  );
}

export function ToolGraph({ steps }: { steps: TraceStep[] }) {
  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = steps.map((s, i) => ({
      id: s.id,
      data: { label: <NodeLabel step={s} /> },
      position: { x: 20, y: i * 104 },
      style: nodeStyle(s.status),
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
    }));

    const edges: Edge[] = steps.slice(1).map((s, i) => ({
      id: `e-${steps[i].id}-${s.id}`,
      source: steps[i].id,
      target: s.id,
      animated: s.status === "running" || steps[i].status === "running",
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: "var(--border)" },
    }));

    return { nodes, edges };
  }, [steps]);

  if (!steps.length) {
    return (
      <p className="p-3 text-sm text-muted-foreground">
        A graph of the tools each question invoked (and their order) appears here.
      </p>
    );
  }

  // Size the canvas to the chain so fitView keeps the node text readable
  // instead of shrinking a tall chain into an unreadable thumbnail.
  const height = Math.max(240, steps.length * 104 + 24);

  return (
    <div className="w-full" style={{ height }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        zoomOnScroll={false}
        panOnDrag={false}
      >
        <Background gap={16} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
