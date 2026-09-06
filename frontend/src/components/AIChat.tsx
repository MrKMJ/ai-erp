"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import Markdown from "@/components/Markdown";
import { Icon } from "@/components/icons";
import type { ChatResponse, ChatEvidence } from "@/lib/types";

interface Msg {
  role: "user" | "assistant";
  content: string;
  evidence?: ChatEvidence[];
}

const SUGGESTIONS = [
  "Give me a summary of inventory",
  "Show me the cash flow forecast",
  "Which products are at stockout risk?",
  "Who owes us the most money?",
  "Any supplier price anomalies?",
];

export default function AIChat({ compact = false }: { compact?: boolean }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const convId = useRef<string | null>(null);
  const scroller = useRef<HTMLDivElement>(null);

  async function send(text: string) {
    if (!text.trim() || busy) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api<ChatResponse>("/api/v1/ai/chat", {
        method: "POST",
        body: { message: text, conversation_id: convId.current },
      });
      convId.current = res.conversation_id;
      setMessages((m) => [...m, { role: "assistant", content: res.answer, evidence: res.evidence }]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `⚠️ ${e instanceof Error ? e.message : "Error"}` },
      ]);
    } finally {
      setBusy(false);
      setTimeout(() => scroller.current?.scrollTo(0, scroller.current.scrollHeight), 50);
    }
  }

  return (
    <div className={`card flex flex-col ${compact ? "h-[560px]" : "h-[calc(100vh-9rem)]"}`}>
      <div className="flex items-center gap-2 border-b border-line px-4 py-3">
        <span className="grid h-7 w-7 place-items-center rounded-md bg-brand-500/15 text-brand-600 dark:text-brand-400">
          <Icon.sparkles width={15} height={15} />
        </span>
        <div>
          <div className="text-sm font-semibold text-fg">Ask your ERP</div>
          <div className="text-[11px] text-faint">
            Answers come from ERP tools — every figure is traceable.
          </div>
        </div>
      </div>

      <div ref={scroller} className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="space-y-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="flex w-full items-center gap-2 rounded-lg border border-line bg-surface px-3 py-2 text-left text-sm text-muted transition-colors hover:border-brand-500/40 hover:bg-brand-500/5 hover:text-fg"
              >
                <span className="text-faint">›</span>
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <div
              className={`inline-block max-w-[92%] rounded-2xl px-3.5 py-2 text-sm ${
                m.role === "user"
                  ? "whitespace-pre-wrap bg-brand-600 text-white"
                  : "bg-surface-2 text-fg"
              }`}
            >
              {m.role === "user" ? m.content : <Markdown>{m.content}</Markdown>}
            </div>
            {m.evidence && m.evidence.length > 0 && (
              <div className="mt-2 space-y-1.5">
                {m.evidence.map((ev, j) => (
                  <details
                    key={j}
                    className="group rounded-lg border border-line bg-surface text-xs"
                  >
                    <summary className="flex cursor-pointer list-none items-center gap-1.5 px-3 py-1.5 font-medium text-muted">
                      <span className="text-faint transition-transform group-open:rotate-90">▸</span>
                      <Icon.spark width={12} height={12} />
                      <span className="font-mono">{ev.name}</span>
                    </summary>
                    <pre className="overflow-x-auto border-t border-line px-3 py-2 text-[11px] leading-relaxed text-muted">
                      {JSON.stringify(ev.result, null, 2)}
                    </pre>
                  </details>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && (
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-faint [animation-delay:-0.2s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-faint [animation-delay:-0.1s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-faint" />
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-2 border-t border-line p-3"
      >
        <input
          className="input"
          placeholder="Ask about sales, cash, inventory, suppliers…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button className="btn-primary !px-3" disabled={busy} aria-label="Send">
          <Icon.send width={16} height={16} />
        </button>
      </form>
    </div>
  );
}
