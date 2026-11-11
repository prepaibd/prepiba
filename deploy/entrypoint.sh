#!/bin/sh
# Runs migrations for the API container only (RUN_MIGRATIONS=1), then starts the given command.
set -e
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  python manage.py migrate --noinput
fi
if [ "${IMPORT_DATA_ON_START:-0}" = "1" ]; then
  python manage.py import_prepiba
fi
exec "$@"
