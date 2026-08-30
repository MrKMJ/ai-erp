"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/", label: "Dashboard", perm: null },
  { href: "/ai", label: "AI Command Center", perm: "ai.chat" },
  { href: "/sales", label: "Sales", perm: "sales.read" },
  { href: "/purchasing", label: "Purchasing", perm: "purchase.read" },
  { href: "/inventory", label: "Inventory", perm: "inventory.read" },
  { href: "/accounting", label: "Accounting", perm: "accounting.read" },
  { href: "/customers", label: "Customers", perm: "customer.read" },
  { href: "/suppliers", label: "Suppliers", perm: "supplier.read" },
  { href: "/products", label: "Products", perm: "product.read" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { me, loading, logout, can } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);

  if (loading || !me) {
    return (
      <div className="flex h-screen items-center justify-center text-slate-400">Loading…</div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-slate-200 bg-white p-4 md:flex">
        <div className="mb-6 px-2">
          <div className="text-lg font-bold text-brand-700">AI ERP</div>
          <div className="text-xs text-slate-400">deterministic core · AI layer</div>
        </div>
        <nav className="flex-1 space-y-1">
          {NAV.filter((n) => !n.perm || can(n.perm)).map((n) => {
            const active = n.href === "/" ? pathname === "/" : pathname.startsWith(n.href);
            return (
              <Link
                key={n.href}
                href={n.href}
                className={`block rounded-lg px-3 py-2 text-sm font-medium ${
                  active
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-4 border-t border-slate-100 pt-3">
          <div className="truncate px-2 text-sm font-medium text-slate-700">
            {me.full_name || me.email}
          </div>
          <div className="px-2 text-xs text-slate-400">{me.roles.join(", ") || "—"}</div>
          <button onClick={logout} className="mt-2 w-full btn-ghost">
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-x-hidden p-6">{children}</main>
    </div>
  );
}
