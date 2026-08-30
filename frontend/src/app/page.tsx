"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import AIChat from "@/components/AIChat";
import { PageHeader, StatCard, Badge } from "@/components/ui";
import { useFetch } from "@/lib/useFetch";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { money, SEVERITY_STYLES } from "@/lib/format";
import type { ProfitLoss, CashFlow, InventoryRow, Recommendation } from "@/lib/types";

export default function DashboardPage() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}

function Dashboard() {
  const { can } = useAuth();
  const canReports = can("accounting.report.read");
  const pnl = useFetch<ProfitLoss>(canReports ? "/api/v1/accounting/reports/profit-loss" : null);
  const recs = useFetch<Recommendation[]>(
    can("ai.recommendation.read") ? "/api/v1/ai/recommendations" : null,
  );
  const inv = useFetch<InventoryRow[]>(can("inventory.read") ? "/api/v1/inventory/position" : null);
  const cash = useCashFlow(canReports);

  const lowStock = (inv.data || []).filter((r) => r.below_reorder);

  return (
    <>
      <PageHeader
        title="AI Command Center"
        subtitle="What the business needs your attention on today"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Net profit"
          value={pnl.data ? money(pnl.data.net_profit) : "—"}
          tone={pnl.data ? (pnl.data.net_profit >= 0 ? "good" : "bad") : "default"}
          hint={pnl.data ? `${money(pnl.data.revenue)} revenue` : undefined}
        />
        <StatCard
          label="Projected cash (30d)"
          value={cash ? money(cash.projected_balance) : canReports ? "…" : "—"}
          tone={cash?.shortfall ? "bad" : "good"}
          hint={
            cash
              ? `${money(cash.expected_inflow)} in / ${money(cash.expected_outflow)} out`
              : undefined
          }
        />
        <StatCard
          label="Open recommendations"
          value={recs.data ? String(recs.data.length) : "—"}
          tone={recs.data?.some((r) => r.severity === "high") ? "bad" : "default"}
        />
        <StatCard
          label="Products below reorder"
          value={inv.data ? String(lowStock.length) : "—"}
          tone={lowStock.length ? "warn" : "good"}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Recommendations</h2>
            {can("ai.recommendation.read") && (
              <Link href="/ai" className="text-sm text-brand-600 hover:underline">
                Open command center →
              </Link>
            )}
          </div>

          {!can("ai.recommendation.read") && (
            <div className="card p-4 text-sm text-slate-400">
              You don&apos;t have access to AI recommendations.
            </div>
          )}
          {recs.data && recs.data.length === 0 && (
            <div className="card p-4 text-sm text-slate-400">
              No open recommendations. Run the monitor from the AI Command Center.
            </div>
          )}
          {recs.data?.map((r) => (
            <div key={r.id} className="card p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <Badge className={SEVERITY_STYLES[r.severity]}>{r.severity}</Badge>
                    <span className="text-xs font-medium text-slate-400">{r.type}</span>
                  </div>
                  <div className="mt-1 font-medium text-slate-800">{r.title}</div>
                  <p className="mt-1 text-sm text-slate-600">{r.description}</p>
                </div>
                {r.estimated_impact && (
                  <div className="shrink-0 text-right text-xs text-slate-400">
                    {r.estimated_impact}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div>
          <AIChat compact />
        </div>
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
