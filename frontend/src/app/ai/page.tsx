"use client";

import AppShell from "@/components/AppShell";
import AIChat from "@/components/AIChat";
import { PageHeader, Badge, useAsyncAction, ErrorBanner } from "@/components/ui";
import { useFetch } from "@/lib/useFetch";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { SEVERITY_STYLES } from "@/lib/format";
import type { Recommendation, ToolSpec } from "@/lib/types";

export default function AIPage() {
  return (
    <AppShell>
      <Inner />
    </AppShell>
  );
}

function Inner() {
  const { can } = useAuth();
  const recs = useFetch<Recommendation[]>("/api/v1/ai/recommendations");
  const tools = useFetch<ToolSpec[]>("/api/v1/ai/tools");
  const monitor = useAsyncAction();

  async function decide(id: string, decision: "accepted" | "dismissed") {
    await api(`/api/v1/ai/recommendations/${id}/${decision}`, { method: "POST" });
    recs.reload();
  }

  return (
    <>
      <PageHeader
        title="AI Command Center"
        subtitle="The AI selects tools, the ERP computes the numbers, a human approves actions."
        actions={
          can("ai.recommendation.read") && (
            <button
              className="btn-primary"
              disabled={monitor.busy}
              onClick={() =>
                monitor.run(async () => {
                  await api("/api/v1/ai/monitor/run", { method: "POST" });
                  await recs.reload();
                })
              }
            >
              {monitor.busy ? "Scanning…" : "Run monitoring sweep"}
            </button>
          )
        }
      />
      <ErrorBanner message={monitor.error || recs.error} />

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="space-y-3 lg:col-span-3">
          <h2 className="font-semibold">Open recommendations</h2>
          {recs.data?.length === 0 && (
            <div className="card p-4 text-sm text-slate-400">Nothing flagged right now.</div>
          )}
          {recs.data?.map((r) => (
            <div key={r.id} className="card p-4">
              <div className="flex items-center gap-2">
                <Badge className={SEVERITY_STYLES[r.severity]}>{r.severity}</Badge>
                <span className="text-xs font-medium text-slate-400">{r.type}</span>
                <span className="ml-auto text-xs text-slate-400">
                  {(r.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
              <div className="mt-1 font-medium text-slate-800">{r.title}</div>
              <p className="mt-1 text-sm text-slate-600">{r.description}</p>
              {r.estimated_impact && (
                <p className="mt-1 text-xs text-slate-400">Impact: {r.estimated_impact}</p>
              )}
              <div className="mt-3 flex gap-2">
                <button className="btn-ghost" onClick={() => decide(r.id, "accepted")}>
                  Accept
                </button>
                <button className="btn-ghost" onClick={() => decide(r.id, "dismissed")}>
                  Dismiss
                </button>
              </div>
            </div>
          ))}

          <h2 className="pt-4 font-semibold">Available AI tools</h2>
          <div className="card divide-y divide-slate-100">
            {tools.data?.map((t) => (
              <div key={t.name} className="flex items-start gap-3 p-3">
                <Badge
                  className={
                    t.risk === "read"
                      ? "bg-slate-100 text-slate-600 border-slate-200"
                      : "bg-amber-100 text-amber-800 border-amber-200"
                  }
                >
                  {t.risk}
                </Badge>
                <div className="min-w-0">
                  <div className="font-mono text-sm text-slate-800">{t.name}</div>
                  <div className="text-xs text-slate-500">{t.description}</div>
                  <div className="text-[11px] text-slate-400">
                    requires <span className="font-mono">{t.permission}</span>
                    {t.allowed_for_you ? " · you can use this" : " · not available to you"}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-2">
          <AIChat />
        </div>
      </div>
    </>
  );
}
