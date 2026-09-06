"use client";

import { useTheme } from "@/lib/theme";
import { Icon } from "@/components/icons";

export default function ThemeToggle({ className = "" }: { className?: string }) {
  const { resolved, cycle } = useTheme();
  return (
    <button
      onClick={cycle}
      aria-label={`Switch to ${resolved === "dark" ? "light" : "dark"} mode`}
      className={`btn-subtle !px-2 !py-2 ${className}`}
      title={`${resolved === "dark" ? "Light" : "Dark"} mode`}
    >
      {resolved === "dark" ? <Icon.sun /> : <Icon.moon />}
    </button>
  );
}
