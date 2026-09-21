#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "Applying database migrations..."
  alembic upgrade head
else
  echo "Skipping migrations (RUN_MIGRATIONS!=1)."
fi

if [ "${RUN_SEED:-0}" = "1" ]; then
  echo "Seeding demo materials and printers (skipped if already seeded)..."
  python -m app.scripts.seed_printers
fi

echo "Starting API on 0.0.0.0:8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
