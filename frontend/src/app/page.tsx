"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import AIChat from "@/components/AIChat";
import { PageHeader, StatCard } from "@/components/ui";
import { useFetch } from "@/lib/useFetch";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import type { ProfitLoss, CashFlow, InventoryRow, Recommendation } from "@/lib/types";

const SEV_DOT: Record<string, string> = {
  high: "bg-rose-500",
  medium: "bg-amber-500",
  low: "bg-sky-500",
  info: "bg-faint",
};

export default function DashboardPage() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}

function Dashboard() {
  const { me, can } = useAuth();
  const canReports = can("accounting.report.read");
  const pnl = useFetch<ProfitLoss>(canReports ? "/api/v1/accounting/reports/profit-loss" : null);
  const recs = useFetch<Recommendation[]>(
    can("ai.recommendation.read") ? "/api/v1/ai/recommendations" : null,
  );
  const inv = useFetch<InventoryRow[]>(can("inventory.read") ? "/api/v1/inventory/position" : null);
  const cash = useCashFlow(canReports);

  const lowStock = (inv.data || []).filter((r) => r.below_reorder);
  const first = (me?.full_name || me?.email || "").split(/[ @]/)[0];
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <>
      <PageHeader
        title={first ? `${greet}, ${first}` : "Overview"}
        subtitle="What the business needs your attention on today."
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Net profit"
          value={pnl.data ? money(pnl.data.net_profit) : "—"}
          tone={pnl.data ? (pnl.data.net_profit >= 0 ? "good" : "bad") : "default"}
          hint={pnl.data ? `${money(pnl.data.revenue)} revenue` : undefined}
        />
        <StatCard
          label="Projected cash · 30d"
          value={cash ? money(cash.projected_balance) : canReports ? "…" : "—"}
          tone={cash ? (cash.shortfall ? "bad" : "good") : "default"}
          hint={
            cash ? `${money(cash.expected_inflow)} in · ${money(cash.expected_outflow)} out` : undefined
          }
        />
        <StatCard
          label="Open recommendations"
          value={recs.data ? String(recs.data.length) : "—"}
          tone={recs.data?.some((r) => r.severity === "high") ? "bad" : "default"}
          hint={recs.data?.length ? "AI flagged" : undefined}
        />
        <StatCard
          label="Below reorder point"
          value={inv.data ? String(lowStock.length) : "—"}
          tone={lowStock.length ? "warn" : "good"}
          hint={inv.data ? `of ${inv.data.length} products` : undefined}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <section className="space-y-3 lg:col-span-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-fg">Needs attention</h2>
            {can("ai.recommendation.read") && (
              <Link href="/ai" className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-400">
                AI Command Center →
              </Link>
            )}
          </div>

          {!can("ai.recommendation.read") ? (
            <div className="card p-5 text-sm text-faint">
              You don&apos;t have access to AI recommendations.
            </div>
          ) : recs.loading ? (
            <div className="card p-5 text-sm text-faint">Loading…</div>
          ) : recs.data && recs.data.length === 0 ? (
            <div className="card flex items-center gap-3 p-5 text-sm text-muted">
              <span className="grid h-8 w-8 place-items-center rounded-full bg-emerald-500/10 text-emerald-500">
                ✓
              </span>
              All clear — nothing flagged right now.
            </div>
          ) : (
            recs.data?.map((r) => (
              <div key={r.id} className="card p-4 transition-shadow hover:shadow-pop">
                <div className="flex items-start gap-3">
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${SEV_DOT[r.severity]}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-fg">{r.title}</span>
                      <span className="text-[11px] font-medium uppercase tracking-wide text-faint">
                        {r.type.replace(/_/g, " ")}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-muted">{r.description}</p>
                  </div>
                  {r.estimated_impact && (
                    <span className="shrink-0 text-right text-xs text-faint">{r.estimated_impact}</span>
                  )}
                </div>
              </div>
            ))
          )}
        </section>

        <section className="lg:col-span-2">
          <AIChat compact />
        </section>
      </div>
    </>
  );
}

function useCashFlow(enabled: boolean) {
  const [data, setData] = useState<CashFlow | null>(null);
  useEffect(() => {
    if (!enabled) return;
    api<{ result: CashFlow }>("/api/v1/ai/execute", {
      method: "POST",
      body: { tool: "get_cash_flow", arguments: { horizon_days: 30 } },
    })
      .then((r) => setData(r.result))
      .catch(() => setData(null));
  }, [enabled]);
  return data;
}
