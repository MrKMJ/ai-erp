#!/usr/bin/env bash
# One-shot Fly.io deployment for AI ERP (API + web + managed Postgres).
#
#   ./deploy.sh              # first-time: creates apps, DB, secrets, deploys
#   ./deploy.sh --redeploy   # just re-deploy code to existing apps
#
# Requires: flyctl (https://fly.io/install.sh) and `fly auth login` already done.
# Nothing here needs editing — override names/region with env vars if you want:
#   API_APP=my-erp-api WEB_APP=my-erp-web DB_APP=my-erp-db REGION=lhr ./deploy.sh
set -euo pipefail

API_APP="${API_APP:-ai-erp-api}"
WEB_APP="${WEB_APP:-ai-erp-web}"
DB_APP="${DB_APP:-ai-erp-db}"
REGION="${REGION:-iad}"
API_URL="https://${API_APP}.fly.dev"
WEB_URL="https://${WEB_APP}.fly.dev"

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

command -v fly >/dev/null 2>&1 || { echo "flyctl not found — https://fly.io/install.sh"; exit 1; }
fly auth whoami >/dev/null 2>&1 || { echo "Run 'fly auth login' first."; exit 1; }

app_exists() { fly apps list 2>/dev/null | awk '{print $1}' | grep -qx "$1"; }

redeploy_only=false
[[ "${1:-}" == "--redeploy" ]] && redeploy_only=true

if ! $redeploy_only; then
  echo "==> Postgres ($DB_APP)"
  if ! app_exists "$DB_APP"; then
    fly postgres create --name "$DB_APP" --region "$REGION" \
      --vm-size shared-cpu-1x --volume-size 10 --initial-cluster-size 1
  fi

  echo "==> API app ($API_APP)"
  app_exists "$API_APP" || fly apps create "$API_APP"
  fly postgres attach "$DB_APP" --app "$API_APP" || true   # idempotent: sets DATABASE_URL

  echo "==> API secrets"
  if ! fly secrets list --app "$API_APP" 2>/dev/null | grep -q '^SECRET_KEY'; then
    SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))' 2>/dev/null \
      || head -c 48 /dev/urandom | base64 | tr -d '/+=' | head -c 64)"
    fly secrets set --app "$API_APP" SECRET_KEY="$SECRET_KEY"
  fi
  fly secrets set --app "$API_APP" CORS_ORIGINS="$WEB_URL"

  echo "==> web app ($WEB_APP)"
  app_exists "$WEB_APP" || fly apps create "$WEB_APP"
fi

echo "==> deploy API (release_command runs 'alembic upgrade head')"
fly deploy --app "$API_APP" --config fly.toml --remote-only

echo "==> deploy web (NEXT_PUBLIC_API_URL baked in at build time)"
( cd frontend && fly deploy --app "$WEB_APP" --config fly.toml --remote-only \
    --build-arg NEXT_PUBLIC_API_URL="$API_URL" )

if ! $redeploy_only; then
  read -r -p "Seed a demo tenant (owner@demo.test / demo12345)? [y/N] " ans
  [[ "${ans:-N}" =~ ^[Yy]$ ]] && fly ssh console --app "$API_APP" -C "python -m scripts.seed"
fi

echo
echo "Done."
echo "  API : $API_URL   (health: $API_URL/health)"
echo "  Web : $WEB_URL"
echo
echo "CI/CD: add repo secret FLY_API_TOKEN  ->  fly tokens create deploy -x 999999h"
