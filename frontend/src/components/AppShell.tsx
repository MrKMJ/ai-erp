"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/", label: "Dashboard", perm: null },
  { href: "/ai", label: "AI Command Center", perm: "ai.chat" },
  { href: "/sales", label: "Sales", perm: "sales.read" },
  { href: "/purchasing", label: "Purchasing", perm: "purchase.read" },
  { href: "/manufacturing", label: "Manufacturing", perm: "manufacturing.read" },
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
  const [drawer, setDrawer] = useState(false);

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);

  useEffect(() => {
    setDrawer(false);
  }, [pathname]);

  if (loading || !me) {
    return <div className="flex h-screen items-center justify-center text-slate-400">Loading…</div>;
  }

  const items = NAV.filter((n) => !n.perm || can(n.perm));

  const sidebar = (
    <div className="flex h-full flex-col p-4">
      <div className="mb-6 px-2">
        <div className="text-lg font-bold text-brand-700">AI ERP</div>
        <div className="text-xs text-slate-400">deterministic core · AI layer</div>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto">
        {items.map((n) => {
          const active = n.href === "/" ? pathname === "/" : pathname.startsWith(n.href);
          return (
            <Link
              key={n.href}
              href={n.href}
              className={`block rounded-lg px-3 py-2 text-sm font-medium ${
                active ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
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
    </div>
  );

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white md:block">
        {sidebar}
      </aside>

      {drawer && (
        <div className="fixed inset-0 z-40 md:hidden" onClick={() => setDrawer(false)}>
          <div className="absolute inset-0 bg-slate-900/40" />
          <aside
            className="absolute left-0 top-0 h-full w-64 border-r border-slate-200 bg-white"
            onClick={(e) => e.stopPropagation()}
          >
            {sidebar}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 md:hidden">
          <button
            className="btn-ghost !px-2 !py-1"
            onClick={() => setDrawer(true)}
            aria-label="Open menu"
          >
            ☰
          </button>
          <span className="font-bold text-brand-700">AI ERP</span>
        </header>
        <main className="flex-1 overflow-x-hidden p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
