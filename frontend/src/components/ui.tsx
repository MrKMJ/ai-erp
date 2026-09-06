"use client";

import { useEffect, useState } from "react";
import { useToast } from "@/lib/toast";
import { Icon } from "@/components/icons";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-fg sm:text-2xl">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

const TONES = {
  default: { text: "text-fg", bar: "bg-line", dot: "bg-faint" },
  good: { text: "text-emerald-600 dark:text-emerald-400", bar: "bg-emerald-500", dot: "bg-emerald-500" },
  bad: { text: "text-rose-600 dark:text-rose-400", bar: "bg-rose-500", dot: "bg-rose-500" },
  warn: { text: "text-amber-600 dark:text-amber-400", bar: "bg-amber-500", dot: "bg-amber-500" },
};

export function StatCard({
  label,
  value,
  tone = "default",
  hint,
}: {
  label: string;
  value: string;
  tone?: keyof typeof TONES;
  hint?: string;
}) {
  const t = TONES[tone];
  return (
    <div className="card relative overflow-hidden p-4">
      <span className={`absolute inset-y-0 left-0 w-1 ${t.bar}`} />
      <div className="pl-1.5">
        <div className="text-xs font-medium text-muted">{label}</div>
        <div className={`mt-1.5 text-2xl font-semibold tabular-nums tracking-tight ${t.text}`}>
          {value}
        </div>
        {hint && <div className="mt-1 text-xs text-faint">{hint}</div>}
      </div>
    </div>
  );
}

export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="mb-4 flex items-start gap-2 rounded-lg border border-rose-500/25 bg-rose-500/10 px-3.5 py-2.5 text-sm text-rose-700 dark:text-rose-300">
      <span className="mt-0.5 select-none">⚠</span>
      <span>{message}</span>
    </div>
  );
}

export function Table<T>({
  columns,
  rows,
  empty = "No records",
  rowKey,
}: {
  columns: { header: string; cell: (row: T) => React.ReactNode; className?: string }[];
  rows: T[];
  empty?: string;
  rowKey: (row: T, i: number) => string;
}) {
  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[640px]">
        <thead>
          <tr className="border-b border-line">
            {columns.map((c) => (
              <th key={c.header} className={`th ${c.className || ""}`}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td className="td text-center text-faint" colSpan={columns.length}>
                {empty}
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr key={rowKey(row, i)} className="transition-colors hover:bg-surface-2/60">
                {columns.map((c) => (
                  <td key={c.header} className={`td ${c.className || ""}`}>
                    {c.cell(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-[10vh] backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="card animate-fade-in w-full max-w-lg p-5 shadow-pop"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-fg">{title}</h2>
          <button onClick={onClose} className="btn-subtle !px-1.5 !py-1.5" aria-label="Close">
            <Icon.x width={16} height={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Badge({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <span className={`chip ${className}`}>{children}</span>;
}

export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
}: {
  tabs: readonly { id: T; label: string }[];
  value: T;
  onChange: (id: T) => void;
}) {
  return (
    <div className="mb-5 inline-flex rounded-lg border border-line bg-surface-2 p-0.5">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`rounded-[7px] px-3 py-1.5 text-sm font-medium transition-colors ${
            value === t.id
              ? "bg-surface text-fg shadow-card"
              : "text-muted hover:text-fg"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function useAsyncAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  async function run(fn: () => Promise<void>, okMessage?: string) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      if (okMessage) toast.success(okMessage);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Something went wrong";
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, setError, run };
}
