"use client";

import { useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader, Table, Badge, ErrorBanner, useAsyncAction } from "@/components/ui";
import { OrderForm } from "@/components/OrderForm";
import { useFetch } from "@/lib/useFetch";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { money } from "@/lib/format";

interface PO {
  id: string;
  number: string;
  status: string;
  total: number;
  source: string;
}
interface Approval {
  id: string;
  entity_type: string;
  reason: string;
  requested_by_kind: string;
  context: Record<string, unknown>;
}
interface Bill {
  id: string;
  number: string;
  status: string;
  total: number;
  amount_paid: number;
}
interface AP {
  bill_number: string;
  supplier: string;
  balance: number;
  overdue: boolean;
}

const STATUS_STYLE: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600 border-slate-200",
  pending_approval: "bg-amber-100 text-amber-800 border-amber-200",
  approved: "bg-sky-100 text-sky-700 border-sky-200",
  received: "bg-indigo-100 text-indigo-700 border-indigo-200",
  billed: "bg-emerald-100 text-emerald-700 border-emerald-200",
  posted: "bg-emerald-100 text-emerald-700 border-emerald-200",
  paid: "bg-emerald-100 text-emerald-700 border-emerald-200",
};

export default function PurchasingPage() {
  return (
    <AppShell>
      <Inner />
    </AppShell>
  );
}

function Inner() {
  const { can } = useAuth();
  const [tab, setTab] = useState<"orders" | "approvals" | "bills" | "payables">("orders");
  const [formOpen, setFormOpen] = useState(false);
  const orders = useFetch<PO[]>("/api/v1/purchasing/orders");
  const approvals = useFetch<Approval[]>(
    tab === "approvals" && can("purchase.order.approve") ? "/api/v1/purchasing/approvals" : null,
  );
  const bills = useFetch<Bill[]>(tab === "bills" ? "/api/v1/purchasing/bills" : null);
  const payables = useFetch<AP[]>(tab === "payables" ? "/api/v1/purchasing/payables" : null);
  const action = useAsyncAction();

  async function orderAct(id: string, path: string) {
    await action.run(async () => {
      await api(`/api/v1/purchasing/orders/${id}/${path}`, { method: "POST" });
      await orders.reload();
    });
  }
  async function decide(id: string, approve: boolean) {
    await action.run(async () => {
      await api(`/api/v1/purchasing/approvals/${id}/decide`, {
        method: "POST",
        body: { approve, note: approve ? "Approved via UI" : "Rejected via UI" },
      });
      await Promise.all([approvals.reload(), orders.reload()]);
    });
  }
  async function payBill(id: string) {
    await action.run(async () => {
      await api(`/api/v1/purchasing/bills/${id}/pay`, { method: "POST" });
      await bills.reload();
    });
  }

  return (
    <>
      <PageHeader
        title="Purchasing"
        subtitle="PO → approval → receipt → bill → pay. AI-created POs land here as drafts."
        actions={
          can("purchase.order.write") && (
            <button className="btn-primary" onClick={() => setFormOpen(true)}>
              + New PO
            </button>
          )
        }
      />
      <ErrorBanner message={action.error || orders.error} />

      <div className="mb-4 flex gap-1">
        {(["orders", "approvals", "bills", "payables"] as const).map((t) => (
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
          empty={orders.loading ? "Loading…" : "No purchase orders"}
          columns={[
            { header: "Number", cell: (r) => r.number },
            {
              header: "Source",
              cell: (r) =>
                r.source === "ai" ? (
                  <Badge className="bg-brand-50 text-brand-700 border-brand-100">AI</Badge>
                ) : (
                  <span className="text-xs text-slate-400">user</span>
                ),
            },
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
                  {r.status === "draft" && can("purchase.order.write") && (
                    <button className="btn-ghost !py-1" onClick={() => orderAct(r.id, "submit")}>
                      Submit
                    </button>
                  )}
                  {r.status === "approved" && can("purchase.receipt.write") && (
                    <button className="btn-ghost !py-1" onClick={() => orderAct(r.id, "receive")}>
                      Receive
                    </button>
                  )}
                  {r.status === "received" && can("purchase.bill.post") && (
                    <button className="btn-primary !py-1" onClick={() => orderAct(r.id, "bill")}>
                      Create bill
                    </button>
                  )}
                </div>
              ),
            },
          ]}
        />
      )}

      {tab === "approvals" && (
        <Table
          rows={approvals.data || []}
          rowKey={(r) => r.id}
          empty={
            !can("purchase.order.approve")
              ? "You cannot approve purchase orders"
              : approvals.loading
                ? "Loading…"
                : "Nothing awaiting approval"
          }
          columns={[
            { header: "Reason", cell: (r) => r.reason },
            {
              header: "Requested by",
              cell: (r) =>
                r.requested_by_kind === "ai" ? (
                  <Badge className="bg-brand-50 text-brand-700 border-brand-100">AI</Badge>
                ) : (
                  "user"
                ),
            },
            {
              header: "Amount",
              className: "text-right",
              cell: (r) => money(Number(r.context?.total ?? 0)),
            },
            {
              header: "",
              className: "text-right",
              cell: (r) => (
                <div className="flex justify-end gap-1">
                  <button className="btn-primary !py-1" onClick={() => decide(r.id, true)}>
                    Approve
                  </button>
                  <button className="btn-ghost !py-1" onClick={() => decide(r.id, false)}>
                    Reject
                  </button>
                </div>
              ),
            },
          ]}
        />
      )}

      {tab === "bills" && (
        <Table
          rows={bills.data || []}
          rowKey={(r) => r.id}
          empty={bills.loading ? "Loading…" : "No bills"}
          columns={[
            { header: "Number", cell: (r) => r.number },
            {
              header: "Status",
              cell: (r) => (
                <Badge className={STATUS_STYLE[r.status] || STATUS_STYLE.draft}>{r.status}</Badge>
              ),
            },
            { header: "Total", className: "text-right", cell: (r) => money(r.total) },
            { header: "Paid", className: "text-right", cell: (r) => money(r.amount_paid) },
            {
              header: "",
              className: "text-right",
              cell: (r) =>
                r.status === "posted" &&
                can("purchase.payment.create") && (
                  <button className="btn-primary !py-1" onClick={() => payBill(r.id)}>
                    Pay
                  </button>
                ),
            },
          ]}
        />
      )}

      {tab === "payables" && (
        <Table
          rows={payables.data || []}
          rowKey={(r, i) => r.bill_number + i}
          empty={payables.loading ? "Loading…" : "Nothing outstanding"}
          columns={[
            { header: "Bill", cell: (r) => r.bill_number },
            { header: "Supplier", cell: (r) => r.supplier },
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
        kind="purchase"
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onCreated={() => orders.reload()}
      />
    </>
  );
}
