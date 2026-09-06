export function money(n: number | string | null | undefined, currency = "USD"): string {
  const v = typeof n === "string" ? parseFloat(n) : n ?? 0;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(v || 0);
}

export function num(n: number | string | null | undefined): string {
  const v = typeof n === "string" ? parseFloat(n) : n ?? 0;
  return new Intl.NumberFormat("en-US").format(v || 0);
}

export function date(s: string | null | undefined): string {
  if (!s) return "—";
  return new Date(s).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

/** Dark-aware chip palettes, keyed by a small set of semantic tones. */
export const chipTone: Record<string, string> = {
  neutral: "border-line bg-surface-2 text-muted",
  brand: "border-brand-500/25 bg-brand-500/10 text-brand-700 dark:text-brand-300",
  info: "border-sky-500/25 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  good: "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  warn: "border-amber-500/25 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  bad: "border-rose-500/25 bg-rose-500/10 text-rose-700 dark:text-rose-300",
};

const STATUS_TONE: Record<string, keyof typeof chipTone> = {
  draft: "neutral",
  planned: "neutral",
  pending_approval: "warn",
  in_progress: "warn",
  confirmed: "info",
  released: "info",
  approved: "info",
  received: "info",
  invoiced: "good",
  posted: "good",
  paid: "good",
  billed: "good",
  done: "good",
  cancelled: "bad",
  void: "bad",
  rejected: "bad",
};

export const statusChip = (status: string): string =>
  chipTone[STATUS_TONE[status] ?? "neutral"];

export const SEVERITY_STYLES: Record<string, string> = {
  high: chipTone.bad,
  medium: chipTone.warn,
  low: chipTone.info,
  info: chipTone.neutral,
};
