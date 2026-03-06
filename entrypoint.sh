#!/bin/sh
set -e

# Ensure /app/data is writable (kept for any local file storage needs).
chown -R appuser:appgroup /app/data

# Wait for the database to accept connections before running migrations.
# Retries up to 30 times (30 s) — handles slow Postgres cold starts on Fly.
echo "Waiting for database..."
i=0
until gosu appuser python3 -c "
import os, sys, psycopg2
url = os.environ.get('DATABASE_URL', '')
if not url.startswith('postgres'):
    sys.exit(0)          # SQLite — nothing to wait for
url = url.replace('postgres://', 'postgresql://', 1)
try:
    psycopg2.connect(url).close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    i=$((i + 1))
    if [ "$i" -ge 30 ]; then
        echo "Database not reachable after 30 attempts — aborting." >&2
        exit 1
    fi
    echo "  attempt $i/30 — retrying in 1s..."
    sleep 1
done
echo "Database is ready."

# Apply any pending database migrations before accepting traffic.
gosu appuser alembic upgrade head

# WEB_WORKERS defaults to 2; override in docker-compose or Fly.io [env].
exec gosu appuser uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WEB_WORKERS:-2}"
