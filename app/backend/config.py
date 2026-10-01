"""Konfigurasi aplikasi Akashic.

Seluruh nilai sensitif (secret key, kredensial database, VAPID key)
dibaca dari environment variable / file .env, tidak pernah ditulis
langsung di source code.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
APP_DIR = BACKEND_DIR.parent
FRONTEND_DIR = APP_DIR / "frontend"

load_dotenv(APP_DIR / ".env")


def _bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _list(name, default=""):
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Config:
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = FLASK_ENV == "development"

    SECRET_KEY = os.getenv("SECRET_KEY")

    HOST = os.getenv("APP_HOST", "127.0.0.1")
    PORT = _int("APP_PORT", 5000)
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "")

    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = _int("DB_PORT", 3306)
    DB_NAME = os.getenv("DB_NAME", "db_akashic")
    DB_USER = os.getenv("DB_USER", "")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_POOL_SIZE = _int("DB_POOL_SIZE", 5)

    SESSION_COOKIE_NAME = "akashic_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = _int("SESSION_LIFETIME_MINUTES", 120) * 60

    CORS_ORIGINS = _list("CORS_ORIGINS")

    VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
    VAPID_CLAIMS_EMAIL = os.getenv("VAPID_CLAIMS_EMAIL", "")

    NEWS_COLLECTOR_ENABLED = _bool("NEWS_COLLECTOR_ENABLED", True)
    NEWS_COLLECT_INTERVAL_MINUTES = _int("NEWS_COLLECT_INTERVAL_MINUTES", 15)
    NEWS_REQUEST_TIMEOUT = _int("NEWS_REQUEST_TIMEOUT", 15)
    NEWS_MAX_ITEMS_PER_SOURCE = _int("NEWS_MAX_ITEMS_PER_SOURCE", 30)
    NEWS_USER_AGENT = os.getenv(
        "NEWS_USER_AGENT", "AkashicNewsCollector/1.0 (+RSS reader)"
    )

    LOCATION_MAX_ACCURACY_METERS = _int("LOCATION_MAX_ACCURACY_METERS", 50000)

    PASSWORD_RESET_TOKEN_MINUTES = _int("PASSWORD_RESET_TOKEN_MINUTES", 30)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = _int("MAIL_PORT", 587)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_USE_TLS = _bool("MAIL_USE_TLS", True)
    MAIL_SENDER = os.getenv("MAIL_SENDER", "")

    @classmethod
    def validate(cls):
        """Hentikan aplikasi lebih awal jika konfigurasi wajib kosong."""
        missing = [
            name for name in ("SECRET_KEY", "DB_USER", "DB_NAME")
            if not getattr(cls, name)
        ]
        if missing:
            raise RuntimeError(
                "Environment variable wajib belum diisi di app/.env: "
                + ", ".join(missing)
            )

    @classmethod
    def push_enabled(cls):
        return bool(
            cls.VAPID_PUBLIC_KEY
            and cls.VAPID_PRIVATE_KEY
            and cls.VAPID_CLAIMS_EMAIL
        )

    @classmethod
    def mail_enabled(cls):
        return bool(cls.MAIL_SERVER and cls.MAIL_SENDER)
