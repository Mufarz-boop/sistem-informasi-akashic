"""CRUD wilayah (polygon) dan pohon hierarki."""

from flask import Blueprint, request

from models import region_model
from services import region_engine
from utils import validators as v
from utils.api import APIError, Conflict, NotFound, success
from utils.security import admin_required, is_admin_scope, log

region_bp = Blueprint("regions", __name__, url_prefix="/api/regions")

TYPES = ("COUNTRY", "PROVINCE", "REGENCY", "CITY", "DISTRICT", "VILLAGE",
         "LOCAL")
STATUSES = ("ACTIVE", "INACTIVE")


def _prune_inactive(nodes):
    return [
        dict(node, children=_prune_inactive(node["children"]))
        for node in nodes if node["status"] == "ACTIVE"
    ]


@region_bp.get("")
def list_regions():
    admin_scope = is_admin_scope()
    status = None
    if admin_scope:
        if request.args.get("status"):
            status = v.choice(request.args.get("status"), "status", STATUSES)
    else:
        status = "ACTIVE"
    region_type = None
    if request.args.get("type"):
        region_type = v.choice(request.args.get("type"), "type", TYPES)
    q = (request.args.get("q") or "").strip()[:100] or None
    return success(region_model.list_regions(status, q, region_type))


@region_bp.get("/tree")
def region_tree():
    nodes = region_engine.tree()
    if not is_admin_scope():
        nodes = _prune_inactive(nodes)
    return success(nodes)


@region_bp.get("/<int:region_id>")
def get_region(region_id):
    admin_scope = is_admin_scope()
    include_geometry = request.args.get("geometry") in ("1", "true")
    region = region_model.get_region(region_id, include_geometry)
    if not region or (not admin_scope and region["status"] != "ACTIVE"):
        raise NotFound("Wilayah tidak ditemukan.")
    region["hierarchy"] = region_engine.hierarchy(region_id)
    region["keywords"] = region_model.get_keywords(region_id)
    region["children_count"] = region_model.count_children(region_id)
    return success(region)


def _validate(data, region_id=None):
    code = v.string(data, "code", "Kode wilayah", max_length=50)
    if region_model.code_taken(code, region_id):
        raise Conflict("Kode wilayah sudah digunakan.")
    parent_id = v.integer(data.get("parent_id"), "Parent", required=False)
    if parent_id:
        if not region_model.get_region(parent_id):
            raise APIError("Parent wilayah tidak ditemukan.")
        if region_id and parent_id in region_engine.descendant_ids(region_id):
            raise APIError("Parent tidak boleh wilayah itu sendiri atau "
                           "turunannya.")
    cleaned = {
        "parent_id": parent_id,
        "code": code,
        "name": v.string(data, "name", "Nama wilayah", max_length=150),
        "type": v.choice(data.get("type"), "Tipe wilayah", TYPES),
        "description": v.string(data, "description", "Deskripsi",
                                required=False, max_length=5000),
        "status": v.choice(data.get("status"), "Status", STATUSES,
                           default="ACTIVE"),
    }
    if "geometry" in data:
        try:
            cleaned["geometry"] = (
                region_engine.validate_geometry(data["geometry"])
                if data["geometry"] else None
            )
        except region_engine.GeometryError as exc:
            raise APIError(str(exc), 400, "invalid_geometry") from exc
    if "keywords" in data:
        cleaned["keywords"] = v.keywords(data["keywords"])
    return cleaned


@region_bp.post("")
@admin_required
def create_region():
    data = _validate(v.json_body())
    data.setdefault("keywords", [data["name"]])
    region_id = region_model.create_region(data)
    region_engine.invalidate_cache()
    log("CREATE", f"Membuat wilayah: {data['name']}", "region", region_id)
    return success(region_model.get_region(region_id),
                   "Wilayah berhasil dibuat.", 201)


@region_bp.put("/<int:region_id>")
@admin_required
def update_region(region_id):
    if not region_model.get_region(region_id):
        raise NotFound("Wilayah tidak ditemukan.")
    data = _validate(v.json_body(), region_id)
    region_model.update_region(region_id, data, "geometry" in data)
    region_engine.invalidate_cache()
    log("UPDATE", f"Memperbarui wilayah: {data['name']}", "region",
        region_id)
    return success(region_model.get_region(region_id),
                   "Wilayah berhasil diperbarui.")


@region_bp.delete("/<int:region_id>")
@admin_required
def delete_region(region_id):
    region = region_model.get_region(region_id)
    if not region:
        raise NotFound("Wilayah tidak ditemukan.")
    if region_model.count_children(region_id):
        raise Conflict("Hapus atau pindahkan sub-wilayah terlebih dahulu.")
    region_model.delete_region(region_id)
    region_engine.invalidate_cache()
    log("DELETE", f"Menghapus wilayah: {region['name']}", "region",
        region_id)
    return success(None, "Wilayah berhasil dihapus.")
