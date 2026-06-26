"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { StepStatus, TraceStep } from "@/lib/types";

// Map a step status to node colors (uses theme CSS variables).
function nodeStyle(status: StepStatus): React.CSSProperties {
  const base: React.CSSProperties = {
    borderRadius: 10,
    padding: "8px 12px",
    fontSize: 12,
    fontWeight: 500,
    border: "1px solid var(--border)",
    background: "var(--card)",
    color: "var(--card-foreground)",
    width: 160,
    textAlign: "center",
  };
  if (status === "running")
    return { ...base, border: "1px solid var(--primary)", background: "color-mix(in oklab, var(--primary) 12%, var(--card))" };
  if (status === "done")
    return { ...base, border: "1px solid #10b981" };
  if (status === "error")
    return { ...base, border: "1px solid var(--destructive)" };
  return { ...base, opacity: 0.6 };
}

export function ToolGraph({ steps }: { steps: TraceStep[] }) {
  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = steps.map((s, i) => ({
      id: s.id,
      data: { label: s.label },
      position: { x: 20, y: i * 80 },
      style: nodeStyle(s.status),
      sourcePosition: "bottom" as const,
      targetPosition: "top" as const,
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
        A graph of the tools the agent invoked (and their order) appears here.
      </p>
    );
  }

  return (
    <div className="h-full min-h-[260px] w-full">
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
