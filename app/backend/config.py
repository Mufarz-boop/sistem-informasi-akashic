import os
from dotenv import load_dotenv

# =====================================================
# LOAD ENVIRONMENT VARIABLES
# =====================================================
load_dotenv()


# =====================================================
# HELPERS — WAJIB ADA DI .env
# =====================================================
def _require(key: str) -> str:
    """Ambil value dari environment. Raise jika tidak ada."""
    value = os.getenv(key)
    if value is None or value == "":
        raise RuntimeError(
            f"[Config] Environment variable '{key}' wajib diisi di file .env"
        )
    return value


def _require_bool(key: str) -> bool:
    """Ambil value boolean dari environment. Raise jika bukan true/false."""
    raw = _require(key).strip().lower()
    if raw in ("true", "1", "yes", "on"):
        return True
    if raw in ("false", "0", "no", "off"):
        return False
    raise RuntimeError(
        f"[Config] Environment variable '{key}' harus bernilai 'true' atau 'false', bukan '{raw}'"
    )


def _require_int(key: str) -> int:
    """Ambil value integer dari environment. Raise jika bukan angka."""
    raw = _require(key).strip()
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(
            f"[Config] Environment variable '{key}' harus berupa angka, bukan '{raw}'"
        )


# =====================================================
# CONFIG CLASS
# =====================================================
class Config:
    # ── Flask Core ────────────────────────────────────
    SECRET_KEY = _require("SECRET_KEY")

    FLASK_ENV = _require("FLASK_ENV")
    FLASK_DEBUG = _require_bool("FLASK_DEBUG")

    # ── Database (MySQL) ──────────────────────────────
    DB_HOST = _require("DB_HOST")
    DB_PORT = _require_int("DB_PORT")
    DB_NAME = _require("DB_NAME")
    DB_USER = _require("DB_USER")
    DB_PASSWORD = _require("DB_PASSWORD")

    # ── Contact Email (SMTP) ──────────────────────────
    MAIL_SERVER = _require("MAIL_SERVER")
    MAIL_PORT = _require_int("MAIL_PORT")
    MAIL_USE_SSL = _require_bool("MAIL_USE_SSL")
    MAIL_USERNAME = _require("MAIL_USERNAME")
    MAIL_PASSWORD = _require("MAIL_PASSWORD")
    MAIL_SENDER = _require("MAIL_SENDER")
    CONTACT_RECIPIENT = _require("CONTACT_RECIPIENT")