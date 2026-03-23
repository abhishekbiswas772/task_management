#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SQLITE_PATH="${1:-$ROOT_DIR/tasks.db}"
CONTAINER_NAME="${APP_CONTAINER_NAME:-taskboard_app}"

if [[ ! -f "$SQLITE_PATH" ]]; then
  echo "SQLite database not found: $SQLITE_PATH" >&2
  exit 1
fi

docker cp "$SQLITE_PATH" "$CONTAINER_NAME:/app/tasks.db"

# Copy migration scripts into the container (excluded by .dockerignore)
docker exec --user root "$CONTAINER_NAME" rm -rf /app/migrations
docker cp "$ROOT_DIR/migrations" "$CONTAINER_NAME:/app/migrations"

docker exec \
  -e POSTGRES_HOST="${POSTGRES_HOST:-postgres}" \
  -e POSTGRES_PORT="${POSTGRES_PORT:-5432}" \
  -e POSTGRES_DB="${POSTGRES_DB:-taskboard}" \
  -e POSTGRES_USER="${POSTGRES_USER:-taskboard}" \
  -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-taskboard}" \
  "$CONTAINER_NAME" \
  python /app/migrations/migrate_sqlite_to_postgres.py --sqlite-path /app/tasks.db
