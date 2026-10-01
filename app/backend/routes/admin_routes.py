"""Endpoint pendukung admin: dashboard, activity log, kategori, settings."""

from flask import Blueprint, request

from config import Config
from models import admin_model, category_model, event_model, \
    information_model, news_model, push_subscription_model, region_model
from utils import validators as v
from utils.api import Conflict, NotFound, success
from utils.security import admin_required, is_admin_scope, log

admin_bp = Blueprint("admin", __name__, url_prefix="/api")

STATUSES = ("ACTIVE", "INACTIVE")


@admin_bp.get("/admin/dashboard")
@admin_required
def dashboard():
    return success({
        "totals": {
            "information": information_model.count_information(),
            "events": event_model.count_events(),
            "news": news_model.count_news(),
            "news_pending": news_model.count_news("PENDING"),
            "regions": region_model.count_regions(),
            "push_subscriptions": push_subscription_model.count_active(),
        },
        "recent_activity": admin_model.recent_activity(10),
    })


@admin_bp.get("/admin/activity")
@admin_required
def activity():
    limit = min(v.integer(request.args.get("limit") or 50, "limit"), 200)
    return success(admin_model.recent_activity(limit))


@admin_bp.get("/admin/settings")
@admin_required
def settings():
    """Status konfigurasi (tanpa membuka nilai rahasia)."""
    return success({
        "push_enabled": Config.push_enabled(),
        "mail_enabled": Config.mail_enabled(),
        "news_collector_enabled": Config.NEWS_COLLECTOR_ENABLED,
        "news_collect_interval_minutes": Config.NEWS_COLLECT_INTERVAL_MINUTES,
        "session_lifetime_minutes": Config.PERMANENT_SESSION_LIFETIME // 60,
        "environment": Config.FLASK_ENV,
        "sources": news_model.list_sources(),
    })


# ------------------------------------------------------------ categories

def _validate_category(data, category_id=None):
    name = v.string(data, "name", "Nama kategori", max_length=100)
    if category_model.name_taken(name, category_id):
        raise Conflict("Nama kategori sudah digunakan.")
    return {
        "name": name,
        "description": v.string(data, "description", "Deskripsi",
                                required=False, max_length=1000),
        "icon": v.string(data, "icon", "Ikon", required=False,
                         max_length=100),
        "status": v.choice(data.get("status"), "Status", STATUSES,
                           default="ACTIVE"),
    }


@admin_bp.get("/categories")
def list_categories():
    return success(category_model.list_categories(
        active_only=not is_admin_scope()
    ))


@admin_bp.post("/categories")
@admin_required
def create_category():
    data = _validate_category(v.json_body())
    category_id = category_model.create_category(data)
    log("CREATE", f"Membuat kategori: {data['name']}", "category",
        category_id)
    return success(category_model.get_category(category_id),
                   "Kategori dibuat.", 201)


@admin_bp.put("/categories/<int:category_id>")
@admin_required
def update_category(category_id):
    if not category_model.get_category(category_id):
        raise NotFound("Kategori tidak ditemukan.")
    data = _validate_category(v.json_body(), category_id)
    category_model.update_category(category_id, data)
    log("UPDATE", f"Memperbarui kategori: {data['name']}", "category",
        category_id)
    return success(category_model.get_category(category_id),
                   "Kategori diperbarui.")


@admin_bp.delete("/categories/<int:category_id>")
@admin_required
def delete_category(category_id):
    category = category_model.get_category(category_id)
    if not category:
        raise NotFound("Kategori tidak ditemukan.")
    category_model.delete_category(category_id)
    log("DELETE", f"Menghapus kategori: {category['name']}", "category",
        category_id)
    return success(None, "Kategori dihapus.")
