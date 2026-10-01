"""CRUD Information (konten internal)."""

from flask import Blueprint, request

from models import category_model, information_model, region_model
from services import notification_engine, region_engine
from utils import validators as v
from utils.api import APIError, NotFound, success
from utils.security import admin_required, current_admin, is_admin_scope, log

information_bp = Blueprint("information", __name__,
                           url_prefix="/api/information")

STATUSES = ("DRAFT", "PUBLISHED", "EXPIRED", "ARCHIVED")
PRIORITIES = ("LOW", "NORMAL", "HIGH", "CRITICAL")
SORTS = ("newest", "oldest", "title")


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
    if admin_scope and args.get("status"):
        filters["status"] = v.choice(args.get("status"), "status", STATUSES)
    return filters


def _validate(data):
    category_id = v.integer(data.get("category_id"), "Kategori")
    if not category_model.get_category(category_id):
        raise APIError("Kategori tidak ditemukan.")
    region_id = v.integer(data.get("region_id"), "Wilayah")
    if not region_model.get_region(region_id):
        raise APIError("Wilayah tidak ditemukan.")
    published_at = v.datetime_value(data.get("published_at"),
                                    "Tanggal publikasi")
    expired_at = v.datetime_value(data.get("expired_at"),
                                  "Tanggal kedaluwarsa")
    if published_at and expired_at and expired_at <= published_at:
        raise APIError("Tanggal kedaluwarsa harus setelah tanggal publikasi.")
    return {
        "category_id": category_id,
        "region_id": region_id,
        "title": v.string(data, "title", "Judul", min_length=3),
        "summary": v.string(data, "summary", "Ringkasan", required=False,
                            max_length=1000),
        "content": v.string(data, "content", "Isi informasi",
                            max_length=100_000),
        "image": v.url(data, "image", "URL gambar", max_length=500),
        "priority": v.choice(data.get("priority"), "Prioritas", PRIORITIES,
                             default="NORMAL"),
        "status": v.choice(data.get("status"), "Status", STATUSES,
                           default="DRAFT"),
        "published_at": published_at,
        "expired_at": expired_at,
    }


def _notify_if_published(info):
    if info and info["status"] == "PUBLISHED":
        notification_engine.notify_information(info)


@information_bp.get("")
def list_information():
    admin_scope = is_admin_scope()
    page, per_page = v.pagination(request.args)
    result = information_model.list_information(
        list_filters(request.args, admin_scope), page, per_page
    )
    return success(result)


@information_bp.get("/<int:information_id>")
def get_information(information_id):
    admin_scope = is_admin_scope()
    info = information_model.get_information(information_id,
                                             public=not admin_scope)
    if not info:
        raise NotFound("Informasi tidak ditemukan.")
    info["hierarchy"] = region_engine.hierarchy(info["region_id"])
    return success(info)


@information_bp.post("")
@admin_required
def create_information():
    data = _validate(v.json_body())
    new_id = information_model.create_information(data, current_admin()["id"])
    log("CREATE", f"Membuat informasi: {data['title']}", "information",
        new_id)
    info = information_model.get_information(new_id)
    _notify_if_published(info)
    return success(info, "Informasi berhasil dibuat.", 201)


@information_bp.put("/<int:information_id>")
@admin_required
def update_information(information_id):
    if not information_model.get_information(information_id):
        raise NotFound("Informasi tidak ditemukan.")
    data = _validate(v.json_body())
    information_model.update_information(information_id, data)
    log("UPDATE", f"Memperbarui informasi: {data['title']}", "information",
        information_id)
    info = information_model.get_information(information_id)
    _notify_if_published(info)
    return success(info, "Informasi berhasil diperbarui.")


@information_bp.delete("/<int:information_id>")
@admin_required
def delete_information(information_id):
    info = information_model.get_information(information_id)
    if not info:
        raise NotFound("Informasi tidak ditemukan.")
    information_model.delete_information(information_id)
    log("DELETE", f"Menghapus informasi: {info['title']}", "information",
        information_id)
    return success(None, "Informasi berhasil dihapus.")
