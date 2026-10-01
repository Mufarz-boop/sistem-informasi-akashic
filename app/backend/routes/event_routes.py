"""CRUD Event."""

from flask import Blueprint, request

from models import category_model, event_model, region_model
from services import notification_engine, region_engine
from utils import validators as v
from utils.api import APIError, NotFound, success
from utils.security import admin_required, current_admin, is_admin_scope, log

event_bp = Blueprint("events", __name__, url_prefix="/api/events")

STATUSES = ("DRAFT", "PUBLISHED", "CANCELLED", "ARCHIVED")
SORTS = ("newest", "oldest", "title", "upcoming")


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
    region_id = v.integer(data.get("region_id"), "Wilayah")
    if not region_model.get_region(region_id):
        raise APIError("Wilayah tidak ditemukan.")
    category_id = v.integer(data.get("category_id"), "Kategori",
                            required=False)
    if category_id and not category_model.get_category(category_id):
        raise APIError("Kategori tidak ditemukan.")
    start_at = v.datetime_value(data.get("start_at"), "Waktu mulai",
                                required=True)
    end_at = v.datetime_value(data.get("end_at"), "Waktu selesai")
    if end_at and end_at < start_at:
        raise APIError("Waktu selesai harus setelah waktu mulai.")
    latitude = v.number(data.get("latitude"), "Latitude", -90, 90)
    longitude = v.number(data.get("longitude"), "Longitude", -180, 180)
    if (latitude is None) != (longitude is None):
        raise APIError("Latitude dan longitude harus diisi bersamaan.")
    return {
        "region_id": region_id,
        "category_id": category_id,
        "title": v.string(data, "title", "Judul", min_length=3),
        "description": v.string(data, "description", "Deskripsi",
                                required=False, max_length=20_000),
        "location_name": v.string(data, "location_name", "Lokasi",
                                  required=False),
        "latitude": latitude,
        "longitude": longitude,
        "start_at": start_at,
        "end_at": end_at,
        "status": v.choice(data.get("status"), "Status", STATUSES,
                           default="DRAFT"),
    }


def _notify_if_published(event):
    if event and event["status"] == "PUBLISHED":
        notification_engine.notify_event(event)


@event_bp.get("")
def list_events():
    admin_scope = is_admin_scope()
    page, per_page = v.pagination(request.args)
    return success(event_model.list_events(
        list_filters(request.args, admin_scope), page, per_page
    ))


@event_bp.get("/<int:event_id>")
def get_event(event_id):
    admin_scope = is_admin_scope()
    event = event_model.get_event(event_id, public=not admin_scope)
    if not event:
        raise NotFound("Event tidak ditemukan.")
    event["hierarchy"] = region_engine.hierarchy(event["region_id"])
    return success(event)


@event_bp.post("")
@admin_required
def create_event():
    data = _validate(v.json_body())
    new_id = event_model.create_event(data, current_admin()["id"])
    log("CREATE", f"Membuat event: {data['title']}", "event", new_id)
    event = event_model.get_event(new_id)
    _notify_if_published(event)
    return success(event, "Event berhasil dibuat.", 201)


@event_bp.put("/<int:event_id>")
@admin_required
def update_event(event_id):
    if not event_model.get_event(event_id):
        raise NotFound("Event tidak ditemukan.")
    data = _validate(v.json_body())
    event_model.update_event(event_id, data)
    log("UPDATE", f"Memperbarui event: {data['title']}", "event", event_id)
    event = event_model.get_event(event_id)
    _notify_if_published(event)
    return success(event, "Event berhasil diperbarui.")


@event_bp.delete("/<int:event_id>")
@admin_required
def delete_event(event_id):
    event = event_model.get_event(event_id)
    if not event:
        raise NotFound("Event tidak ditemukan.")
    event_model.delete_event(event_id)
    log("DELETE", f"Menghapus event: {event['title']}", "event", event_id)
    return success(None, "Event berhasil dihapus.")
