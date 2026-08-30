"use client";

import { useState } from "react";
import { Modal, ErrorBanner, useAsyncAction } from "@/components/ui";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";

interface Party {
  id: string;
  code: string;
  name: string;
}
interface Product {
  id: string;
  sku: string;
  name: string;
  selling_price: number;
  cost_price: number;
}
interface Warehouse {
  id: string;
  code: string;
  name: string;
}

interface Line {
  product_id: string;
  quantity: string;
  price: string;
  tax_rate: string;
}

export function OrderForm({
  open,
  onClose,
  onCreated,
  kind,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  kind: "sales" | "purchase";
}) {
  const isSales = kind === "sales";
  const parties = useFetch<Party[]>(open ? (isSales ? "/api/v1/customers" : "/api/v1/suppliers") : null);
  const products = useFetch<Product[]>(open ? "/api/v1/products" : null);
  const warehouses = useFetch<Warehouse[]>(open ? "/api/v1/warehouses" : null);

  const [partyId, setPartyId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [lines, setLines] = useState<Line[]>([{ product_id: "", quantity: "1", price: "", tax_rate: "0" }]);
  const action = useAsyncAction();

  function reset() {
    setPartyId("");
    setWarehouseId("");
    setLines([{ product_id: "", quantity: "1", price: "", tax_rate: "0" }]);
    action.setError(null);
  }

  function updateLine(i: number, patch: Partial<Line>) {
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await action.run(async () => {
      const wh = warehouseId || warehouses.data?.[0]?.id;
      const payloadLines = lines
        .filter((l) => l.product_id && Number(l.quantity) > 0)
        .map((l) => ({
          product_id: l.product_id,
          quantity: Number(l.quantity),
          tax_rate: Number(l.tax_rate) || 0,
          ...(isSales
            ? l.price
              ? { unit_price: Number(l.price) }
              : {}
            : l.price
              ? { unit_cost: Number(l.price) }
              : {}),
        }));
      if (payloadLines.length === 0) throw new Error("Add at least one line");

      const body = isSales
        ? { customer_id: partyId, warehouse_id: wh, lines: payloadLines }
        : { supplier_id: partyId, warehouse_id: wh, lines: payloadLines };
      await api(isSales ? "/api/v1/sales/orders" : "/api/v1/purchasing/orders", {
        method: "POST",
        body,
      });
      reset();
      onClose();
      onCreated();
    });
  }

  return (
    <Modal open={open} onClose={onClose} title={isSales ? "New sales order" : "New purchase order"}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label">{isSales ? "Customer" : "Supplier"} *</label>
          <select className="input" required value={partyId} onChange={(e) => setPartyId(e.target.value)}>
            <option value="">Select…</option>
            {parties.data?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code} — {p.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Warehouse</label>
          <select className="input" value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)}>
            <option value="">Default</option>
            {warehouses.data?.map((w) => (
              <option key={w.id} value={w.id}>
                {w.code} — {w.name}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="label">Lines</label>
          {lines.map((l, i) => (
            <div key={i} className="grid grid-cols-[1fr_64px_72px_60px_auto] items-center gap-1.5">
              <select
                className="input"
                value={l.product_id}
                onChange={(e) => {
                  const p = products.data?.find((x) => x.id === e.target.value);
                  updateLine(i, {
                    product_id: e.target.value,
                    price: p ? String(isSales ? p.selling_price : p.cost_price) : "",
                  });
                }}
              >
                <option value="">Product…</option>
                {products.data?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.sku} — {p.name}
                  </option>
                ))}
              </select>
              <input
                className="input"
                type="number"
                step="any"
                min="0"
                value={l.quantity}
                onChange={(e) => updateLine(i, { quantity: e.target.value })}
                placeholder="Qty"
              />
              <input
                className="input"
                type="number"
                step="any"
                value={l.price}
                onChange={(e) => updateLine(i, { price: e.target.value })}
                placeholder={isSales ? "Price" : "Cost"}
              />
              <input
                className="input"
                type="number"
                step="any"
                value={l.tax_rate}
                onChange={(e) => updateLine(i, { tax_rate: e.target.value })}
                placeholder="Tax"
                title="Tax rate, e.g. 0.1 for 10%"
              />
              <button
                type="button"
                className="px-2 text-slate-400 hover:text-red-500"
                onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))}
              >
                ✕
              </button>
            </div>
          ))}
          <button
            type="button"
            className="text-sm text-brand-600 hover:underline"
            onClick={() =>
              setLines((ls) => [...ls, { product_id: "", quantity: "1", price: "", tax_rate: "0" }])
            }
          >
            + Add line
          </button>
        </div>

        <ErrorBanner message={action.error} />
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" disabled={action.busy}>
            {action.busy ? "Creating…" : "Create draft"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
