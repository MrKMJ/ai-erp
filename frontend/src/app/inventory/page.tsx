"use client";

import AppShell from "@/components/AppShell";
import { PageHeader, Table, Badge, ErrorBanner } from "@/components/ui";
import { useFetch } from "@/lib/useFetch";
import { money, num, date } from "@/lib/format";
import type { InventoryRow } from "@/lib/types";

interface LedgerRow {
  id: string;
  product_id: string;
  type: string;
  quantity: number;
  unit_cost: number;
  reference_type: string | null;
  created_at: string;
}

export default function InventoryPage() {
  return (
    <AppShell>
      <Inner />
    </AppShell>
  );
}

function Inner() {
  const position = useFetch<InventoryRow[]>("/api/v1/inventory/position");
  const ledger = useFetch<LedgerRow[]>("/api/v1/inventory/ledger?limit=50");

  return (
    <>
      <PageHeader title="Inventory" subtitle="Positions are derived from an append-only ledger" />
      <ErrorBanner message={position.error} />

      <h2 className="mb-2 font-semibold">Stock position</h2>
      <Table
        rows={position.data || []}
        rowKey={(r) => r.product_id}
        empty={position.loading ? "Loading…" : "No stock"}
        columns={[
          { header: "SKU", cell: (r) => r.sku },
          { header: "Product", cell: (r) => r.name },
          { header: "On hand", className: "text-right", cell: (r) => num(r.on_hand) },
          { header: "Reorder", className: "text-right", cell: (r) => num(r.reorder_level) },
          { header: "Avg cost", className: "text-right", cell: (r) => money(r.avg_cost) },
          {
            header: "Status",
            cell: (r) =>
              r.below_reorder ? (
                <Badge className="bg-amber-100 text-amber-800 border-amber-200">below reorder</Badge>
              ) : (
                <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">ok</Badge>
              ),
          },
        ]}
      />

      <h2 className="mb-2 mt-8 font-semibold">Recent movements</h2>
      <Table
        rows={ledger.data || []}
        rowKey={(r) => r.id}
        empty={ledger.loading ? "Loading…" : "No movements"}
        columns={[
          { header: "Date", cell: (r) => date(r.created_at) },
          { header: "Type", cell: (r) => r.type },
          {
            header: "Qty",
            className: "text-right",
            cell: (r) => (
              <span className={r.quantity < 0 ? "text-red-600" : "text-emerald-600"}>
                {r.quantity > 0 ? "+" : ""}
                {num(r.quantity)}
              </span>
            ),
          },
          { header: "Unit cost", className: "text-right", cell: (r) => money(r.unit_cost) },
          { header: "Reference", cell: (r) => r.reference_type || "—" },
        ]}
      />
    </>
  );
}
