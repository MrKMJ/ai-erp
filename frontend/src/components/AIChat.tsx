"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import Markdown from "@/components/Markdown";
import type { ChatResponse, ChatEvidence } from "@/lib/types";

interface Msg {
  role: "user" | "assistant";
  content: string;
  evidence?: ChatEvidence[];
}

const SUGGESTIONS = [
  "What is our profit and loss?",
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
      setMessages((m) => [
        ...m,
        { role: "assistant", content: res.answer, evidence: res.evidence },
      ]);
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
    <div className={`card flex flex-col ${compact ? "h-[520px]" : "h-[calc(100vh-8rem)]"}`}>
      <div className="border-b border-slate-100 px-4 py-3">
        <div className="font-semibold">Ask your ERP</div>
        <div className="text-xs text-slate-400">
          Answers are computed by ERP tools — every figure is traceable.
        </div>
      </div>

      <div ref={scroller} className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="space-y-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="block w-full rounded-lg border border-slate-200 px-3 py-2 text-left text-sm text-slate-600 hover:border-brand-300 hover:bg-brand-50"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <div
              className={`inline-block max-w-[92%] rounded-2xl px-4 py-2 text-sm ${
                m.role === "user"
                  ? "whitespace-pre-wrap bg-brand-600 text-white"
                  : "bg-slate-100 text-slate-800"
              }`}
            >
              {m.role === "user" ? m.content : <Markdown>{m.content}</Markdown>}
            </div>
            {m.evidence && m.evidence.length > 0 && (
              <div className="mt-2 space-y-2">
                {m.evidence.map((ev, j) => (
                  <details key={j} className="rounded-lg border border-slate-200 bg-white text-xs">
                    <summary className="cursor-pointer px-3 py-1.5 font-medium text-slate-600">
                      🔧 {ev.name}
                    </summary>
                    <pre className="overflow-x-auto border-t border-slate-100 px-3 py-2 text-[11px] text-slate-600">
                      {JSON.stringify(ev.result, null, 2)}
                    </pre>
                  </details>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="text-sm text-slate-400">Thinking…</div>}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-2 border-t border-slate-100 p-3"
      >
        <input
          className="input"
          placeholder="Ask about sales, cash, inventory, suppliers…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button className="btn-primary" disabled={busy}>
          Send
        </button>
      </form>
    </div>
  );
}
