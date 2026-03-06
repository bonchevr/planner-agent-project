#!/bin/sh
set -e

# When Docker mounts a named volume at /app/data, the directory AND any
# existing files (e.g. planner.db) may be owned by root. Fix recursively
# before dropping to appuser.
chown -R appuser:appgroup /app/data

exec gosu appuser uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1
