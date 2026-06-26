"use client";

import { Card } from "@/components/ui/card";
import { FileText, Image as ImageIcon, AudioLines, Link2, Layers } from "lucide-react";

// The 5 official assignment test cases, surfaced as one-click prompts.
// (File-based cases prefill the query; the user then attaches the file.)
const SAMPLES: {
  icon: typeof FileText;
  title: string;
  query: string;
  hint: string;
}[] = [
  {
    icon: AudioLines,
    title: "Audio → summary",
    query: "Transcribe this audio and give me a 1-line summary, 3 bullets, a 5-sentence summary, and the duration.",
    hint: "Attach an audio lecture",
  },
  {
    icon: FileText,
    title: "PDF action items",
    query: "What are the action items in this PDF?",
    hint: "Attach a meeting-notes PDF",
  },
  {
    icon: ImageIcon,
    title: "Explain code screenshot",
    query: "Explain this code, flag any bugs, and tell me its time complexity.",
    hint: "Attach a code screenshot",
  },
  {
    icon: Link2,
    title: "YouTube link in PDF",
    query: "Hit the YouTube URL in this PDF and give me a summary of it.",
    hint: "Attach a PDF containing a YouTube link",
  },
  {
    icon: Layers,
    title: "Compare two inputs",
    query: "Do the audio and the document discuss the same topic?",
    hint: "Attach one audio file + one PDF",
  },
];

export function SampleGallery({ onPick }: { onPick: (query: string) => void }) {
  return (
    <div className="grid w-full max-w-3xl grid-cols-1 gap-2 sm:grid-cols-2">
      {SAMPLES.map((s) => {
        const Icon = s.icon;
        return (
          <Card
            key={s.title}
            onClick={() => onPick(s.query)}
            className="cursor-pointer p-3 transition-colors hover:bg-muted"
          >
            <div className="flex items-start gap-3">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted">
                <Icon className="size-4 text-primary" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium">{s.title}</p>
                <p className="truncate text-xs text-muted-foreground">{s.hint}</p>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
