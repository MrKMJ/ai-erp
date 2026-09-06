# AI ERP

An AI-powered ERP for SME manufacturing / distribution, built to the provided
architecture blueprint. **Python/FastAPI backend** (this folder) + **Next.js
frontend** ([`frontend/`](frontend/README.md)).

**Design principle:** the ERP core is deterministic and auditable (double-entry
accounting, an append-only inventory ledger, RBAC, workflow approvals). The AI
sits *above* the ERP as an intelligence, prediction and controlled-action layer —
it selects tools, passes arguments and narrates results, but it never computes a
financial figure and never executes a sensitive action without the workflow
engine and a human.

## Stack

| Layer            | Choice                                             |
| ---------------- | -------------------------------------------------- |
| API              | FastAPI                                            |
| ORM / DB         | SQLAlchemy 2.0 · PostgreSQL (SQLite for dev)       |
| Auth             | OAuth2 password + JWT, granular RBAC               |
| AI orchestration | In-process AI Gateway + tool registry             |
| LLM provider     | `rule` (offline planner, default) or `anthropic`   |
| ML               | dependency-free forecasting / anomaly models       |
| Events           | in-process domain event bus                        |
| Frontend         | Next.js 14 (App Router) · TypeScript · Tailwind    |
| Packaging        | Docker + docker-compose (backend + Postgres)       |

## Quick start (local, zero setup)

```bash
cd ai-erp
python -m venv .venv && . .venv/Scripts/activate   # Windows
#   source .venv/bin/activate                       # macOS/Linux
pip install -r requirements.txt
python -m scripts.seed                               # demo tenant + 90 days of data
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs. Log in via `POST /api/v1/auth/login` with
`owner@demo.test` / `demo12345`, click **Authorize**, and explore.

Then start the UI:

```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL, defaults to http://localhost:8000
npm install
npm run dev                        # http://localhost:3000 (falls back to 3001 if taken)
```

`.env.local` is git-ignored and baked in at build time — restart `npm run dev` after
editing it. The backend's default CORS allows ports 3000–3002; see
[`frontend/README.md`](frontend/README.md) for other ports and deployed APIs.

## Quick start (Docker + Postgres + web)

```bash
docker compose up --build              # db + api (migrations auto-run) + web on :3000
docker compose run --rm api seed       # optional demo data
```

## Deploy

- **Free, no card** — push to GitHub, then Render **New → Blueprint** on the repo
  ([`render.yaml`](render.yaml): API + static frontend + Postgres).
- **Always-on** — `./deploy.sh` (Fly.io).

Full walkthrough, config reference and rollback in [DEPLOY.md](DEPLOY.md).

## Database migrations

Dev/SQLite auto-creates tables (`AUTO_CREATE_TABLES=true`). Everywhere else:

```bash
alembic upgrade head                   # apply
alembic revision --autogenerate -m "add X"   # after changing models
alembic check                          # CI: fails if models drifted from migrations
```

## Run tests

```bash
pip install pytest ruff
pytest && ruff check app scripts
```

## Deploy

See [DEPLOY.md](DEPLOY.md) — Fly.io (API + web + managed Postgres) with a GitHub
Actions pipeline. The image is a plain container and also runs on Render / Railway
/ ECS / Cloud Run.

## Enabling real LLM reasoning

```bash
pip install anthropic
export AI_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
export AI_MODEL=claude-sonnet-5
```

The gateway then runs a full tool-use loop with Claude; permission and risk gates
are unchanged. Without a key it transparently falls back to the rule planner.

## Module map

```
app/
  core/         config (prod-validated), db, security, RBAC catalogue,
                event bus, audit, middleware (request id / security headers /
                rate limit), structured logging, pagination
  models/       tenants, users, rbac, master data, sales, purchasing, inventory,
                accounting, manufacturing, ai, workflow, document_sequences
  services/     deterministic business logic
                  inventory_service     append-only ledger + cached balances
                  sales_service         order → deliver → invoice → payment (+ JEs)
                  purchasing_service    PO → approval → receipt (GRNI) → bill → pay
                  manufacturing_service BOM → production order → issue → finish (WIP)
                  accounting_service    double-entry engine, trial balance, P&L
                  forecasting           demand / stockout / cash-flow models
                  anomaly               supplier price & expense outliers
                  recommendations       turns analysis into AIRecommendation rows
                  numbering             gap-free locked document sequences
  ai/
    tools.py        explicit tool layer over the services (permission + risk)
    gateway.py      the single AI entry point: auth, policy, audit, execution
    llm.py          RuleProvider (offline) / AnthropicProvider (tool-use loop)
    subscribers.py  domain events → AI reactions
  api/routes/    auth, master-data, sales, purchasing, inventory, manufacturing,
                 accounting, ai
alembic/         migrations   ·   frontend/   Next.js UI   ·   DEPLOY.md
```

## AI safety model

* Every tool call is written to `ai_tool_calls` (who, which tool, args, result, model).
* The AI can only invoke tools the **calling user** is authorized for.
* Tools are risk-classified: `read` runs freely; `low` (draft creation) needs the
  `ai.action` permission; `medium`+ must be executed by a human.
* AI-created purchase orders are always drafts routed through the approval
  workflow — the AI cannot approve or pay them.
* Tool results and documents are treated as data, never as instructions
  (prompt-injection isolation).

## Key endpoints

| Area        | Endpoint                                             |
| ----------- | --------------------------------------------------- |
| Auth        | `POST /api/v1/auth/register` · `/login` · `/me`     |
| Sales       | `POST /api/v1/sales/orders` → `/confirm` → `/deliver-invoice` |
| Purchasing  | `POST /api/v1/purchasing/orders` → `/submit` → `/receive` → `/bill` → `/pay` |
| Inventory   | `GET /api/v1/inventory/position` · `/ledger` · `/forecast/{id}` |
| Manufacturing | `POST /api/v1/manufacturing/boms` · `/orders` → `/release` → `/issue-materials` → `/complete` |
| Accounting  | `GET /api/v1/accounting/reports/profit-loss` · `/trial-balance` |
| AI          | `POST /api/v1/ai/chat` · `/execute` · `GET /ai/recommendations` · `POST /ai/monitor/run` |

## Accounting flows

Every document posts a balanced journal entry; posted entries are reversed, never
edited. Purchasing uses **GRNI** (Goods Received Not Invoiced): receipt posts
`DR Inventory / CR GRNI`, billing clears it `DR GRNI / CR AP`. Manufacturing uses
a **WIP** account: material issue `DR WIP / CR Inventory`, completion
`DR Inventory / CR WIP` at accumulated cost.

## Not built yet (architecture roadmap)

RAG document Q&A, document OCR / invoice extraction, MRP planning across BOM
levels, specialised autonomous agents. The extension points (event bus, tool
registry, recommendation entity, agent-ready gateway) are in place. Forecasting /
anomaly models are statistical baselines — swap for scikit-learn / XGBoost /
Prophet behind the same service interface.
