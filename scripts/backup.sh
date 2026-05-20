#!/usr/bin/env bash
# Nightly Postgres backup. Keep last 30 days.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP=$(date +%Y%m%d-%H%M%S)
DEST="${REPO_ROOT}/backups/finance-${STAMP}.sql.gz"

mkdir -p "${REPO_ROOT}/backups"

docker compose -f "${REPO_ROOT}/compose/docker-compose.yml" \
    exec -T postgres \
    pg_dump -U finance finance \
    | gzip > "$DEST"

# Keep last 30 backups
ls -1t "${REPO_ROOT}/backups/"finance-*.sql.gz | tail -n +31 | xargs -r rm

# Optional: rclone to offsite
# rclone copy "$DEST" remote:finance-pi-backups/

echo "[$(date)] Backed up to $DEST"
