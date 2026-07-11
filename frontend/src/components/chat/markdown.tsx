"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

// Lightweight markdown renderer with hand-styled elements (no typography
// plugin needed). Used for assistant message bodies.
export function Markdown({
  children,
  className,
}: {
  children: string;
  className?: string;
}) {
  return (
    <div className={cn("space-y-3 break-words text-[15px] leading-relaxed", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (p) => <h1 className="text-lg font-semibold" {...p} />,
          h2: (p) => <h2 className="text-base font-semibold" {...p} />,
          h3: (p) => <h3 className="text-sm font-semibold" {...p} />,
          p: (p) => <p className="leading-relaxed" {...p} />,
          ul: (p) => <ul className="ml-5 list-disc space-y-1" {...p} />,
          ol: (p) => <ol className="ml-5 list-decimal space-y-1" {...p} />,
          li: (p) => <li className="leading-relaxed" {...p} />,
          a: (p) => (
            <a
              className="text-primary underline underline-offset-2"
              target="_blank"
              rel="noreferrer"
              {...p}
            />
          ),
          strong: (p) => <strong className="font-semibold" {...p} />,
          blockquote: (p) => (
            <blockquote
              className="border-l-2 border-border pl-3 text-muted-foreground"
              {...p}
            />
          ),
          pre: (p) => (
            <pre
              className="overflow-x-auto rounded-lg bg-muted p-3 text-sm"
              {...p}
            />
          ),
          code: ({ className: c, children, ...props }) => {
            const isBlock = /language-/.test(c ?? "");
            if (isBlock) {
              return (
                <code className={cn("font-mono text-sm", c)} {...props}>
                  {children}
                </code>
              );
            }
            return (
              <code
                className="rounded bg-muted px-1.5 py-0.5 font-mono text-[13px]"
                {...props}
              >
                {children}
              </code>
            );
          },
          table: (p) => (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm" {...p} />
            </div>
          ),
          th: (p) => (
            <th className="border border-border bg-muted px-2 py-1 text-left" {...p} />
          ),
          td: (p) => <td className="border border-border px-2 py-1" {...p} />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
