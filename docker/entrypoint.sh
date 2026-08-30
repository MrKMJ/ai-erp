#!/usr/bin/env bash
set -euo pipefail

: "${PORT:=8000}"
: "${WEB_CONCURRENCY:=2}"

run_migrations() {
  echo "==> alembic upgrade head"
  alembic upgrade head
}

case "${1:-serve}" in
  migrate)
    run_migrations
    ;;
  seed)
    run_migrations
    python -m scripts.seed
    ;;
  serve)
    run_migrations
    echo "==> starting gunicorn on :${PORT} (${WEB_CONCURRENCY} workers)"
    exec gunicorn app.main:app \
      --worker-class uvicorn.workers.UvicornWorker \
      --workers "${WEB_CONCURRENCY}" \
      --bind "0.0.0.0:${PORT}" \
      --access-logfile - --error-logfile - \
      --timeout 60 --graceful-timeout 30
    ;;
  *)
    exec "$@"
    ;;
esac
