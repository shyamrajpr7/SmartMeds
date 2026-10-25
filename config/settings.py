"""
Django settings for SmartMeds.

All secrets and environment-specific values are read from environment
variables (or a local ``.env`` file via python-decouple). Never commit real
values.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

import dj_database_url
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

ON_VERCEL = bool(os.environ.get("VERCEL"))

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = config(
    "SECRET_KEY", default="django-insecure-dev-only-change-me-in-production"
)
DEBUG = config("DEBUG", default=not ON_VERCEL, cast=bool)

_default_hosts = "localhost,127.0.0.1"
if ON_VERCEL:
    _default_hosts += ",.vercel.app,.vercel.sh"
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default=_default_hosts, cast=Csv())

_default_csrf_origins = ""
if ON_VERCEL:
    _default_csrf_origins = "https://*.vercel.app,https://*.vercel.sh"
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS", default=_default_csrf_origins, cast=Csv()
)
USE_X_FORWARDED_HOST = True

INSTALLED_APPS = [
    "config.apps.MongoAdminConfig",
    "config.apps.MongoAuthConfig",
    "config.apps.MongoContentTypesConfig",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_mongodb_backend",
    # Local apps
    "accounts",
    "prescriptions",
    "assistant",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database — MongoDB Atlas when a Mongo URI is configured, otherwise use
# DATABASE_URL (PostgreSQL/SQLite). SQLite is the local development default.
# ---------------------------------------------------------------------------
DATABASE_URL = config("DATABASE_URL", default="")
MONGODB_URI = config("MONGODB_URI", default="")
DJANGO_MONGODB_DB = config("DJANGO_MONGODB_DB", default="smartmeds_web")

_mongo_uri = DATABASE_URL or MONGODB_URI
if _mongo_uri.startswith(("mongodb://", "mongodb+srv://")):
    DATABASES = {
        "default": {
            "ENGINE": "django_mongodb_backend",
            "NAME": DJANGO_MONGODB_DB,
            "HOST": _mongo_uri,
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.parse(
            _mongo_uri or f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
            conn_max_age=600,
            conn_health_checks=True,
        )
    }

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = config("TIME_ZONE", default="Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = Path("/tmp/media") if ON_VERCEL else BASE_DIR / "media"

STORAGES = {
    # Keep uploads in the database so they survive serverless redeploys and
    # remain available on hosts with an ephemeral filesystem.
    "default": {"BACKEND": "prescriptions.storage.DatabaseStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

WHITENOISE_USE_FINDERS = ON_VERCEL

# Optional Cloudinary storage for uploaded prescriptions.
CLOUDINARY_URL = config("CLOUDINARY_URL", default="")
if CLOUDINARY_URL:
    _cloudinary = urlparse(CLOUDINARY_URL)
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": _cloudinary.hostname or "",
        "API_KEY": _cloudinary.username or "",
        "API_SECRET": _cloudinary.password or "",
    }
    INSTALLED_APPS += ["cloudinary_storage", "cloudinary"]
    STORAGES["default"] = {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    }

# ---------------------------------------------------------------------------
# Email (reminders, password reset)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL", default="SmartMeds <noreply@smartmeds.local>"
)

# ---------------------------------------------------------------------------
# Third-party integrations (used by later apps)
# ---------------------------------------------------------------------------
CRON_SECRET = config("CRON_SECRET", default="")

LLM_API_KEY = config(
    "LLM_API_KEY",
    default=config(
        "GROQ_API_KEY",
        default=config("XAI_API_KEY", default=config("OPENAI_API_KEY", default="")),
    ),
)
LLM_MODEL = config("LLM_MODEL", default="openai/gpt-oss-120b")
LLM_BASE_URL = config("LLM_BASE_URL", default="https://api.groq.com/openai/v1")

# WhatsApp / Notifications
TWILIO_ACCOUNT_SID = config("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = config("TWILIO_AUTH_TOKEN", default="")
TWILIO_WHATSAPP_FROM = config("TWILIO_WHATSAPP_FROM", default="whatsapp:+14155238886")
WHATSAPP_WEBHOOK_URL = config("WHATSAPP_WEBHOOK_URL", default="")
WHATSAPP_WEBHOOK_TOKEN = config("WHATSAPP_WEBHOOK_TOKEN", default="")

# Optional web search provider (Tavily). When unset, the assistant falls back
# to public DuckDuckGo and Google News feeds.
WEB_SEARCH_API_KEY = config(
    "WEB_SEARCH_API_KEY", default=config("TAVILY_API_KEY", default="")
)
WEB_SEARCH_BASE_URL = config(
    "WEB_SEARCH_BASE_URL", default="https://api.tavily.com"
)
TAVILY_API_KEY = WEB_SEARCH_API_KEY

WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": config("VAPID_PUBLIC_KEY", default=""),
    "VAPID_PRIVATE_KEY": config("VAPID_PRIVATE_KEY", default=""),
    "VAPID_ADMIN_EMAIL": config("VAPID_ADMIN_EMAIL", default="admin@example.com"),
}

SITE_URL = config("SITE_URL", default="http://localhost:8000")

# ---------------------------------------------------------------------------
# Security (enabled outside DEBUG, e.g. on Render)
# ---------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

if not DEBUG:
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"

MIGRATION_MODULES = {
    "admin": "mongo_migrations.admin",
    "auth": "mongo_migrations.auth",
    "contenttypes": "mongo_migrations.contenttypes",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
