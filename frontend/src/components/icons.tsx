import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement>;

function S({ children, ...p }: P & { children: React.ReactNode }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...p}
    >
      {children}
    </svg>
  );
}

export const Icon = {
  dashboard: (p: P) => (
    <S {...p}>
      <rect x="3" y="3" width="8" height="10" rx="1.5" />
      <rect x="3" y="17" width="8" height="4" rx="1.5" />
      <rect x="15" y="11" width="6" height="10" rx="1.5" />
      <rect x="15" y="3" width="6" height="4" rx="1.5" />
    </S>
  ),
  sparkles: (p: P) => (
    <S {...p}>
      <path d="M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6z" />
      <path d="M19 14l.8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8z" />
    </S>
  ),
  sales: (p: P) => (
    <S {...p}>
      <path d="M6 2h9l3 3v15a1 1 0 0 1-1.4.9L14 19l-2 1.5L10 19l-2.6 1.9A1 1 0 0 1 6 20z" />
      <path d="M9 8h6M9 12h6" />
    </S>
  ),
  purchasing: (p: P) => (
    <S {...p}>
      <circle cx="9" cy="20" r="1.4" />
      <circle cx="18" cy="20" r="1.4" />
      <path d="M2 3h2.2l2.4 12.2a2 2 0 0 0 2 1.6h8.6a2 2 0 0 0 2-1.6L22 7H6" />
    </S>
  ),
  manufacturing: (p: P) => (
    <S {...p}>
      <path d="M3 21V9l6 4V9l6 4V6l6 4v11z" />
      <path d="M3 21h18" />
    </S>
  ),
  inventory: (p: P) => (
    <S {...p}>
      <path d="M3 8l9-5 9 5-9 5z" />
      <path d="M3 8v8l9 5 9-5V8" />
      <path d="M12 13v8" />
    </S>
  ),
  accounting: (p: P) => (
    <S {...p}>
      <rect x="5" y="3" width="14" height="18" rx="2" />
      <path d="M9 7h6M9 11h2M13 11h2M9 15h2M13 15h2" />
    </S>
  ),
  customers: (p: P) => (
    <S {...p}>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
      <path d="M16 3.5a3 3 0 0 1 0 5.8M21 20c0-2.6-1.6-4.8-4-5.6" />
    </S>
  ),
  suppliers: (p: P) => (
    <S {...p}>
      <path d="M2 7h11v10H2z" />
      <path d="M13 10h4l4 4v3h-8z" />
      <circle cx="7" cy="18" r="1.6" />
      <circle cx="17" cy="18" r="1.6" />
    </S>
  ),
  products: (p: P) => (
    <S {...p}>
      <path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10z" />
      <circle cx="8.5" cy="8.5" r="1.6" />
    </S>
  ),
  sun: (p: P) => (
    <S {...p}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19" />
    </S>
  ),
  moon: (p: P) => (
    <S {...p}>
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </S>
  ),
  menu: (p: P) => (
    <S {...p}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </S>
  ),
  x: (p: P) => (
    <S {...p}>
      <path d="M6 6l12 12M18 6 6 18" />
    </S>
  ),
  logout: (p: P) => (
    <S {...p}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="M16 17l5-5-5-5M21 12H9" />
    </S>
  ),
  send: (p: P) => (
    <S {...p}>
      <path d="M22 2 11 13" />
      <path d="M22 2 15 22l-4-9-9-4z" />
    </S>
  ),
  spark: (p: P) => (
    <S {...p}>
      <path d="M13 2 3 14h7l-1 8 10-12h-7z" />
    </S>
  ),
};

export type IconName = keyof typeof Icon;
