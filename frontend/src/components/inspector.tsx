"use client";

import { PanelRightClose } from "lucide-react";
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
import type { Message } from "@/lib/types";

type Props = {
  message?: Message;
  open: boolean;
  onClose: () => void;
};

export function Inspector({ message, open, onClose }: Props) {
  const trace = message?.trace ?? [];
  const extracted = message?.extracted ?? [];
  const cost = message?.cost;

  return (
    <aside
      className={cn(
        "flex shrink-0 flex-col border-l border-border transition-all duration-300",
        open ? "w-[32%] min-w-[340px]" : "w-0 overflow-hidden border-l-0",
      )}
    >
      <div className="flex items-center justify-between p-2">
        <div className="flex items-center gap-2 px-2">
          <span className="text-xs font-semibold text-muted-foreground">
            Agent activity
          </span>
          {isMock() && (
            <Badge variant="outline" className="text-[10px]">
              demo data
            </Badge>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Collapse panels"
          onClick={onClose}
        >
          <PanelRightClose className="size-4" />
        </Button>
      </div>

      <Tabs defaultValue="trace" className="flex min-h-0 flex-1 flex-col">
        <TabsList className="mx-3">
          <TabsTrigger value="trace">Plan Trace</TabsTrigger>
          <TabsTrigger value="graph">Graph</TabsTrigger>
          <TabsTrigger value="extracted">Extracted</TabsTrigger>
          <TabsTrigger value="cost">Cost</TabsTrigger>
        </TabsList>

        <TabsContent value="trace" className="min-h-0 flex-1 px-3 pb-3">
          <ScrollArea className="h-full rounded-md border border-border">
            <TracePanel steps={trace} />
          </ScrollArea>
        </TabsContent>

        <TabsContent value="graph" className="min-h-0 flex-1 px-3 pb-3">
          <div className="h-full rounded-md border border-border">
            <ToolGraph steps={trace} />
          </div>
        </TabsContent>

        <TabsContent value="extracted" className="min-h-0 flex-1 px-3 pb-3">
          <ScrollArea className="h-full rounded-md border border-border">
            <ExtractedPanel docs={extracted} />
          </ScrollArea>
        </TabsContent>

        <TabsContent value="cost" className="min-h-0 flex-1 px-3 pb-3">
          <ScrollArea className="h-full rounded-md border border-border">
            <CostPanel cost={cost} />
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </aside>
  );
}
