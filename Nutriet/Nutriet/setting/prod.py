"""
Configuración de PRODUCCIÓN para NutriET.
Importa todo desde settings.py principal y sobreescribe lo necesario.

✅ CORRECCIONES DE SEGURIDAD aplicadas:
  - Headers de seguridad HTTP forzados vía middleware
  - X-Frame-Options: DENY
  - Strict-Transport-Security (HSTS)
  - X-Content-Type-Options: nosniff
  - Referrer-Policy
  - Permissions-Policy
"""

import os
import pathlib
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

from Nutriet.settings import *  # noqa

# ── Seguridad básica ──────────────────────────────────────────────────────────
DEBUG      = False
SECRET_KEY = os.getenv("SECRET_KEY")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ── HTTPS y proxy Render ──────────────────────────────────────────────────────
SECURE_PROXY_SSL_HEADER    = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT        = os.getenv("SECURE_SSL_REDIRECT", "True") == "True"
SESSION_COOKIE_SECURE      = True
CSRF_COOKIE_SECURE         = True
SECURE_HSTS_SECONDS        = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD        = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS            = "DENY"

# ── Middleware — agregar SecurityHeadersMiddleware ────────────────────────────
# ✅ FIX: Los headers X-Frame-Options y HSTS que Django genera a veces no llegan
# al navegador porque Render o WhiteNoise los descarta. Este middleware los
# fuerza en CADA respuesta directamente desde Python, sin depender de Django.
#
# Si MIDDLEWARE ya fue definido en settings.py (importado arriba con *),
# lo tomamos y agregamos el nuestro al principio.

_mw = list(MIDDLEWARE)  # copia mutable del MIDDLEWARE importado

SECURITY_HEADERS_MIDDLEWARE = "Nutriet.middleware.SecurityHeadersMiddleware"
if SECURITY_HEADERS_MIDDLEWARE not in _mw:
    _mw.insert(0, SECURITY_HEADERS_MIDDLEWARE)

# WhiteNoise siempre después de SecurityHeaders
WN = "whitenoise.middleware.WhiteNoiseMiddleware"
if WN not in _mw:
    _mw.insert(1, WN)

MIDDLEWARE = _mw

# ── Base de datos (PostgreSQL) ────────────────────────────────────────────────
import dj_database_url

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }

# ── Static files con WhiteNoise ───────────────────────────────────────────────
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ── Caché con Redis ───────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,
            },
        }
    }
    SESSION_ENGINE      = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
    CELERY_BROKER_URL   = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

# ── Logging ───────────────────────────────────────────────────────────────────
log_dir = BASE_DIR / "logs"
pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {message}", "style": "{"},
        "simple":  {"format": "{levelname} {asctime} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "nutriet.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "errors.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "level": "ERROR",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django":       {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "applications": {"handlers": ["console", "file", "error_file"], "level": "INFO", "propagate": False},
        "apscheduler":  {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "https://tudominio.com/api/auth/google/callback/")
CORS_ALLOWED_ORIGINS = [o for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o]
CORS_ALLOW_CREDENTIALS = True