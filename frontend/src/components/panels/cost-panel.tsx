"use client";

import { Badge } from "@/components/ui/badge";
import { formatUsd } from "@/lib/utils";
import type { CostInfo } from "@/lib/types";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}

export function CostPanel({ cost }: { cost?: CostInfo }) {
  if (!cost) {
    return (
      <p className="p-3 text-sm text-muted-foreground">
        A token &amp; cost estimate appears here before the run, and the actual
        cost after it completes.
      </p>
    );
  }

  return (
    <div className="space-y-3 p-1">
      {cost.model && (
        <Badge variant="secondary" className="text-[10px]">
          {cost.model}
        </Badge>
      )}

      <div className="rounded-lg border border-border p-3">
        <div className="mb-1 text-xs font-medium uppercase text-muted-foreground">
          Cost
        </div>
        <Row label="Estimated" value={formatUsd(cost.estimatedUsd)} />
        <Row label="Actual" value={formatUsd(cost.actualUsd)} />
      </div>

      <div className="rounded-lg border border-border p-3">
        <div className="mb-1 text-xs font-medium uppercase text-muted-foreground">
          Tokens
        </div>
        <Row label="Input" value={(cost.inputTokens ?? 0).toLocaleString()} />
        <Row label="Output" value={(cost.outputTokens ?? 0).toLocaleString()} />
      </div>
    </div>
  );
}
