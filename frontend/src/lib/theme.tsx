"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark" | "system";
const KEY = "ai_erp_theme";

interface ThemeCtx {
  theme: Theme;
  resolved: "light" | "dark";
  setTheme: (t: Theme) => void;
  cycle: () => void;
}

const Ctx = createContext<ThemeCtx | null>(null);

function systemDark(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function apply(theme: Theme) {
  const dark = theme === "dark" || (theme === "system" && systemDark());
  const root = document.documentElement;
  root.classList.toggle("dark", dark);
  root.classList.toggle("light", !dark);
}

/** Inlined in <head> so the theme is set before first paint (no flash). */
export const themeScript = `(function(){try{var t=localStorage.getItem("${KEY}")||"system";var d=t==="dark"||(t==="system"&&matchMedia("(prefers-color-scheme:dark)").matches);var c=document.documentElement.classList;c.toggle("dark",d);c.toggle("light",!d);}catch(e){}})();`;

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("system");
  const [resolved, setResolved] = useState<"light" | "dark">("light");

  useEffect(() => {
    let stored: Theme = "system";
    try {
      stored = (localStorage.getItem(KEY) as Theme) || "system";
    } catch {
      /* ignore */
    }
    setThemeState(stored);
    apply(stored);
    setResolved(document.documentElement.classList.contains("dark") ? "dark" : "light");

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if ((localStorage.getItem(KEY) as Theme) === "system" || !localStorage.getItem(KEY)) {
        apply("system");
        setResolved(document.documentElement.classList.contains("dark") ? "dark" : "light");
      }
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const setTheme = (t: Theme) => {
    setThemeState(t);
    try {
      localStorage.setItem(KEY, t);
    } catch {
      /* ignore */
    }
    apply(t);
    setResolved(document.documentElement.classList.contains("dark") ? "dark" : "light");
  };

  const cycle = () => setTheme(resolved === "dark" ? "light" : "dark");

  return <Ctx.Provider value={{ theme, resolved, setTheme, cycle }}>{children}</Ctx.Provider>;
}

export function useTheme(): ThemeCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
