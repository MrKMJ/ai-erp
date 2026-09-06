"use client";

import { useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader, Table, Badge, Tabs, Modal, ErrorBanner, useAsyncAction } from "@/components/ui";
import { useFetch } from "@/lib/useFetch";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { money, num, statusChip, chipTone } from "@/lib/format";

const TABS = [
  { id: "orders", label: "Production orders" },
  { id: "boms", label: "Bills of materials" },
] as const;

interface Product {
  id: string;
  sku: string;
  name: string;
}
interface Warehouse {
  id: string;
  code: string;
  name: string;
}
interface Bom {
  id: string;
  product_id: string;
  version: number;
  is_active: boolean;
  output_quantity: number;
  lines: { component_id: string; quantity: number; scrap_rate: number }[];
}
interface MO {
  id: string;
  number: string;
  product_id: string;
  status: string;
  quantity: number;
  quantity_produced: number;
  material_cost: number;
  source: string;
  planned_date: string;
}
interface MaterialRow {
  sku: string;
  name: string;
  required: number;
  issued: number;
  outstanding: number;
  on_hand: number;
  shortfall: number;
}

export default function ManufacturingPage() {
  return (
    <AppShell>
      <Inner />
    </AppShell>
  );
}

function Inner() {
  const { can } = useAuth();
  const [tab, setTab] = useState<"orders" | "boms">("orders");
  const [moForm, setMoForm] = useState(false);
  const [bomForm, setBomForm] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const orders = useFetch<MO[]>("/api/v1/manufacturing/orders");
  const boms = useFetch<Bom[]>("/api/v1/manufacturing/boms");
  const products = useFetch<Product[]>("/api/v1/products");
  const action = useAsyncAction();

  const productName = (id: string) => products.data?.find((p) => p.id === id)?.name ?? id;

  async function act(id: string, path: string, ok: string) {
    await action.run(async () => {
      await api(`/api/v1/manufacturing/orders/${id}/${path}`, { method: "POST" });
      await orders.reload();
    }, ok);
  }

  return (
    <>
      <PageHeader
        title="Manufacturing"
        subtitle="BOM → production order → issue materials → finished goods (with WIP accounting)"
        actions={
          <div className="flex gap-2">
            {can("manufacturing.bom.write") && (
              <button className="btn-ghost" onClick={() => setBomForm(true)}>
                + BOM
              </button>
            )}
            {can("manufacturing.order.write") && (
              <button className="btn-primary" onClick={() => setMoForm(true)}>
                + Production order
              </button>
            )}
          </div>
        }
      />
      <ErrorBanner message={action.error || orders.error} />

      <Tabs tabs={TABS} value={tab} onChange={setTab} />

      {tab === "orders" && (
        <div className="space-y-3">
          <Table
            rows={orders.data || []}
            rowKey={(r) => r.id}
            empty={orders.loading ? "Loading…" : "No production orders"}
            columns={[
              { header: "Number", cell: (r) => r.number },
              { header: "Product", cell: (r) => productName(r.product_id) },
              {
                header: "Source",
                cell: (r) =>
                  r.source === "ai" ? (
                    <Badge className={chipTone.brand}>AI</Badge>
                  ) : (
                    <span className="text-xs text-faint">user</span>
                  ),
              },
              {
                header: "Status",
                cell: (r) => (
                  <Badge className={statusChip(r.status)}>
                    {r.status.replace("_", " ")}
                  </Badge>
                ),
              },
              {
                header: "Qty",
                className: "text-right",
                cell: (r) => `${num(r.quantity_produced)} / ${num(r.quantity)}`,
              },
              {
                header: "Material cost",
                className: "text-right",
                cell: (r) => money(r.material_cost),
              },
              {
                header: "",
                className: "text-right",
                cell: (r) => (
                  <div className="flex justify-end gap-1">
                    <button
                      className="btn-ghost !py-1"
                      onClick={() => setExpanded(expanded === r.id ? null : r.id)}
                    >
                      Materials
                    </button>
                    {can("manufacturing.execute") && r.status === "planned" && (
                      <button
                        className="btn-ghost !py-1"
                        onClick={() => act(r.id, "release", `${r.number} released`)}
                      >
                        Release
                      </button>
                    )}
                    {can("manufacturing.execute") && r.status === "released" && (
                      <button
                        className="btn-ghost !py-1"
                        onClick={() => act(r.id, "issue-materials", "Materials issued")}
                      >
                        Issue materials
                      </button>
                    )}
                    {can("manufacturing.execute") && r.status === "in_progress" && (
                      <button
                        className="btn-primary !py-1"
                        onClick={() => act(r.id, "complete", "Finished goods received")}
                      >
                        Complete
                      </button>
                    )}
                  </div>
                ),
              },
            ]}
          />
          {expanded && <MaterialPanel orderId={expanded} />}
        </div>
      )}

      {tab === "boms" && (
        <Table
          rows={boms.data || []}
          rowKey={(r) => r.id}
          empty={boms.loading ? "Loading…" : "No BOMs"}
          columns={[
            { header: "Product", cell: (r) => productName(r.product_id) },
            { header: "Version", cell: (r) => `v${r.version}` },
            { header: "Output qty", className: "text-right", cell: (r) => num(r.output_quantity) },
            { header: "Components", className: "text-right", cell: (r) => r.lines.length },
            {
              header: "Active",
              cell: (r) =>
                r.is_active ? (
                  <Badge className={chipTone.good}>
                    active
                  </Badge>
                ) : (
                  <span className="text-xs text-faint">superseded</span>
                ),
            },
          ]}
        />
      )}

      <MoForm
        open={moForm}
        onClose={() => setMoForm(false)}
        onCreated={() => orders.reload()}
      />
      <BomForm
        open={bomForm}
        onClose={() => setBomForm(false)}
        onCreated={() => boms.reload()}
        products={products.data || []}
      />
    </>
  );
}

