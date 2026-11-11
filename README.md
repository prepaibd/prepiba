# PrepIBA

IBA (MBA) admission-test preparation platform: past papers, mock exams, solutions (English and Bangla),
AI tutor and analytics. Django/DRF backend, Next.js web app, Postgres.

## Layout
- `backend/` Django project (`accounts`, `catalog`, `practice`, `review`, `analytics`, `ai`, `chat`, `writing`)
- `web/` Next.js 16 app (Tailwind v4, KaTeX)
- `data/` curated exam data (the source of truth for the import)
- `tools/` data validation and audit scripts
- `docs/` design and data notes

## Backend quickstart
```
docker compose -f docker-compose.dev.yml -p prepiba up -d db
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements/dev.txt
cp .env.example .env            # set SECRET_KEY
.venv/bin/python manage.py migrate
.venv/bin/python manage.py import_prepiba
.venv/bin/python -m pytest
```
Validate the data files: `(cd tools/katex_check && npm install) && python3 tools/validate.py`.

## Run it in Docker (production-shaped)
```
cp .env.example .env          # set POSTGRES_PASSWORD, SECRET_KEY, GEMINI_API_KEY, GOOGLE_CLIENT_ID
docker compose up -d --build   # nginx on http://localhost:8088
docker compose exec api python manage.py import_prepiba
```
This stack uses its own compose project (`prepiba-prod`), so it never touches the dev database from
`docker-compose.dev.yml`. See `docs/RUNBOOK.md` for deployment, backups and troubleshooting.

## Run the whole app locally (development)
```
# terminal 1: API (use any free port; 8000 may be taken by other projects)
cd backend && .venv/bin/python manage.py runserver 8010
# terminal 2: web
cd web && cp .env.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8010/api/v1, NEXT_PUBLIC_DEV_LOGIN=1
npm install && npm run dev -- -p 3010
```
`NEXT_PUBLIC_*` values are baked in at build time, so rebuild the web app after changing them.
Dev login (email only) exists only when the API runs with `config.settings.dev`; it returns 404 in production.
Real sign-in needs `GOOGLE_CLIENT_ID` (API) and `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (web).

## API (all under `/api/v1/`)
`auth/google|dev-login|refresh|me`, `exams`, `questions` (+ `questions/{id}/solution`), `subjects`, `topics`,
`formulas`, `rules`, `attempts` (+ `answers`, `submit`, `result`), `bookmarks`, `chat/sessions` (+ streaming `messages`),
`writing/prompts|submissions`, `ai/usage`, `analytics/overview|topic-frequency`, `review/questions` (reviewers only; also `/answer/`). Docs at `/api/docs/`. See `docs/AI.md`.
Question payloads never include answers; they are revealed only by `solution` or an attempt's `result`.
Attempts auto-submit when their deadline passes (checked on every access; `manage.py submit_expired_attempts`
sweeps abandoned ones and should run every minute in production).
