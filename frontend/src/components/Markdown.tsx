"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Small, safe Markdown renderer for AI chat answers (bold, lists, tables). */
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="space-y-2 text-sm leading-relaxed [&_strong]:font-semibold">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: (props) => <p {...props} />,
          ul: (props) => <ul className="list-disc space-y-1 pl-5" {...props} />,
          ol: (props) => <ol className="list-decimal space-y-1 pl-5" {...props} />,
          li: (props) => <li {...props} />,
          a: (props) => <a className="text-brand-600 underline dark:text-brand-400" {...props} />,
          code: (props) => (
            <code className="rounded bg-surface-2 px-1 py-0.5 text-[0.85em]" {...props} />
          ),
          table: (props) => (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-xs" {...props} />
            </div>
          ),
          th: (props) => (
            <th className="border border-line bg-surface-2 px-2 py-1 text-left font-semibold" {...props} />
          ),
          td: (props) => <td className="border border-line px-2 py-1" {...props} />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
