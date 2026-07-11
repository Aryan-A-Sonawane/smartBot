// Serialise a completed agent run (query, plan, extracted text, result, cost)
// to Markdown or JSON and trigger a browser download. Used by the Inspector's
// export buttons.

import type { Message } from "@/lib/types";

export function runToJson(query: string, m: Message): string {
  return JSON.stringify(
    {
      query,
      result: m.content,
      plan: (m.trace ?? []).map((s) => ({
        tool: s.tool,
        label: s.label,
        rationale: s.rationale,
        status: s.status,
        durationMs: s.durationMs,
      })),
      extracted: m.extracted ?? [],
      cost: m.cost ?? null,
      exportedAt: new Date().toISOString(),
    },
    null,
    2,
  );
}

export function runToMarkdown(query: string, m: Message): string {
  const out: string[] = ["# SmartBot run", ""];
  if (query) out.push(`**Query:** ${query}`, "");

  if (m.trace?.length) {
    out.push("## Plan");
    m.trace.forEach((s, i) => {
      const timing = s.durationMs != null ? ` · ${s.durationMs}ms` : "";
      out.push(`${i + 1}. **${s.label}** (\`${s.tool}\`) — ${s.status}${timing}`);
      if (s.rationale) out.push(`   - _${s.rationale}_`);
    });
    out.push("");
  }

  if (m.extracted?.length) {
    out.push("## Extracted text");
    for (const d of m.extracted) {
      const conf = d.ocrConfidence != null ? ` — OCR ${Math.round(d.ocrConfidence * 100)}%` : "";
      out.push(`### ${d.source} (${d.kind})${conf}`, "```", d.content, "```", "");
    }
  }

  out.push("## Result", m.content || "_(no output)_");

  if (m.cost) {
    const usd = (v?: number) => (v != null ? `$${v.toFixed(6)}` : "—");
    out.push(
      "",
      "## Cost",
      `- Model: ${m.cost.model ?? "—"}`,
      `- Estimated: ${usd(m.cost.estimatedUsd)}`,
      `- Actual: ${usd(m.cost.actualUsd)}`,
      `- Tokens: ${m.cost.inputTokens ?? "—"} in / ${m.cost.outputTokens ?? "—"} out`,
    );
  }

  return out.join("\n");
}

export function downloadText(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
