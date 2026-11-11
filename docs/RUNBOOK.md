# Runbook

## Architecture
`nginx :80` -> `web` (Next.js) for pages, `api` (gunicorn/Django) for `/api`, `/admin`, `/health/`, `/static/`;
`/media/` (question figures) is served by nginx from a shared volume. `api` talks to `db` (Postgres 17) and `redis`
(cache only: rate limits and AI allowances, shared by all workers). `sweeper` auto-submits exams whose time ran out.
TLS is **not** terminated here: put a load balancer or certbot/Caddy in front and forward `X-Forwarded-Proto`.

## First deployment
1. `cp .env.example .env` and set: `POSTGRES_PASSWORD`, `SECRET_KEY` (long random), `ALLOWED_HOSTS` (your domain),
   `CSRF_TRUSTED_ORIGINS` (`https://your.domain`), `SECURE_SSL_REDIRECT=true`, `GOOGLE_CLIENT_ID`, `GEMINI_API_KEY`.
2. Google sign-in: in the Google Cloud console add `https://your.domain` to the OAuth client's *Authorized JavaScript
   origins*. Use a **separate Gemini key for this product** so its quota and billing are isolated.
3. `docker compose up -d --build` (the `api` container runs migrations on start).
4. `docker compose exec api python manage.py import_prepiba` (loads exams, solutions, Bangla, figures; safe to repeat).
5. `docker compose exec api python manage.py createsuperuser` (email + password, for `/admin/`).
6. Give a trusted person reviewer access: `/admin/` -> Users -> role `reviewer`.
7. Check: `curl https://your.domain/health/` returns `{"status": "ok"}`.

`HTTP_PORT` (default 8088) is the host port nginx listens on; map it to 80/443 behind your TLS front end.

## Updating
`git pull && docker compose up -d --build`. Migrations run automatically. New exam data: add files under `data/`,
rebuild, run `import_prepiba` (reviewer-verified answers and reviewed Bangla are never overwritten).

## Backups
`./deploy/backup.sh /path/to/backups` writes a compressed `pg_dump`. Schedule it (e.g. cron `0 2 * * *`) and copy the
files off the server. Restore with `./deploy/restore.sh <file>` (asks for confirmation; replaces all data).
Test a restore on a copy before you need one. Figures are rebuilt from `data/` by `import_prepiba`; nothing else
is stored on disk.

## Monitoring
- Uptime: poll `/health/` (checks the database; 503 when it is down).
- Logs: `docker compose logs -f api web nginx`. Set `SENTRY_DSN` for error reports.
- AI spend and abuse: Django admin -> AI usage logs; limits are `AI_*_PER_DAY` in `.env`.

## Troubleshooting
| Symptom | Likely cause |
|---|---|
| `api` restarts, "password authentication failed" | The Postgres volume was created with a different `POSTGRES_PASSWORD`. The password is only read on first creation; reset the volume or change the DB user's password. |
| `/health/` returns 400 | The request's `Host` is not in `ALLOWED_HOSTS`. |
| Admin login: "CSRF verification failed" | Add the site origin (with scheme) to `CSRF_TRUSTED_ORIGINS`. |
| Everyone shares one rate limit | The proxy chain differs from `NUM_PROXIES` (default 1 = just nginx). Set it to the number of proxies in front of the API. |
| Tutor replies arrive all at once | A proxy in front of nginx is buffering. Disable buffering for `/api/v1/chat/` (nginx here already does). |
| 503 from tutor/writing | `AI_PROVIDER`/`GEMINI_API_KEY` not set, or the model is unreachable. |

## Known limits
- Single host, no Celery: writing feedback is generated inside the web request (a few seconds).
- No Google sign-in on `localhost` unless that origin is registered; to try the stack locally, mint a JWT with
  `manage.py shell` (production has no dev login by design).
- HSTS preload is intentionally off (it is effectively permanent): enable `SECURE_HSTS_PRELOAD` once the domain is final.