function MaterialPanel({ orderId }: { orderId: string }) {
  const { data, loading } = useFetch<MaterialRow[]>(
    `/api/v1/manufacturing/orders/${orderId}/materials`,
    [orderId],
  );
  return (
    <div className="card p-3">
      <div className="mb-2 text-sm font-semibold">Material requirements</div>
      <Table
        rows={data || []}
        rowKey={(r, i) => r.sku + i}
        empty={loading ? "Loading…" : "No materials"}
        columns={[
          { header: "SKU", cell: (r) => r.sku },
          { header: "Component", cell: (r) => r.name },
          { header: "Required", className: "text-right", cell: (r) => num(r.required) },
          { header: "Issued", className: "text-right", cell: (r) => num(r.issued) },
          { header: "On hand", className: "text-right", cell: (r) => num(r.on_hand) },
          {
            header: "Shortfall",
            className: "text-right",
            cell: (r) =>
              r.shortfall > 0 ? (
                <span className="font-semibold text-rose-600 dark:text-rose-400">{num(r.shortfall)}</span>
              ) : (
                <span className="text-emerald-600 dark:text-emerald-400">0</span>
              ),
          },
        ]}
      />
    </div>
  );
}

function MoForm({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const boms = useFetch<Bom[]>(open ? "/api/v1/manufacturing/boms" : null);
  const products = useFetch<Product[]>(open ? "/api/v1/products" : null);
  const warehouses = useFetch<Warehouse[]>(open ? "/api/v1/warehouses" : null);
  const [productId, setProductId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [quantity, setQuantity] = useState("10");
  const action = useAsyncAction();

  const withBom = new Set((boms.data || []).filter((b) => b.is_active).map((b) => b.product_id));
  const options = (products.data || []).filter((p) => withBom.has(p.id));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await action.run(async () => {
      await api("/api/v1/manufacturing/orders", {
        method: "POST",
        body: {
          product_id: productId,
          warehouse_id: warehouseId || warehouses.data?.[0]?.id,
          quantity: Number(quantity),
        },
      });
      onClose();
      onCreated();
    }, "Production order created");
  }

  return (
    <Modal open={open} onClose={onClose} title="New production order">
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="label">Product (must have an active BOM) *</label>
          <select
            className="input"
            required
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
          >
            <option value="">Select…</option>
            {options.map((p) => (
              <option key={p.id} value={p.id}>
                {p.sku} — {p.name}
              </option>
            ))}
          </select>
          {options.length === 0 && (
            <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
              No products have an active BOM yet — create one first.
            </p>
          )}
        </div>
        <div>
          <label className="label">Warehouse</label>
          <select
            className="input"
            value={warehouseId}
            onChange={(e) => setWarehouseId(e.target.value)}
          >
            <option value="">Default</option>
            {warehouses.data?.map((w) => (
              <option key={w.id} value={w.id}>
                {w.code} — {w.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Quantity to produce *</label>
          <input
            className="input"
            type="number"
            step="any"
            min="0"
            required
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
        </div>
        <ErrorBanner message={action.error} />
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" disabled={action.busy}>
            {action.busy ? "Creating…" : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function BomForm({
  open,
  onClose,
  onCreated,
  products,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  products: Product[];
}) {
  const [productId, setProductId] = useState("");
  const [outputQty, setOutputQty] = useState("1");
  const [lines, setLines] = useState<{ component_id: string; quantity: string; scrap_rate: string }[]>(
    [{ component_id: "", quantity: "1", scrap_rate: "0" }],
  );
  const action = useAsyncAction();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await action.run(async () => {
      const payloadLines = lines
        .filter((l) => l.component_id && Number(l.quantity) > 0)
        .map((l) => ({
          component_id: l.component_id,
          quantity: Number(l.quantity),
          scrap_rate: Number(l.scrap_rate) || 0,
        }));
      if (!payloadLines.length) throw new Error("Add at least one component");
      await api("/api/v1/manufacturing/boms", {
        method: "POST",
        body: { product_id: productId, output_quantity: Number(outputQty), lines: payloadLines },
      });
      setLines([{ component_id: "", quantity: "1", scrap_rate: "0" }]);
      onClose();
      onCreated();
    }, "BOM created");
  }

  return (
    <Modal open={open} onClose={onClose} title="New bill of materials">
      <form onSubmit={submit} className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="label">Finished product *</label>
            <select
              className="input"
              required
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
            >
              <option value="">Select…</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.sku} — {p.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Output qty / batch</label>
            <input
              className="input"
              type="number"
              step="any"
              min="0"
              value={outputQty}
              onChange={(e) => setOutputQty(e.target.value)}
            />
          </div>
        </div>
        <div className="space-y-2">
          <label className="label">Components</label>
          {lines.map((l, i) => (
            <div key={i} className="grid grid-cols-[1fr_70px_64px_auto] items-center gap-1.5">
              <select
                className="input"
                value={l.component_id}
                onChange={(e) =>
                  setLines((ls) =>
                    ls.map((x, idx) => (idx === i ? { ...x, component_id: e.target.value } : x)),
                  )
                }
              >
                <option value="">Component…</option>
                {products
                  .filter((p) => p.id !== productId)
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} — {p.name}
                    </option>
                  ))}
              </select>
              <input
                className="input"
                type="number"
                step="any"
                placeholder="Qty"
                value={l.quantity}
                onChange={(e) =>
                  setLines((ls) =>
                    ls.map((x, idx) => (idx === i ? { ...x, quantity: e.target.value } : x)),
                  )
                }
              />
              <input
                className="input"
                type="number"
                step="any"
                placeholder="Scrap"
                title="Scrap rate, e.g. 0.05"
                value={l.scrap_rate}
                onChange={(e) =>
                  setLines((ls) =>
                    ls.map((x, idx) => (idx === i ? { ...x, scrap_rate: e.target.value } : x)),
                  )
                }
              />
              <button
                type="button"
                className="px-2 text-faint hover:text-rose-500"
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
              setLines((ls) => [...ls, { component_id: "", quantity: "1", scrap_rate: "0" }])
            }
          >
            + Add component
          </button>
        </div>
        <ErrorBanner message={action.error} />
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" disabled={action.busy}>
            {action.busy ? "Saving…" : "Save BOM"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
