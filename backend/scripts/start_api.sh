#!/bin/sh
set -eu

cd /app

until alembic -c backend/alembic.ini upgrade head; do
  echo "waiting for database migrations"
  sleep 1
done

python -m backend.scripts.seed_base_data
python -m backend.scripts.seed_demo_data

exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
