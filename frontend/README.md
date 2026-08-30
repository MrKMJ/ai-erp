# AI ERP — Frontend

Next.js 14 (App Router) + TypeScript + Tailwind. Talks to the FastAPI backend over REST
with a JWT held in `localStorage`.

## Run

```bash
cd frontend
cp .env.local.example .env.local     # points at http://localhost:8000 by default
npm install
npm run dev                           # http://localhost:3000
```

The backend must be running (`uvicorn app.main:app` in the parent folder) and seeded
(`python -m scripts.seed`). Log in with **owner@demo.test / demo12345**.

## What's here

| Route          | Purpose |
| -------------- | ------- |
| `/login`       | Password login → JWT |
| `/`            | Dashboard: KPI cards + recommendations feed + embedded AI chat |
| `/ai`          | AI Command Center: recommendations, tool catalogue (with your access), full chat with expandable tool-evidence |
| `/sales`       | Orders (confirm / deliver & invoice), invoices, receivables |
| `/purchasing`  | POs (submit / receive / bill), approval queue (AI-raised POs flagged), bills (pay), payables |
| `/inventory`   | Stock position with reorder flags, movement ledger |
| `/accounting`  | P&L, trial balance (with balanced check), journal entries |
| `/customers` `/suppliers` `/products` | Master-data lists + create |

The sidebar and in-page actions are **permission-aware** — they render only what your
role allows, mirroring the backend RBAC. Traditional ERP screens and the AI interface
live side by side (blueprint §46): use the tables when precision matters, ask the AI
when you want analysis.

## Notes

- ESLint is not wired into `next build` (no `eslint-config-next` dependency) — see
  `next.config.mjs`. TypeScript type-checking still runs.
- Auth is client-side only (JWT in `localStorage`); there is no SSR-protected route.
