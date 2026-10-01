"""Deteksi wilayah dari koordinat browser dan feed berbasis wilayah.

Koordinat tidak disimpan; hanya dipakai selama request.
"""

from flask import Blueprint, request

from services import feed_engine, location_engine
from utils import validators as v
from utils.api import APIError, success

location_bp = Blueprint("location", __name__, url_prefix="/api")

SORTS = ("newest", "oldest", "title")


@location_bp.post("/location/detect")
def detect():
    try:
        result = location_engine.detect(v.json_body())
    except location_engine.LocationError as exc:
        raise APIError(str(exc), 400, "invalid_location") from exc
    if result["region"]:
        message = f"Anda berada di {result['region']['name']}."
    else:
        message = "Lokasi Anda belum termasuk wilayah yang terdaftar."
    return success(result, message)


@location_bp.get("/feed")
def feed():
    args = request.args
    page, per_page = v.pagination(args)
    page = min(page, feed_engine.MAX_WINDOW // per_page)
    types = [t.strip() for t in (args.get("types") or "").split(",")
             if t.strip()]
    filters = {
        "region_id": v.integer(args.get("region_id"), "region_id",
                               required=False),
        "category_id": v.integer(args.get("category_id"), "category_id",
                                 required=False),
        "types": types or None,
        "q": (args.get("q") or "").strip()[:100] or None,
        "sort": args.get("sort") if args.get("sort") in SORTS else "newest",
    }
    filters.update(v.date_range(args))
    return success(feed_engine.get_feed(filters, page, per_page))
