"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import {
  AudioLines,
  FileText,
  Image as ImageIcon,
  Layers,
  Link2,
  Loader2,
} from "lucide-react";

// The 5 official assignment test cases as one-click prompts. File-based cases
// load a bundled sample from /public/samples into the composer; audio cases
// prefill the query for the user to attach their own clip.
type SampleFile = { url: string; name: string; type: string };
type Sample = {
  icon: typeof FileText;
  title: string;
  query: string;
  hint: string;
  files?: SampleFile[];
};

const PDF = "application/pdf";
const NOTES: SampleFile = { url: "/samples/meeting-notes.pdf", name: "meeting-notes.pdf", type: PDF };

const SAMPLES: Sample[] = [
  {
    icon: AudioLines,
    title: "Audio → summary",
    query:
      "Transcribe this audio and give me a 1-line summary, 3 bullets, a 5-sentence summary, and the duration.",
    hint: "Attach an audio lecture",
  },
  {
    icon: FileText,
    title: "PDF action items",
    query: "What are the action items in this PDF?",
    hint: "Loads a sample meeting-notes PDF",
    files: [NOTES],
  },
  {
    icon: ImageIcon,
    title: "Explain code screenshot",
    query: "Explain this code, flag any bugs, and tell me its time complexity.",
    hint: "Loads a sample code screenshot",
    files: [{ url: "/samples/code-snippet.png", name: "code-snippet.png", type: "image/png" }],
  },
  {
    icon: Link2,
    title: "YouTube link in PDF",
    query: "Hit the YouTube URL in this PDF and give me a summary of it.",
    hint: "Loads a PDF containing a YouTube link",
    files: [{ url: "/samples/youtube-in-pdf.pdf", name: "youtube-in-pdf.pdf", type: PDF }],
  },
  {
    icon: Layers,
    title: "Compare two inputs",
    query: "Do the audio and the document discuss the same topic?",
    hint: "Loads the meeting PDF — add your own audio",
    files: [NOTES],
  },
];

async function loadFiles(files: SampleFile[]): Promise<File[]> {
  return Promise.all(
    files.map(async (f) => {
      const res = await fetch(f.url);
      if (!res.ok) throw new Error(`Could not load ${f.url} (${res.status})`);
      const blob = await res.blob();
      return new File([blob], f.name, { type: f.type });
    }),
  );
}

export function SampleGallery({
  onLoad,
}: {
  onLoad: (query: string, files: File[]) => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);

  async function pick(s: Sample) {
    if (busy) return;
    if (!s.files?.length) {
      onLoad(s.query, []);
      return;
    }
    setBusy(s.title);
    try {
      onLoad(s.query, await loadFiles(s.files));
    } catch {
      onLoad(s.query, []); // graceful: still prefill the query if the fetch fails
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="grid w-full max-w-3xl grid-cols-1 gap-2 sm:grid-cols-2">
      {SAMPLES.map((s) => {
        const loading = busy === s.title;
        const Icon = loading ? Loader2 : s.icon;
        return (
          <Card
            key={s.title}
            onClick={() => pick(s)}
            className="cursor-pointer p-3 transition-colors hover:bg-muted"
          >
            <div className="flex items-start gap-3">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted">
                <Icon className={"size-4 text-primary" + (loading ? " animate-spin" : "")} />
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
