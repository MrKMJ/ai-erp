"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { API_URL } from "@/lib/api";
import { Icon } from "@/components/icons";
import ThemeToggle from "@/components/ThemeToggle";

export default function LoginPage() {
  const { login, me, loading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("owner@demo-erp.com");
  const [password, setPassword] = useState("demo12345");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && me) router.replace("/");
  }, [loading, me, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden p-4">
      <div
        className="pointer-events-none absolute -top-40 left-1/2 h-[36rem] w-[36rem] -translate-x-1/2 rounded-full opacity-40 blur-3xl"
        style={{ background: "radial-gradient(closest-side, rgb(99 102 241 / 0.5), transparent)" }}
      />
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>

      <div className="card animate-fade-in relative w-full max-w-sm p-7 shadow-pop">
        <div className="mb-6 flex items-center gap-2.5">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-sm">
            <Icon.spark width={18} height={18} />
          </div>
          <div>
            <div className="text-base font-semibold tracking-tight text-fg">AI ERP</div>
            <div className="text-xs text-faint">Sign in to your workspace</div>
          </div>
        </div>

        <form onSubmit={submit} className="space-y-3.5">
          <div>
            <label className="label">Email</label>
            <input
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              autoFocus
            />
          </div>
          <div>
            <label className="label">Password</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          {error && (
            <div className="rounded-lg border border-rose-500/25 bg-rose-500/10 px-3 py-2 text-sm text-rose-600 dark:text-rose-300">
              {error}
            </div>
          )}
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="mt-5 border-t border-line pt-4 text-center text-xs text-faint">
          <span className="font-medium text-muted">Demo</span> · owner@demo-erp.com / demo12345
          <div className="mt-1 truncate">API: {API_URL}</div>
        </div>
      </div>
    </div>
  );
}
