#!/bin/sh
# Dump the production database to a timestamped, compressed file.
#   ./deploy/backup.sh [output-dir]        (run on the host that runs docker compose)
# Keep copies off the server. Restore with deploy/restore.sh.
set -eu
OUT="${1:-./backups}"
mkdir -p "$OUT"
FILE="$OUT/prepiba-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T db pg_dump -U prepiba -d prepiba --no-owner --clean --if-exists | gzip > "$FILE"
# a dump that is nearly empty means pg_dump failed half way
[ "$(wc -c < "$FILE")" -gt 1000 ] || { echo "backup looks empty: $FILE" >&2; rm -f "$FILE"; exit 1; }
echo "wrote $FILE ($(du -h "$FILE" | cut -f1))"
