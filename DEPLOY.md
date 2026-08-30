# Deploying AI ERP to production (Fly.io)

Two Fly apps + one managed Postgres:

| App           | Source          | URL (example)                 |
| ------------- | --------------- | ----------------------------- |
| `ai-erp-api`  | repo root       | `https://ai-erp-api.fly.dev`  |
| `ai-erp-web`  | `frontend/`     | `https://ai-erp-web.fly.dev`  |
| `ai-erp-db`   | Fly Postgres    | internal only                 |

> These are the only steps that need **your** credentials — an assistant cannot
> create the Fly account, hold the API token, or run `fly auth login` for you.

## 0. One-time

```bash
brew install flyctl          # or: curl -L https://fly.io/install.sh | sh
fly auth login
```

## 1. Database

```bash
fly postgres create --name ai-erp-db --region iad --vm-size shared-cpu-1x --volume-size 10
```

## 2. API

```bash
# from repo root
fly launch --no-deploy --copy-config --name ai-erp-api --region iad
fly postgres attach ai-erp-db --app ai-erp-api        # sets DATABASE_URL secret

fly secrets set --app ai-erp-api \
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" \
  CORS_ORIGINS="https://ai-erp-web.fly.dev"

# optional: real LLM instead of the offline planner
fly secrets set --app ai-erp-api AI_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-...

fly deploy --app ai-erp-api        # release_command runs `alembic upgrade head`
```

Seed a demo tenant once (optional):

```bash
fly ssh console --app ai-erp-api -C "python -m scripts.seed"
```

## 3. Web

```bash
cd frontend
fly launch --no-deploy --copy-config --name ai-erp-web --region iad
fly deploy --app ai-erp-web --build-arg NEXT_PUBLIC_API_URL=https://ai-erp-api.fly.dev
```

`NEXT_PUBLIC_API_URL` is compiled into the bundle — re-run this deploy (with the
build-arg) whenever the API URL changes.

## 4. CI/CD (GitHub Actions)

`.github/workflows/ci.yml` runs tests + lint + frontend build + `alembic check` on
every push/PR. `.github/workflows/deploy.yml` deploys both apps after CI passes on
`main`. Add one repo secret:

```bash
fly tokens create deploy -x 999999h        # copy the output
# GitHub → repo → Settings → Secrets and variables → Actions → New secret
#   name: FLY_API_TOKEN   value: <token>
```

Then every green push to `main` deploys. Trigger manually from the Actions tab
(`workflow_dispatch`) if needed.

## Configuration reference

Production config is validated at boot (`app/core/config.py`) — the API refuses to
start if any of these are wrong when `APP_ENV=production`:

| Var                 | Required in prod | Notes |
| ------------------- | ---------------- | ----- |
| `SECRET_KEY`        | yes, ≥32 chars   | JWT signing |
| `DATABASE_URL`      | yes, PostgreSQL  | `postgresql+psycopg://…` |
| `AUTO_CREATE_TABLES`| must be `false`  | migrations only |
| `CORS_ORIGINS`      | yes              | comma-separated, the web origin |
| `ANTHROPIC_API_KEY` | if `AI_PROVIDER=anthropic` | |
| `LOG_JSON`          | recommended `true` | structured logs |
| `WEB_CONCURRENCY`   | default 2        | gunicorn workers |

## Rollback

```bash
fly releases --app ai-erp-api
fly deploy --app ai-erp-api --image <previous-image-ref>
```

Migrations are additive; roll application code back freely. To undo a schema
change, add a new `alembic` revision with the reversing `downgrade`, don't
hand-edit the database.

## Other targets

The API image is a plain Docker container (`ENTRYPOINT` runs migrations then
gunicorn) and works unchanged on Render, Railway, ECS, Cloud Run or a
`docker compose` host — only the `fly.toml` files are Fly-specific. `render.yaml`
equivalents: a Web Service from `Dockerfile`, a Static Site / Web Service from
`frontend/`, and a managed Postgres, wired with the same env vars above.
