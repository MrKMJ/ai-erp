"use client";

import { useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader, Table, Badge, Tabs, ErrorBanner, useAsyncAction } from "@/components/ui";
import { OrderForm } from "@/components/OrderForm";
import { useFetch } from "@/lib/useFetch";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { money, date, statusChip } from "@/lib/format";

const TABS = [
  { id: "orders", label: "Orders" },
  { id: "invoices", label: "Invoices" },
  { id: "receivables", label: "Receivables" },
] as const;

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

      <Tabs tabs={TABS} value={tab} onChange={setTab} />

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
                <Badge className={statusChip(r.status)}>{r.status}</Badge>
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
                <Badge className={statusChip(r.status)}>{r.status}</Badge>
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
                <span className={r.overdue ? "font-semibold text-rose-600 dark:text-rose-400" : ""}>
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
