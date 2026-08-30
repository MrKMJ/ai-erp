"use client";

import { MasterDataPage } from "@/components/MasterData";

export default function SuppliersPage() {
  return (
    <MasterDataPage
      title="Suppliers"
      subtitle="Vendors you buy from"
      endpoint="/api/v1/suppliers"
      readPerm="supplier.read"
      writePerm="supplier.write"
      columns={[
        { header: "Code", key: "code" },
        { header: "Name", key: "name" },
        { header: "Lead time", key: "lead_time_days", format: (v) => `${Number(v ?? 0)} days` },
        {
          header: "Reliability",
          key: "reliability",
          className: "text-right",
          format: (v) => `${(Number(v ?? 0) * 100).toFixed(0)}%`,
        },
        { header: "Terms", key: "payment_terms_days", format: (v) => `${Number(v ?? 0)} days` },
      ]}
      fields={[
        { name: "code", label: "Code", required: true },
        { name: "name", label: "Name", required: true },
        { name: "email", label: "Email", type: "email" },
        { name: "phone", label: "Phone" },
        { name: "lead_time_days", label: "Lead time (days)", type: "number", default: 14 },
        { name: "payment_terms_days", label: "Payment terms (days)", type: "number", default: 30 },
        { name: "reliability", label: "Reliability (0-1)", type: "number", default: 0.95 },
      ]}
    />
  );
}
