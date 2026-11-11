#!/bin/sh
# Restore a dump made by backup.sh into the running database. DESTRUCTIVE: replaces current data.
#   ./deploy/restore.sh backups/prepiba-YYYYMMDD-HHMMSS.sql.gz
set -eu
[ $# -eq 1 ] && [ -f "$1" ] || { echo "usage: $0 <dump.sql.gz>" >&2; exit 2; }
printf "This REPLACES the database with %s. Type 'restore' to continue: " "$1"
read -r answer
[ "$answer" = "restore" ] || { echo "aborted"; exit 1; }
gunzip -c "$1" | docker compose exec -T db psql -U prepiba -d prepiba -v ON_ERROR_STOP=1 -q
echo "restored $1"
