import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { AttachmentKind } from "@/lib/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Small unique id helper (good enough for client-side keys).
export function uid(prefix = "id"): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

// Map a browser File to one of our attachment kinds.
export function fileKind(file: File): AttachmentKind {
  const type = file.type;
  const name = file.name.toLowerCase();
  if (type.startsWith("image/") || /\.(png|jpe?g|webp|gif|bmp)$/.test(name)) {
    return "image";
  }
  if (type === "application/pdf" || name.endsWith(".pdf")) return "pdf";
  if (type.startsWith("audio/") || /\.(mp3|wav|m4a|ogg|flac)$/.test(name)) {
    return "audio";
  }
  return "other";
}

// Human-readable file size.
export function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${units[i]}`;
}

// Crude token estimate (~4 chars/token) for the cost estimator.
export function estimateTokens(text: string): number {
  return Math.max(1, Math.ceil(text.length / 4));
}

export function formatUsd(value?: number): string {
  if (value == null) return "—";
  if (value < 0.01) return `$${value.toFixed(5)}`;
  return `$${value.toFixed(4)}`;
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Find the first URL in a blob of text (used to detect links inside inputs).
export function findUrl(text: string): string | null {
  const match = text.match(/https?:\/\/[^\s)>\]]+/i);
  return match ? match[0] : null;
}

export function isYouTube(url: string): boolean {
  return /youtube\.com\/watch|youtu\.be\//i.test(url);
}
