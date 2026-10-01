"""Berita eksternal: daftar publik, moderasi admin, sumber RSS."""

from flask import Blueprint, request

from models import category_model, news_model, region_model
from services import news_collector, notification_engine, region_engine
from utils import validators as v
from utils.api import APIError, Conflict, NotFound, success
from utils.security import admin_required, client_ip, current_admin, \
    is_admin_scope, log

news_bp = Blueprint("news", __name__, url_prefix="/api/news")

SORTS = ("newest", "oldest", "title")
SOURCE_STATUSES = ("ACTIVE", "INACTIVE")


def list_filters(args, admin_scope):
    filters = {
        "public": not admin_scope,
        "q": (args.get("q") or "").strip()[:100] or None,
        "category_id": v.integer(args.get("category_id"), "category_id",
                                 required=False),
        "sort": args.get("sort") if args.get("sort") in SORTS else "newest",
    }
    filters.update(v.date_range(args))
    region_id = v.integer(args.get("region_id"), "region_id", required=False)
    if region_id:
        filters["region_ids"] = (region_engine.descendant_ids(region_id)
                                 if admin_scope
                                 else region_engine.related_ids(region_id))
    if admin_scope:
        if args.get("status"):
            filters["status"] = v.choice(args.get("status"), "status",
                                         news_model.STATUSES)
        filters["source_id"] = v.integer(args.get("source_id"), "source_id",
                                         required=False)
    return filters


@news_bp.get("")
def list_news():
    admin_scope = is_admin_scope()
    page, per_page = v.pagination(request.args)
    return success(news_model.list_news(
        list_filters(request.args, admin_scope), page, per_page
    ))


@news_bp.get("/<int:news_id>")
def get_news(news_id):
    admin_scope = is_admin_scope()
    news = news_model.get_news(news_id, public=not admin_scope)
    if not news:
        raise NotFound("Berita tidak ditemukan.")
    news["hierarchy"] = (region_engine.hierarchy(news["region_id"])
                         if news["region_id"] else [])
    return success(news)


@news_bp.post("/collect")
@admin_required
def collect():
    try:
        summary = news_collector.collect_all(current_admin()["id"],
                                             client_ip())
    except news_collector.CollectorBusy as exc:
        raise APIError(str(exc), 409, "collector_busy") from exc
    message = f"{summary['inserted']} berita baru ditemukan."
    if summary["errors"]:
        message += f" {len(summary['errors'])} sumber gagal diambil."
    return success(summary, message)


@news_bp.put("/<int:news_id>")
@admin_required
def update_news(news_id):
    news = news_model.get_news(news_id)
    if not news:
        raise NotFound("Berita tidak ditemukan.")
    data = v.json_body()
    region_id = v.integer(data.get("region_id"), "Wilayah", required=False)
    if region_id and not region_model.get_region(region_id):
        raise APIError("Wilayah tidak ditemukan.")
    category_id = v.integer(data.get("category_id"), "Kategori",
                            required=False)
    if category_id and not category_model.get_category(category_id):
        raise APIError("Kategori tidak ditemukan.")
    cleaned = {
        "title": v.string(data, "title", "Judul", max_length=500)
        if "title" in data else news["title"],
        "summary": v.string(data, "summary", "Ringkasan", required=False,
                            max_length=2000)
        if "summary" in data else news["summary"],
        "region_id": region_id if "region_id" in data else news["region_id"],
        "category_id": category_id if "category_id" in data
        else news["category_id"],
        "status": v.choice(data.get("status"), "Status", news_model.STATUSES,
                           default=news["status"]),
    }
    news_model.update_news(news_id, cleaned, current_admin()["id"])
    log("MODERATE", f"Berita #{news_id} -> {cleaned['status']}", "news",
        news_id)
    updated = news_model.get_news(news_id)
    if updated["status"] == "APPROVED":
        notification_engine.notify_news(updated)
    return success(updated, "Berita berhasil diperbarui.")


@news_bp.delete("/<int:news_id>")
@admin_required
def delete_news(news_id):
    news = news_model.get_news(news_id)
    if not news:
        raise NotFound("Berita tidak ditemukan.")
    news_model.delete_news(news_id)
    log("DELETE", f"Menghapus berita: {news['title'][:200]}", "news", news_id)
    return success(None, "Berita berhasil dihapus.")


# ------------------------------------------------------------- sources

def _validate_source(data, source_id=None):
    rss_url = v.url(data, "rss_url", "URL RSS", required=True)
    if news_model.rss_url_taken(rss_url, source_id):
        raise Conflict("URL RSS sudah terdaftar.")
    region_id = v.integer(data.get("region_id"), "Wilayah", required=False)
    if region_id and not region_model.get_region(region_id):
        raise APIError("Wilayah tidak ditemukan.")
    category_id = v.integer(data.get("category_id"), "Kategori",
                            required=False)
    if category_id and not category_model.get_category(category_id):
        raise APIError("Kategori tidak ditemukan.")
    return {
        "name": v.string(data, "name", "Nama sumber", max_length=150),
        "website_url": v.url(data, "website_url", "Website", required=True,
                             max_length=500),
        "rss_url": rss_url,
        "region_id": region_id,
        "category_id": category_id,
        "status": v.choice(data.get("status"), "Status", SOURCE_STATUSES,
                           default="ACTIVE"),
    }


@news_bp.get("/sources")
@admin_required
def list_sources():
    return success(news_model.list_sources())


@news_bp.post("/sources")
@admin_required
def create_source():
    data = _validate_source(v.json_body())
    source_id = news_model.create_source(data)
    log("CREATE", f"Menambah sumber berita: {data['name']}", "news_source",
        source_id)
    return success(news_model.get_source(source_id),
                   "Sumber berita ditambahkan.", 201)


@news_bp.put("/sources/<int:source_id>")
@admin_required
def update_source(source_id):
    if not news_model.get_source(source_id):
        raise NotFound("Sumber berita tidak ditemukan.")
    data = _validate_source(v.json_body(), source_id)
    news_model.update_source(source_id, data)
    log("UPDATE", f"Memperbarui sumber berita: {data['name']}",
        "news_source", source_id)
    return success(news_model.get_source(source_id),
                   "Sumber berita diperbarui.")


@news_bp.delete("/sources/<int:source_id>")
@admin_required
def delete_source(source_id):
    source = news_model.get_source(source_id)
    if not source:
        raise NotFound("Sumber berita tidak ditemukan.")
    news_model.delete_source(source_id)
    log("DELETE", f"Menghapus sumber berita: {source['name']}",
        "news_source", source_id)
    return success(None, "Sumber berita dihapus.")
