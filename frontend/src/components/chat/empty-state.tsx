"use client";

import { Bot } from "lucide-react";
import { SampleGallery } from "@/components/chat/sample-gallery";

export function EmptyState({
  onLoad,
}: {
  onLoad: (query: string, files: File[]) => void;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 px-4 text-center">
      <div className="flex flex-col items-center gap-3">
        <div className="flex size-12 items-center justify-center rounded-2xl bg-muted">
          <Bot className="size-6 text-primary" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">How can I help?</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Send text, images, PDFs, or audio — together if you like. I&apos;ll extract,
            reason, and chain tools to do the task.
          </p>
        </div>
      </div>
      <SampleGallery onLoad={onLoad} />

      <p className="max-w-md text-xs leading-relaxed text-muted-foreground/70">
        Heads up: this hosted demo runs on a small free instance. Short audio clips
        (a few minutes) and modest files work best — very long audio may be declined
        to stay within memory, and the first request after a while can take ~30–50 s
        while the server wakes up.
      </p>
    </div>
  );
}
