"use client";

import AppShell from "@/components/AppShell";
import { PageHeader, Table, Badge, ErrorBanner } from "@/components/ui";
import { useFetch } from "@/lib/useFetch";
import { money, num, date, chipTone } from "@/lib/format";
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

      <h2 className="mb-3 text-sm font-semibold text-fg">Stock position</h2>
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
                <Badge className={chipTone.warn}>below reorder</Badge>
              ) : (
                <Badge className={chipTone.good}>ok</Badge>
              ),
          },
        ]}
      />

      <h2 className="mb-3 mt-8 text-sm font-semibold text-fg">Recent movements</h2>
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
              <span className={r.quantity < 0 ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"}>
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
