# Build context is the repository root so the curated data/ directory can be baked in.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DJANGO_SETTINGS_MODULE=config.settings.prod

RUN useradd --create-home --uid 10001 app
WORKDIR /app

COPY backend/requirements/ requirements/
RUN pip install -r requirements/prod.txt

COPY backend/ /app/
COPY data/ /app/data/
COPY deploy/entrypoint.sh /entrypoint.sh

# Static files are baked into the image (served by WhiteNoise). The build needs settings to import but never
# touches the database.
RUN SECRET_KEY=build-only DATABASE_URL=postgres://x:x@localhost/x python manage.py collectstatic --noinput \
 && mkdir -p /app/media && chown -R app:app /app/media /app/staticfiles && chmod +x /entrypoint.sh

ENV DATA_DIR=/app/data MEDIA_ROOT=/app/media
USER app
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--worker-class", "gthread", "--workers", "2", "--threads", "8", "--timeout", "120", "--access-logfile", "-"]
