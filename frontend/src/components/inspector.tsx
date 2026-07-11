"use client";

import { useMemo } from "react";
import { Braces, Download, MessageSquare, X } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TracePanel } from "@/components/panels/trace-panel";
import { ToolGraph } from "@/components/panels/tool-graph";
import { ExtractedPanel } from "@/components/panels/extracted-panel";
import { CostPanel } from "@/components/panels/cost-panel";
import { cn } from "@/lib/utils";
import { isMock } from "@/lib/api";
import { downloadText, runToJson, runToMarkdown } from "@/lib/export";
import type { Message } from "@/lib/types";

type Props = {
  messages: Message[];
  open: boolean;
  onClose: () => void;
};

// One assistant turn paired with the user question that triggered it.
type Turn = { id: string; question: string; message: Message };

function buildTurns(messages: Message[]): Turn[] {
  const turns: Turn[] = [];
  let question = "";
  for (const m of messages) {
    if (m.role === "user") question = m.content;
    else turns.push({ id: m.id, question, message: m });
  }
  return turns;
}

// Header shown on each per-question box in the Trace / Graph tabs.
function TurnHeader({ turn }: { turn: Turn }) {
  return (
    <div className="flex items-center gap-2 border-b border-border bg-muted/40 px-2.5 py-1.5">
      <MessageSquare className="size-3.5 shrink-0 text-muted-foreground" />
      <span className="truncate text-xs font-medium" title={turn.question}>
        {turn.question || "(no question)"}
      </span>
      {turn.message.intent && (
        <Badge variant="outline" className="ml-auto shrink-0 text-[10px]">
          {turn.message.intent}
        </Badge>
      )}
    </div>
  );
}

export function Inspector({ messages, open, onClose }: Props) {
  const turns = useMemo(() => buildTurns(messages), [messages]);
  const ordered = useMemo(() => [...turns].reverse(), [turns]); // newest first
  const latest = turns.length ? turns[turns.length - 1] : undefined;

  const latestMsg = latest?.message;
  const canExport =
    !!latestMsg && !latestMsg.streaming && (!!latestMsg.content || (latestMsg.trace?.length ?? 0) > 0);
  const stamp = () => new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");

  const emptyHint = (text: string) => (
    <p className="p-3 text-sm text-muted-foreground">{text}</p>
  );

  return (
    <aside
      className={cn(
        "z-40 flex shrink-0 flex-col border-l border-border bg-background",
        // Mobile: off-canvas drawer from the right.
        "fixed inset-y-0 right-0 w-[88%] max-w-sm transition-transform duration-300",
        // Desktop: inline column that toggles width.
        "md:static md:z-auto md:max-w-none md:transition-[width]",
        open
          ? "translate-x-0 md:w-[32%] md:min-w-[340px]"
          : "translate-x-full md:w-0 md:min-w-0 md:overflow-hidden md:border-l-0",
      )}
    >
      <div className="flex items-center justify-between p-2">
        <div className="flex min-w-0 items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Close agent activity"
            title="Close"
            onClick={onClose}
          >
            <X className="size-4" />
          </Button>
          <span className="truncate text-xs font-semibold text-muted-foreground">
            Agent activity
          </span>
          {isMock() && (
            <Badge variant="outline" className="text-[10px]">
              demo data
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-0.5">
          {canExport && latest && (
            <>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Export latest run as Markdown"
                title="Export latest run as Markdown"
                onClick={() =>
                  downloadText(
                    `smartbot-run-${stamp()}.md`,
                    runToMarkdown(latest.question, latest.message),
                    "text/markdown",
                  )
                }
              >
                <Download className="size-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Export latest run as JSON"
                title="Export latest run as JSON"
                onClick={() =>
                  downloadText(
                    `smartbot-run-${stamp()}.json`,
                    runToJson(latest.question, latest.message),
                    "application/json",
                  )
                }
              >
                <Braces className="size-4" />
              </Button>
            </>
          )}
        </div>
      </div>

      <Tabs defaultValue="trace" className="flex min-h-0 flex-1 flex-col">
        <TabsList className="mx-3">
          <TabsTrigger value="trace">Plan Trace</TabsTrigger>
          <TabsTrigger value="graph">Graph</TabsTrigger>
          <TabsTrigger value="extracted">Extracted</TabsTrigger>
          <TabsTrigger value="cost">Cost</TabsTrigger>
        </TabsList>

        {/* Trace: one box per question, newest first, each with its own intent/goal + steps */}
        <TabsContent value="trace" className="min-h-0 flex-1 px-3 pb-3">
          <ScrollArea className="h-full">
            {ordered.length === 0
              ? emptyHint("The agent's understood goal and tool steps will appear here, one box per question.")
              : (
                <div className="space-y-2 pr-1">
                  {ordered.map((t) => (
                    <div key={t.id} className="overflow-hidden rounded-lg border border-border">
                      <TurnHeader turn={t} />
                      <TracePanel steps={t.message.trace ?? []} goal={t.message.goal} />
                    </div>
                  ))}
                </div>
              )}
          </ScrollArea>
        </TabsContent>

        {/* Graph: the tool chain of every question in this chat, newest first */}
        <TabsContent value="graph" className="min-h-0 flex-1 px-3 pb-3">
          <ScrollArea className="h-full">
            {ordered.length === 0
              ? emptyHint("A graph of the tools each question invoked (and their order) appears here.")
              : (
                <div className="space-y-2 pr-1">
                  {ordered.map((t) => (
                    <div key={t.id} className="overflow-hidden rounded-lg border border-border">
                      <TurnHeader turn={t} />
                      <ToolGraph steps={t.message.trace ?? []} />
                    </div>
                  ))}
                </div>
              )}
          </ScrollArea>
        </TabsContent>

        {/* Extracted + Cost reflect the most recent turn. */}
        <TabsContent value="extracted" className="min-h-0 flex-1 px-3 pb-3">
          <ScrollArea className="h-full rounded-md border border-border">
            <ExtractedPanel docs={latestMsg?.extracted ?? []} />
          </ScrollArea>
        </TabsContent>

        <TabsContent value="cost" className="min-h-0 flex-1 px-3 pb-3">
          <ScrollArea className="h-full rounded-md border border-border">
            <CostPanel cost={latestMsg?.cost} />
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </aside>
  );
}
