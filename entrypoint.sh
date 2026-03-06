#!/bin/sh
set -e

# Ensure /app/data is writable (kept for any local file storage needs).
chown -R appuser:appgroup /app/data

# Apply any pending database migrations before accepting traffic.
# Works with both SQLite (local dev) and PostgreSQL (Docker/production).
gosu appuser alembic upgrade head

# Start with multiple workers — safe now that PostgreSQL handles concurrency.
exec gosu appuser uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
