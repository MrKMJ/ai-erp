"use client";

import { MasterDataPage } from "@/components/MasterData";
import { money } from "@/lib/format";

export default function ProductsPage() {
  return (
    <MasterDataPage
      title="Products"
      subtitle="Items you stock, buy and sell"
      endpoint="/api/v1/products"
      readPerm="product.read"
      writePerm="product.write"
      columns={[
        { header: "SKU", key: "sku" },
        { header: "Name", key: "name" },
        {
          header: "Cost",
          key: "cost_price",
          className: "text-right",
          format: (v) => money(v as number),
        },
        {
          header: "Price",
          key: "selling_price",
          className: "text-right",
          format: (v) => money(v as number),
        },
        { header: "Reorder", key: "reorder_level", className: "text-right" },
        { header: "Safety", key: "safety_stock", className: "text-right" },
      ]}
      fields={[
        { name: "sku", label: "SKU", required: true },
        { name: "name", label: "Name", required: true },
        { name: "cost_price", label: "Cost price", type: "number", default: 0 },
        { name: "selling_price", label: "Selling price", type: "number", default: 0 },
        { name: "reorder_level", label: "Reorder level", type: "number", default: 0 },
        { name: "safety_stock", label: "Safety stock", type: "number", default: 0 },
        { name: "preferred_supplier_id", label: "Preferred supplier ID (optional)" },
      ]}
    />
  );
}
