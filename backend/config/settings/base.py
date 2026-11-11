from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BASE_DIR.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "apps.accounts",
    "apps.catalog",
    "apps.practice",
    "apps.review",
    "apps.analytics",
    "apps.ai",
    "apps.chat",
    "apps.writing",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASES = {"default": env.db("DATABASE_URL")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))

REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "600/min", "anon": "60/min", "login": "20/min", "chat": "30/min", "writing": "10/min",
    },
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "config.pagination.Pagination",
    "PAGE_SIZE": 50,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

SPECTACULAR_SETTINGS = {"TITLE": "PrepIBA API", "VERSION": "1.0.0", "SERVE_INCLUDE_SCHEMA": False}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")

# Where `import_prepiba` reads the curated exam data from.
DATA_DIR = Path(env("DATA_DIR", default=str(REPO_ROOT / "data")))

# Exam rules. IBA's real duration / negative marking are not in the source data (unconfirmed):
# these are fallbacks used only when an Exam row has no value of its own.
DEFAULT_NEGATIVE_MARK = env.float("DEFAULT_NEGATIVE_MARK", default=0.25)
DEFAULT_DURATION_MINUTES = env.int("DEFAULT_DURATION_MINUTES", default=90)
SECONDS_PER_QUESTION = env.int("SECONDS_PER_QUESTION", default=60)  # timed practice
DEV_LOGIN_ENABLED = False  # email-only login for local development; never enabled in prod

# --- AI -------------------------------------------------------------------------------------------------
# "mock" returns canned text (dev/tests). "gemini" needs GEMINI_API_KEY; without it AI endpoints answer 503
# rather than silently pretending to work.
AI_PROVIDER = env("AI_PROVIDER", default="mock")
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-3.5-flash-lite")
# Upper bound for one model call. Writing feedback may retry once on unusable JSON, so keep 2x this under the
# gunicorn timeout (120 s).
AI_TIMEOUT_SECONDS = env.int("AI_TIMEOUT_SECONDS", default=45)
# Per-user daily allowance by plan. Days roll over at local midnight (TIME_ZONE).
AI_DAILY_LIMITS = {
    "free": {
        "chat": env.int("AI_FREE_CHAT_PER_DAY", default=20),
        "writing": env.int("AI_FREE_WRITING_PER_DAY", default=2),
    },
    "paid": {
        "chat": env.int("AI_PAID_CHAT_PER_DAY", default=200),
        "writing": env.int("AI_PAID_WRITING_PER_DAY", default=20),
    },
}
CHAT_MAX_MESSAGE_CHARS = 2000
CHAT_HISTORY_MESSAGES = 10
WRITING_MIN_WORDS = 30
WRITING_MAX_WORDS = 1200
