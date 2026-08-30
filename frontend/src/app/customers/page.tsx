"use client";

import { MasterDataPage } from "@/components/MasterData";
import { money } from "@/lib/format";

export default function CustomersPage() {
  return (
    <MasterDataPage
      title="Customers"
      subtitle="Accounts you sell to"
      endpoint="/api/v1/customers"
      readPerm="customer.read"
      writePerm="customer.write"
      columns={[
        { header: "Code", key: "code" },
        { header: "Name", key: "name" },
        { header: "Email", key: "email" },
        { header: "Terms", key: "payment_terms_days", format: (v) => `${Number(v ?? 0)} days` },
        {
          header: "Credit limit",
          key: "credit_limit",
          className: "text-right",
          format: (v) => money(v as number),
        },
        { header: "Status", key: "status" },
      ]}
      fields={[
        { name: "code", label: "Code", required: true },
        { name: "name", label: "Name", required: true },
        { name: "email", label: "Email", type: "email" },
        { name: "phone", label: "Phone" },
        { name: "payment_terms_days", label: "Payment terms (days)", type: "number", default: 30 },
        { name: "credit_limit", label: "Credit limit", type: "number", default: 0 },
      ]}
    />
  );
}
