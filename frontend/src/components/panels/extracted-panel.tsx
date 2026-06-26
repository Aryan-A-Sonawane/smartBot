"use client";

import { AudioLines, FileText, Image as ImageIcon, Type, File as FileIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ExtractedDoc } from "@/lib/types";

const KIND_ICON = {
  image: ImageIcon,
  pdf: FileText,
  audio: AudioLines,
  text: Type,
  other: FileIcon,
} as const;

export function ExtractedPanel({ docs }: { docs: ExtractedDoc[] }) {
  if (!docs.length) {
    return (
      <p className="p-3 text-sm text-muted-foreground">
        Text extracted from your images, PDFs, and audio will show up here.
      </p>
    );
  }

  return (
    <div className="space-y-3 p-1">
      {docs.map((d, i) => {
        const Icon = KIND_ICON[d.kind] ?? FileIcon;
        return (
          <div key={i} className="rounded-lg border border-border">
            <div className="flex items-center gap-2 border-b border-border px-3 py-2">
              <Icon className="size-4 text-muted-foreground" />
              <span className="truncate text-sm font-medium">{d.source}</span>
              <Badge variant="secondary" className="text-[10px] uppercase">
                {d.kind}
              </Badge>
              {d.ocrConfidence != null && (
                <Badge variant="outline" className="ml-auto text-[10px]">
                  OCR {Math.round(d.ocrConfidence * 100)}%
                </Badge>
              )}
            </div>
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap px-3 py-2 font-mono text-xs leading-relaxed text-muted-foreground">
              {d.content}
            </pre>
          </div>
        );
      })}
    </div>
  );
}
