#!/bin/sh
set -e

# Ensure /app/data is writable (kept for any local file storage needs).
chown -R appuser:appgroup /app/data

# Apply any pending database migrations before accepting traffic.
# Works with both SQLite (local dev) and PostgreSQL (Docker/production).
gosu appuser alembic upgrade head

# WEB_WORKERS defaults to 2 (safe for 256 MB); override in docker-compose or
# Fly.io [env] for larger machines.
exec gosu appuser uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WEB_WORKERS:-2}"
