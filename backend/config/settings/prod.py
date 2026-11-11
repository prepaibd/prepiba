import logging

from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, REST_FRAMEWORK, env

DEBUG = False
DEV_LOGIN_ENABLED = False  # never in production

# --- HTTPS / proxy ------------------------------------------------------------------------------------------
# TLS is terminated by the reverse proxy. SECURE_SSL_REDIRECT can be turned off only for a plain-http check
# (e.g. `docker compose up` on localhost); production leaves it on.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_REDIRECT_EXEMPT = [r"^health/$"]  # container health checks talk plain http
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000 if SECURE_SSL_REDIRECT else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_CONTENT_TYPE_NOSNIFF = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# One proxy (nginx) sits in front: rate limits must key on the real client address, not on nginx's.
REST_FRAMEWORK = {**REST_FRAMEWORK, "NUM_PROXIES": env.int("NUM_PROXIES", default=1)}

# --- static files, cache ----------------------------------------------------------------------------------
MIDDLEWARE = [MIDDLEWARE[0], "whitenoise.middleware.WhiteNoiseMiddleware", *MIDDLEWARE[1:]]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
# Throttles and quotas must be shared by every worker, so the cache lives in Redis when configured.
if env("REDIS_URL", default=""):
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": env("REDIS_URL")}}

# --- logging, error reporting ----------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
if env("SENTRY_DSN", default=""):
    import sentry_sdk

    sentry_sdk.init(dsn=env("SENTRY_DSN"), traces_sample_rate=0.0, send_default_pii=False)
else:
    logging.getLogger(__name__).info("SENTRY_DSN not set: error reporting disabled")
