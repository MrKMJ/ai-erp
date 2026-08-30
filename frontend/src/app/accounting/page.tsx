"use client";

import AppShell from "@/components/AppShell";
import { PageHeader, StatCard, Table, ErrorBanner } from "@/components/ui";
import { useFetch } from "@/lib/useFetch";
import { useAuth } from "@/lib/auth";
import { money, date } from "@/lib/format";
import type { ProfitLoss } from "@/lib/types";

interface TrialRow {
  code: string;
  name: string;
  type: string;
  debit: number;
  credit: number;
  balance: number;
}
interface JournalRow {
  id: string;
  number: string;
  date: string;
  description: string;
  status: string;
  lines: { account_id: string; debit: number; credit: number; memo: string }[];
}

export default function AccountingPage() {
  return (
    <AppShell>
      <Inner />
    </AppShell>
  );
}

function Inner() {
  const { can } = useAuth();
  const pnl = useFetch<ProfitLoss>(
    can("accounting.report.read") ? "/api/v1/accounting/reports/profit-loss" : null,
  );
  const tb = useFetch<TrialRow[]>(
    can("accounting.report.read") ? "/api/v1/accounting/reports/trial-balance" : null,
  );
  const journal = useFetch<JournalRow[]>("/api/v1/accounting/journal?limit=40");

  const tbBalanced =
    tb.data && Math.abs(tb.data.reduce((s, r) => s + r.debit - r.credit, 0)) < 0.01;

  return (
    <>
      <PageHeader title="Accounting" subtitle="Double-entry ledger — every document posts a balanced journal" />
      <ErrorBanner message={pnl.error || journal.error} />

      {pnl.data && (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard label="Revenue" value={money(pnl.data.revenue)} tone="good" />
          <StatCard label="Expenses" value={money(pnl.data.expenses)} tone="bad" />
          <StatCard
            label="Net profit"
            value={money(pnl.data.net_profit)}
            tone={pnl.data.net_profit >= 0 ? "good" : "bad"}
          />
        </div>
      )}

      {tb.data && (
        <>
          <h2 className="mb-2 mt-8 flex items-center gap-2 font-semibold">
            Trial balance
            <span
              className={`text-xs font-normal ${tbBalanced ? "text-emerald-600" : "text-red-600"}`}
            >
              {tbBalanced ? "· balanced" : "· OUT OF BALANCE"}
            </span>
          </h2>
          <Table
            rows={tb.data}
            rowKey={(r) => r.code}
            columns={[
              { header: "Code", cell: (r) => r.code },
              { header: "Account", cell: (r) => r.name },
              { header: "Type", cell: (r) => r.type },
              { header: "Debit", className: "text-right", cell: (r) => money(r.debit) },
              { header: "Credit", className: "text-right", cell: (r) => money(r.credit) },
              {
                header: "Balance",
                className: "text-right",
                cell: (r) => money(r.balance),
              },
            ]}
          />
        </>
      )}

      <h2 className="mb-2 mt-8 font-semibold">Journal entries</h2>
      <Table
        rows={journal.data || []}
        rowKey={(r) => r.id}
        empty={journal.loading ? "Loading…" : "No entries"}
        columns={[
          { header: "Number", cell: (r) => r.number },
          { header: "Date", cell: (r) => date(r.date) },
          { header: "Description", cell: (r) => r.description },
          { header: "Status", cell: (r) => r.status },
          {
            header: "Amount",
            className: "text-right",
            cell: (r) => money(r.lines.reduce((s, l) => s + l.debit, 0)),
          },
        ]}
      />
    </>
  );
}
