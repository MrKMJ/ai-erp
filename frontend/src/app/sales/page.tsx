"use client";

import { useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader, Table, Badge, ErrorBanner, useAsyncAction } from "@/components/ui";
import { OrderForm } from "@/components/OrderForm";
import { useFetch } from "@/lib/useFetch";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { money, date } from "@/lib/format";

interface SO {
  id: string;
  number: string;
  status: string;
  total: number;
  order_date: string;
}
interface INV {
  id: string;
  number: string;
  status: string;
  total: number;
  amount_paid: number;
  due_date: string;
}
interface AR {
  invoice_number: string;
  customer: string;
  balance: number;
  due_date: string;
  overdue: boolean;
}

const STATUS_STYLE: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600 border-slate-200",
  confirmed: "bg-sky-100 text-sky-700 border-sky-200",
  invoiced: "bg-emerald-100 text-emerald-700 border-emerald-200",
  posted: "bg-emerald-100 text-emerald-700 border-emerald-200",
  paid: "bg-emerald-100 text-emerald-700 border-emerald-200",
};

export default function SalesPage() {
  return (
    <AppShell>
      <Inner />
    </AppShell>
  );
}

function Inner() {
  const { can } = useAuth();
  const [tab, setTab] = useState<"orders" | "invoices" | "receivables">("orders");
  const [formOpen, setFormOpen] = useState(false);
  const orders = useFetch<SO[]>("/api/v1/sales/orders");
  const invoices = useFetch<INV[]>(tab === "invoices" ? "/api/v1/sales/invoices" : null);
  const receivables = useFetch<AR[]>(tab === "receivables" ? "/api/v1/sales/receivables" : null);
  const action = useAsyncAction();

  async function act(id: string, path: string) {
    await action.run(async () => {
      await api(`/api/v1/sales/orders/${id}/${path}`, { method: "POST" });
      await orders.reload();
    });
  }

  return (
    <>
      <PageHeader
        title="Sales"
        subtitle="Quote → confirm → deliver & invoice → collect"
        actions={
          can("sales.order.write") && (
            <button className="btn-primary" onClick={() => setFormOpen(true)}>
              + New order
            </button>
          )
        }
      />
      <ErrorBanner message={action.error || orders.error} />

      <div className="mb-4 flex gap-1">
        {(["orders", "invoices", "receivables"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium capitalize ${
              tab === t ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "orders" && (
        <Table
          rows={orders.data || []}
          rowKey={(r) => r.id}
          empty={orders.loading ? "Loading…" : "No orders"}
          columns={[
            { header: "Number", cell: (r) => r.number },
            { header: "Date", cell: (r) => date(r.order_date) },
            {
              header: "Status",
              cell: (r) => (
                <Badge className={STATUS_STYLE[r.status] || STATUS_STYLE.draft}>{r.status}</Badge>
              ),
            },
            { header: "Total", className: "text-right", cell: (r) => money(r.total) },
            {
              header: "",
              className: "text-right",
              cell: (r) => (
                <div className="flex justify-end gap-1">
                  {r.status === "draft" && can("sales.order.write") && (
                    <button className="btn-ghost !py-1" onClick={() => act(r.id, "confirm")}>
                      Confirm
                    </button>
                  )}
                  {(r.status === "confirmed" || r.status === "draft") &&
                    can("sales.invoice.post") && (
                      <button
                        className="btn-primary !py-1"
                        onClick={() => act(r.id, "deliver-invoice")}
                      >
                        Deliver &amp; invoice
                      </button>
                    )}
                </div>
              ),
            },
          ]}
        />
      )}

      {tab === "invoices" && (
        <Table
          rows={invoices.data || []}
          rowKey={(r) => r.id}
          empty={invoices.loading ? "Loading…" : "No invoices"}
          columns={[
            { header: "Number", cell: (r) => r.number },
            { header: "Due", cell: (r) => date(r.due_date) },
            {
              header: "Status",
              cell: (r) => (
                <Badge className={STATUS_STYLE[r.status] || STATUS_STYLE.draft}>{r.status}</Badge>
              ),
            },
            { header: "Total", className: "text-right", cell: (r) => money(r.total) },
            { header: "Paid", className: "text-right", cell: (r) => money(r.amount_paid) },
          ]}
        />
      )}

      {tab === "receivables" && (
        <Table
          rows={receivables.data || []}
          rowKey={(r, i) => r.invoice_number + i}
          empty={receivables.loading ? "Loading…" : "Nothing outstanding"}
          columns={[
            { header: "Invoice", cell: (r) => r.invoice_number },
            { header: "Customer", cell: (r) => r.customer },
            { header: "Due", cell: (r) => date(r.due_date) },
            {
              header: "Balance",
              className: "text-right",
              cell: (r) => (
                <span className={r.overdue ? "font-semibold text-red-600" : ""}>
                  {money(r.balance)}
                </span>
              ),
            },
          ]}
        />
      )}

      <OrderForm
        kind="sales"
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onCreated={() => orders.reload()}
      />
    </>
  );
}
