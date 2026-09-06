"use client";

import AppShell from "@/components/AppShell";
import AIChat from "@/components/AIChat";
import { PageHeader, Badge, useAsyncAction, ErrorBanner } from "@/components/ui";
import { useFetch } from "@/lib/useFetch";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { SEVERITY_STYLES, chipTone } from "@/lib/format";
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
          <h2 className="text-sm font-semibold text-fg">Open recommendations</h2>
          {recs.data?.length === 0 && (
            <div className="card p-4 text-sm text-faint">Nothing flagged right now.</div>
          )}
          {recs.data?.map((r) => (
            <div key={r.id} className="card p-4">
              <div className="flex items-center gap-2">
                <Badge className={SEVERITY_STYLES[r.severity]}>{r.severity}</Badge>
                <span className="text-xs font-medium text-faint">{r.type}</span>
                <span className="ml-auto text-xs text-faint">
                  {(r.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
              <div className="mt-1 font-medium text-fg">{r.title}</div>
              <p className="mt-1 text-sm text-muted">{r.description}</p>
              {r.estimated_impact && (
                <p className="mt-1 text-xs text-faint">Impact: {r.estimated_impact}</p>
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

          <h2 className="pt-6 text-sm font-semibold text-fg">Available AI tools</h2>
          <div className="card divide-y divide-line">
            {tools.data?.map((t) => (
              <div key={t.name} className="flex items-start gap-3 p-3">
                <Badge
                  className={
                    t.risk === "read"
                      ? "bg-surface-2 text-muted border-line"
                      : chipTone.warn
                  }
                >
                  {t.risk}
                </Badge>
                <div className="min-w-0">
                  <div className="font-mono text-sm text-fg">{t.name}</div>
                  <div className="text-xs text-muted">{t.description}</div>
                  <div className="text-[11px] text-faint">
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
