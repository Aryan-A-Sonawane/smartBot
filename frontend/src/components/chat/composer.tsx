"use client";

import {
  forwardRef,
  useImperativeHandle,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type KeyboardEvent,
} from "react";
import {
  ArrowUp,
  AudioLines,
  FileText,
  ImageIcon,
  Paperclip,
  Square,
  X,
  File as FileIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn, fileKind, formatBytes, uid } from "@/lib/utils";
import type { Attachment, AttachmentKind } from "@/lib/types";

export type ComposerHandle = {
  setText: (t: string) => void;
  focus: () => void;
};

type Props = {
  onSend: (query: string, attachments: Attachment[]) => void;
  isRunning: boolean;
  onStop: () => void;
};

const KIND_ICON: Record<AttachmentKind, typeof FileIcon> = {
  image: ImageIcon,
  pdf: FileText,
  audio: AudioLines,
  other: FileIcon,
};

export const Composer = forwardRef<ComposerHandle, Props>(function Composer(
  { onSend, isRunning, onStop },
  ref,
) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState<Attachment[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  useImperativeHandle(ref, () => ({
    setText: (t) => {
      setText(t);
      requestAnimationFrame(() => {
        adjustHeight();
        taRef.current?.focus();
      });
    },
    focus: () => taRef.current?.focus(),
  }));

  function adjustHeight() {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  }

  function addFiles(list: FileList | null) {
    if (!list) return;
    const next: Attachment[] = Array.from(list).map((f) => ({
      id: uid("file"),
      name: f.name,
      size: f.size,
      kind: fileKind(f),
      file: f,
    }));
    setFiles((prev) => [...prev, ...next]);
  }

  function onFileInput(e: ChangeEvent<HTMLInputElement>) {
    addFiles(e.target.files);
    e.target.value = ""; // allow re-selecting the same file
  }

  function removeFile(id: string) {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }

  function submit() {
    if (isRunning) return;
    if (!text.trim() && files.length === 0) return;
    onSend(text, files);
    setText("");
    setFiles([]);
    requestAnimationFrame(adjustHeight);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    addFiles(e.dataTransfer.files);
  }

  const canSend = !!text.trim() || files.length > 0;

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={cn(
          "rounded-2xl border bg-card p-2 shadow-sm transition-colors",
          dragOver ? "border-primary ring-2 ring-primary/30" : "border-border",
        )}
      >
        {/* File chips */}
        {files.length > 0 && (
          <div className="flex flex-wrap gap-2 px-1 pb-2">
            {files.map((f) => {
              const Icon = KIND_ICON[f.kind];
              return (
                <div
                  key={f.id}
                  className="flex items-center gap-2 rounded-lg border border-border bg-background py-1 pl-2 pr-1 text-xs"
                >
                  <Icon className="size-3.5 text-muted-foreground" />
                  <span className="max-w-[160px] truncate">{f.name}</span>
                  <span className="text-muted-foreground">{formatBytes(f.size)}</span>
                  <button
                    onClick={() => removeFile(f.id)}
                    aria-label={`Remove ${f.name}`}
                    className="rounded p-0.5 hover:bg-muted"
                  >
                    <X className="size-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Input row */}
        <div className="flex items-end gap-2">
          <input
            ref={inputRef}
            type="file"
            multiple
            accept="image/*,application/pdf,audio/*"
            className="hidden"
            onChange={onFileInput}
          />
          <Button
            variant="ghost"
            size="icon"
            aria-label="Attach files"
            onClick={() => inputRef.current?.click()}
          >
            <Paperclip className="size-4" />
          </Button>

          <textarea
            ref={taRef}
            rows={1}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              adjustHeight();
            }}
            onKeyDown={onKeyDown}
            placeholder="Ask anything, or attach an image, PDF, or audio…"
            className="max-h-40 flex-1 resize-none bg-transparent px-1 py-2 text-sm outline-none placeholder:text-muted-foreground"
          />

          {isRunning ? (
            <Button
              size="icon"
              variant="secondary"
              aria-label="Stop"
              onClick={onStop}
              className="rounded-xl"
            >
              <Square className="size-4" />
            </Button>
          ) : (
            <Button
              size="icon"
              aria-label="Send"
              disabled={!canSend}
              onClick={submit}
              className="rounded-xl"
            >
              <ArrowUp className="size-4" />
            </Button>
          )}
        </div>
      </div>
      <p className="mt-2 text-center text-[11px] text-muted-foreground">
        SmartBot can make mistakes. Outputs are text-only · Enter to send, Shift+Enter for a new line.
      </p>
    </div>
  );
});
