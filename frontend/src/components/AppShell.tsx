"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { Icon, type IconName } from "@/components/icons";
import ThemeToggle from "@/components/ThemeToggle";

const NAV: { href: string; label: string; perm: string | null; icon: IconName }[] = [
  { href: "/", label: "Dashboard", perm: null, icon: "dashboard" },
  { href: "/ai", label: "AI Command Center", perm: "ai.chat", icon: "sparkles" },
  { href: "/sales", label: "Sales", perm: "sales.read", icon: "sales" },
  { href: "/purchasing", label: "Purchasing", perm: "purchase.read", icon: "purchasing" },
  { href: "/manufacturing", label: "Manufacturing", perm: "manufacturing.read", icon: "manufacturing" },
  { href: "/inventory", label: "Inventory", perm: "inventory.read", icon: "inventory" },
  { href: "/accounting", label: "Accounting", perm: "accounting.read", icon: "accounting" },
  { href: "/customers", label: "Customers", perm: "customer.read", icon: "customers" },
  { href: "/suppliers", label: "Suppliers", perm: "supplier.read", icon: "suppliers" },
  { href: "/products", label: "Products", perm: "product.read", icon: "products" },
];

function BrandMark() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-sm">
        <Icon.spark width={16} height={16} />
      </div>
      <div className="leading-tight">
        <div className="text-sm font-semibold tracking-tight text-fg">AI ERP</div>
        <div className="text-[11px] text-faint">deterministic core · AI layer</div>
      </div>
    </div>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { me, loading, logout, can } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [drawer, setDrawer] = useState(false);

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);
  useEffect(() => setDrawer(false), [pathname]);

  if (loading || !me) {
    return (
      <div className="grid h-screen place-items-center">
        <div className="flex items-center gap-2 text-sm text-faint">
          <span className="h-2 w-2 animate-ping rounded-full bg-brand-500" />
          Loading…
        </div>
      </div>
    );
  }

  const items = NAV.filter((n) => !n.perm || can(n.perm));

  const sidebar = (
    <div className="flex h-full flex-col gap-1 p-3">
      <div className="px-2 pb-3 pt-1">
        <BrandMark />
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto">
        {items.map((n) => {
          const active = n.href === "/" ? pathname === "/" : pathname.startsWith(n.href);
          return (
            <Link
              key={n.href}
              href={n.href}
              className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-brand-500/10 text-brand-700 dark:text-brand-300"
                  : "text-muted hover:bg-surface-2 hover:text-fg"
              }`}
            >
              <span className={active ? "text-brand-600 dark:text-brand-400" : "text-faint group-hover:text-muted"}>
                {(() => {
                  const C = Icon[n.icon];
                  return <C />;
                })()}
              </span>
              {n.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-2 rounded-lg border border-line bg-surface-2/60 p-3">
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-500/15 text-xs font-semibold text-brand-700 dark:text-brand-300">
            {(me.full_name || me.email).slice(0, 2).toUpperCase()}
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-medium text-fg">{me.full_name || me.email}</div>
            <div className="truncate text-[11px] text-faint">{me.roles.join(", ") || "—"}</div>
          </div>
        </div>
        <button onClick={logout} className="btn-subtle mt-2 w-full !justify-start !px-2">
          <Icon.logout width={15} height={15} /> Sign out
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-bg">
      <aside className="hidden w-64 shrink-0 border-r border-line bg-surface md:block">
        {sidebar}
      </aside>

      {drawer && (
        <div className="fixed inset-0 z-40 md:hidden" onClick={() => setDrawer(false)}>
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
          <aside
            className="animate-fade-in absolute left-0 top-0 h-full w-72 border-r border-line bg-surface"
            onClick={(e) => e.stopPropagation()}
          >
            {sidebar}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line bg-bg/80 px-4 py-2.5 backdrop-blur md:justify-end md:px-6">
          <button
            className="btn-subtle !px-2 !py-2 md:hidden"
            onClick={() => setDrawer(true)}
            aria-label="Open menu"
          >
            <Icon.menu />
          </button>
          <div className="md:hidden">
            <BrandMark />
          </div>
          <ThemeToggle />
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
