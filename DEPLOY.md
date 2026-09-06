# Deploying AI ERP

Two supported paths. Both give you an HTTPS API + web app + Postgres.

| | Cost | Card required | Notes |
|---|---|---|---|
| **A. Render** (blueprint) | free | no | API sleeps after 15 min idle (~50s cold start); free Postgres expires in 30 days |
| **B. Fly.io** (`deploy.sh`) | ~$3–5/mo | yes | always-on, no expiry |

The app image and config are platform-neutral — it also runs on Railway, Koyeb,
Cloud Run, ECS, or any `docker compose` host.

---

## A. Render — free, no credit card

Everything from **one Render account**, driven by [`render.yaml`](render.yaml):
an API web service (Docker), a static site (Next export), and a Postgres.

### 1. Put the repo on GitHub

```bash
# create an empty repo at github.com/new (name it e.g. ai-erp), then:
git remote add origin https://github.com/<you>/ai-erp.git
git push -u origin master
```

### 2. Deploy

1. [render.com](https://render.com) → sign up (GitHub login is easiest)
2. **New → Blueprint** → pick the `ai-erp` repo → **Apply**
3. Render reads `render.yaml` and creates `ai-erp-db`, `ai-erp-api`, `ai-erp-web`.
   First build takes a few minutes; the API runs `alembic upgrade head` on boot.

### 3. Seed a demo tenant (optional)

Render dashboard → **ai-erp-api → Shell**:

```bash
python -m scripts.seed
```

Then open `https://ai-erp-web.onrender.com` and log in with
`owner@demo.test` / `demo12345`.

### Free-tier realities

- **Cold start** — the API sleeps after 15 min idle; the next request wakes it in
  ~50s. The frontend retries automatically with backoff, so the first page load
  after idle just takes a while.
- **Postgres expiry** — Render's free database is deleted after 30 days. For a
  database that stays free forever, create one at **[neon.tech](https://neon.tech)**
  (no card) and set `DATABASE_URL` on the `ai-erp-api` service to its connection
  string. The app normalizes `postgres://` automatically. Then run
  `alembic upgrade head` from the API shell once.
- **Custom API/web names** — if `ai-erp-api` / `ai-erp-web` are taken, edit the
  names in `render.yaml` **and** the two cross-referencing URLs
  (`CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`) before applying the blueprint.

### Frontend elsewhere (also free, also no card)

`render.yaml` builds the frontend on Render, but the static export in
`frontend/out` works on any static host:

```bash
cd frontend && NEXT_OUTPUT=export NEXT_PUBLIC_API_URL=https://<your-api> npm run build
# then drag frontend/out into Netlify, or:  npx wrangler pages deploy out   (Cloudflare)
```

Set `CORS_ORIGINS` on the API to wherever the frontend ends up.

---

## B. Fly.io — always-on

flyctl is installed. One command after `fly auth login`:

```bash
fly auth login
./deploy.sh                 # creates apps + DB + secrets, deploys both
./deploy.sh --redeploy      # later, code-only
```

`deploy.sh` is idempotent. Manual equivalent:

```bash
fly postgres create --name ai-erp-db --region iad --vm-size shared-cpu-1x --volume-size 10
fly apps create ai-erp-api
fly postgres attach ai-erp-db --app ai-erp-api
fly secrets set --app ai-erp-api \
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" \
  CORS_ORIGINS="https://ai-erp-web.fly.dev"
fly deploy --app ai-erp-api          # release_command runs alembic upgrade head
cd frontend && fly apps create ai-erp-web && \
  fly deploy --app ai-erp-web --build-arg NEXT_PUBLIC_API_URL=https://ai-erp-api.fly.dev
```

---

## CI/CD (GitHub Actions)

`.github/workflows/ci.yml` runs tests + ruff + `alembic check` + frontend build on
every push/PR. `.github/workflows/deploy.yml` deploys to Fly after CI passes on
`main` — add repo secret `FLY_API_TOKEN` (`fly tokens create deploy -x 999999h`).
Render auto-deploys from GitHub on its own once the blueprint is applied.

## Configuration reference

The API validates these at boot when `APP_ENV=production` and refuses to start otherwise:

| Var | Required | Notes |
|---|---|---|
| `SECRET_KEY` | yes, ≥32 chars | JWT signing (Render `generateValue`) |
| `DATABASE_URL` | yes, Postgres | `postgres://` / `postgresql://` accepted |
| `AUTO_CREATE_TABLES` | must be `false` | migrations only |
| `CORS_ORIGINS` | yes | comma-separated; the web origin(s) |
| `AI_PROVIDER` | `rule` \| `anthropic` | `rule` needs no key |
| `ANTHROPIC_API_KEY` | if `anthropic` | |
| `LOG_JSON` | recommend `true` | structured logs |
| `WEB_CONCURRENCY` | default `2` | gunicorn workers |

## Rollback

- **Render**: dashboard → service → **Deploys** → *Rollback* to a prior deploy.
- **Fly**: `fly releases --app ai-erp-api` then `fly deploy --image <ref>`.

Migrations are additive; roll code back freely. To undo a schema change, add a new
Alembic revision with the reversing `downgrade` — don't hand-edit the database.
