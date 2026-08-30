"use client";

import { useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader, Table, Modal, ErrorBanner, useAsyncAction } from "@/components/ui";
import { useFetch } from "@/lib/useFetch";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

export interface FieldDef {
  name: string;
  label: string;
  type?: "text" | "number" | "email";
  required?: boolean;
  default?: string | number;
}

export interface ColumnDef {
  header: string;
  key: string;
  format?: (v: unknown, row: Record<string, unknown>) => React.ReactNode;
  className?: string;
}

export function MasterDataPage({
  title,
  subtitle,
  endpoint,
  readPerm,
  writePerm,
  columns,
  fields,
}: {
  title: string;
  subtitle: string;
  endpoint: string;
  readPerm: string;
  writePerm: string;
  columns: ColumnDef[];
  fields: FieldDef[];
}) {
  return (
    <AppShell>
      <Inner
        title={title}
        subtitle={subtitle}
        endpoint={endpoint}
        readPerm={readPerm}
        writePerm={writePerm}
        columns={columns}
        fields={fields}
      />
    </AppShell>
  );
}

function Inner(props: {
  title: string;
  subtitle: string;
  endpoint: string;
  readPerm: string;
  writePerm: string;
  columns: ColumnDef[];
  fields: FieldDef[];
}) {
  const { can } = useAuth();
  const { data, error, loading, reload } = useFetch<Record<string, unknown>[]>(props.endpoint);
  const [open, setOpen] = useState(false);
  const [formVal, setFormVal] = useState<Record<string, string>>({});
  const action = useAsyncAction();

  function openForm() {
    const initial: Record<string, string> = {};
    props.fields.forEach((f) => {
      initial[f.name] = f.default !== undefined ? String(f.default) : "";
    });
    setFormVal(initial);
    action.setError(null);
    setOpen(true);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await action.run(async () => {
      const payload: Record<string, unknown> = {};
      props.fields.forEach((f) => {
        const raw = formVal[f.name];
        if (raw === "" || raw === undefined) return;
        payload[f.name] = f.type === "number" ? Number(raw) : raw;
      });
      await api(props.endpoint, { method: "POST", body: payload });
      setOpen(false);
      await reload();
    });
  }

  return (
    <>
      <PageHeader
        title={props.title}
        subtitle={props.subtitle}
        actions={
          can(props.writePerm) && (
            <button className="btn-primary" onClick={openForm}>
              + New
            </button>
          )
        }
      />
      <ErrorBanner message={error} />

      <Table
        rows={data || []}
        rowKey={(r, i) => String(r.id ?? i)}
        empty={loading ? "Loading…" : "No records yet"}
        columns={props.columns.map((c) => ({
          header: c.header,
          className: c.className,
          cell: (row: Record<string, unknown>) =>
            c.format ? c.format(row[c.key], row) : String(row[c.key] ?? "—"),
        }))}
      />

      <Modal open={open} onClose={() => setOpen(false)} title={`New ${props.title.replace(/s$/, "")}`}>
        <form onSubmit={submit} className="space-y-3">
          {props.fields.map((f) => (
            <div key={f.name}>
              <label className="label">
                {f.label}
                {f.required && " *"}
              </label>
              <input
                className="input"
                type={f.type === "number" ? "number" : f.type || "text"}
                step="any"
                required={f.required}
                value={formVal[f.name] ?? ""}
                onChange={(e) => setFormVal((v) => ({ ...v, [f.name]: e.target.value }))}
              />
            </div>
          ))}
          <ErrorBanner message={action.error} />
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" className="btn-ghost" onClick={() => setOpen(false)}>
              Cancel
            </button>
            <button className="btn-primary" disabled={action.busy}>
              {action.busy ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
