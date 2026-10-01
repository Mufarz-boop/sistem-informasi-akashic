"""Entry point aplikasi Akashic.

Menjalankan:  python app.py   (dari folder app/backend)
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import mysql.connector
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from config import FRONTEND_DIR, Config
from database import DatabaseUnavailable, ping
from routes import register_blueprints
from services import news_collector
from utils.api import AkashicJSONProvider, APIError, error, success

logger = logging.getLogger("akashic")
scheduler = None


def _wants_json():
    return request.path.startswith("/api/")


def _error_page(status, title, message):
    template = "error/500.html" if status >= 500 else "error/400.html"
    return render_template(template, status=status, title=title,
                           message=message), status


def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(exc):
        return error(exc.message, exc.status, exc.error)

    @app.errorhandler(DatabaseUnavailable)
    def handle_db_unavailable(exc):
        logger.error("Database tidak tersedia: %s", exc)
        message = "Database tidak dapat dihubungi. Coba lagi nanti."
        if _wants_json():
            return error(message, 503, "database_unavailable")
        return _error_page(503, "Layanan belum tersedia", message)

    @app.errorhandler(mysql.connector.IntegrityError)
    def handle_integrity_error(exc):
        logger.warning("Integrity error: %s", exc)
        return error("Data masih digunakan oleh data lain atau duplikat.",
                     409, "conflict")

    @app.errorhandler(HTTPException)
    def handle_http_error(exc):
        if _wants_json():
            return error(exc.description, exc.code,
                         exc.name.lower().replace(" ", "_"))
        if exc.code == 404:
            return _error_page(404, "Halaman tidak ditemukan",
                               "Alamat yang Anda buka tidak tersedia.")
        return _error_page(exc.code, exc.name, exc.description)

    @app.errorhandler(Exception)
    def handle_unexpected(exc):
        logger.exception("Kesalahan tidak terduga: %s", exc)
        message = "Terjadi kesalahan pada server."
        if _wants_json():
            return error(message, 500, "internal_server_error")
        return _error_page(500, "Kesalahan server", message)


def register_security_headers(app):
    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy",
                                    "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy",
                                    "geolocation=(self), camera=(), "
                                    "microphone=()")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response


def start_scheduler(app):
    """News collector berkala. Hanya satu scheduler per proses server."""
    global scheduler
    if not Config.NEWS_COLLECTOR_ENABLED or scheduler is not None:
        return
    # Saat debug reloader aktif, hanya proses anak yang menjalankan job.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    scheduler = BackgroundScheduler(daemon=True, timezone="UTC")
    scheduler.add_job(
        news_collector.scheduled_job, "interval",
        minutes=Config.NEWS_COLLECT_INTERVAL_MINUTES,
        id="news_collector", max_instances=1, coalesce=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=30),
    )
    scheduler.start()
    logger.info("News collector terjadwal setiap %s menit.",
                Config.NEWS_COLLECT_INTERVAL_MINUTES)


def create_app(start_jobs=True):
    Config.validate()
    app = Flask(
        __name__,
        template_folder=str(FRONTEND_DIR / "pages"),
        static_folder=str(FRONTEND_DIR / "assets"),
        static_url_path="/static",
    )
    app.json = AkashicJSONProvider(app)
    app.config.from_object(Config)
    app.config["JSON_SORT_KEYS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

    if Config.CORS_ORIGINS:
        CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}},
             supports_credentials=True)

    register_blueprints(app)
    register_error_handlers(app)
    register_security_headers(app)

    @app.get("/api/health")
    def health():
        db_ok = ping()
        return success({"database": db_ok,
                        "push_enabled": Config.push_enabled()},
                       "OK" if db_ok else "Database tidak terhubung",
                       200 if db_ok else 503)

    @app.context_processor
    def inject_globals():
        return {"app_name": "Akashic",
                "contact_email": Config.CONTACT_EMAIL}

    if start_jobs:
        start_scheduler(app)
    return app


def main():
    logging.basicConfig(
        level=logging.DEBUG if Config.DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    app = create_app()
    if not ping():
        logger.warning("MySQL belum terhubung. Periksa konfigurasi DB_* "
                       "di app/.env lalu import database/db_akashic.sql.")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)


if __name__ == "__main__":
    main()
