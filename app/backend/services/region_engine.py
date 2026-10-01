"""Region Engine: menentukan wilayah berdasarkan titik koordinat.

Pencocokan memakai polygon (point-in-polygon), bukan radius.
Polygon dimuat dari database sekali lalu disimpan di memori
(prepared geometry) agar setiap deteksi cepat. Cache dibuang setiap
kali admin mengubah wilayah.
"""

import math
import threading

from shapely import affinity, get_num_coordinates
from shapely.geometry import Point, shape
from shapely.prepared import prep
from shapely.validation import explain_validity

from models import region_model

METERS_PER_DEGREE = 111_320
ALLOWED_GEOMETRY_TYPES = ("Polygon", "MultiPolygon")
MAX_GEOMETRY_POINTS = 20_000

_lock = threading.Lock()
_cache = None


class GeometryError(ValueError):
    """GeoJSON wilayah tidak valid."""


def invalidate_cache():
    global _cache
    with _lock:
        _cache = None


def _load():
    global _cache
    with _lock:
        if _cache is not None:
            return _cache
        nodes = {row["id"]: row for row in region_model.list_hierarchy_nodes()}
        shapes = []
        for row in region_model.list_active_geometries():
            geom = shape(row["geometry"])
            shapes.append({
                "id": row["id"],
                "geometry": geom,
                "prepared": prep(geom),
                "area": geom.area,
            })
        _cache = {"nodes": nodes, "shapes": shapes}
        return _cache


def depth(region_id, nodes=None):
    nodes = nodes or _load()["nodes"]
    level, current, seen = 0, nodes.get(region_id), set()
    while current and current["parent_id"] and current["id"] not in seen:
        seen.add(current["id"])
        level += 1
        current = nodes.get(current["parent_id"])
    return level


def hierarchy(region_id):
    """Rantai wilayah dari akar (negara) sampai wilayah ini."""
    nodes = _load()["nodes"]
    chain, current, seen = [], nodes.get(region_id), set()
    while current and current["id"] not in seen:
        seen.add(current["id"])
        chain.append(_public_node(current))
        current = nodes.get(current["parent_id"])
    return list(reversed(chain))


def ancestor_ids(region_id):
    return [node["id"] for node in hierarchy(region_id)]


def descendant_ids(region_id):
    """Wilayah ini beserta seluruh turunannya."""
    nodes = _load()["nodes"]
    children = {}
    for node in nodes.values():
        children.setdefault(node["parent_id"], []).append(node["id"])
    result, stack = [], [region_id]
    while stack:
        current = stack.pop()
        if current in result:
            continue
        result.append(current)
        stack.extend(children.get(current, []))
    return result


def related_ids(region_id):
    """Wilayah yang relevan untuk feed: leluhur + diri + turunan."""
    return list(dict.fromkeys(ancestor_ids(region_id)
                              + descendant_ids(region_id)))


def tree():
    """Pohon wilayah bersarang untuk visualisasi di admin."""
    nodes = _load()["nodes"]
    by_parent = {}
    for node in nodes.values():
        by_parent.setdefault(node["parent_id"], []).append(node)

    def build(parent_id, seen):
        branch = []
        for node in sorted(by_parent.get(parent_id, []),
                           key=lambda item: item["name"]):
            if node["id"] in seen:
                continue
            item = _public_node(node)
            item["status"] = node["status"]
            item["children"] = build(node["id"], seen | {node["id"]})
            branch.append(item)
        return branch

    return build(None, set())


def find_region(latitude, longitude, accuracy=None):
    """Mencari wilayah terdalam yang memuat titik.

    Mengembalikan dict berisi region, parent, hierarchy, dan
    confidence; atau None jika titik di luar semua wilayah.
    """
    cache = _load()
    point = Point(longitude, latitude)
    matches = [item for item in cache["shapes"]
               if item["prepared"].covers(point)]
    if not matches:
        return None

    nodes = cache["nodes"]
    # Wilayah paling spesifik = paling dalam di hierarki; jika setara,
    # pilih yang luasnya paling kecil.
    best = max(matches, key=lambda item: (depth(item["id"], nodes),
                                          -item["area"]))
    chain = hierarchy(best["id"])
    return {
        "region": chain[-1],
        "parent_region": chain[-2] if len(chain) > 1 else None,
        "hierarchy": chain,
        "confidence": _confidence(best["geometry"], point, latitude, accuracy),
    }


def _confidence(geometry, point, latitude, accuracy):
    """'high' jika seluruh lingkaran akurasi berada di dalam wilayah."""
    if not accuracy:
        return "unknown"
    lat_deg = accuracy / METERS_PER_DEGREE
    lon_deg = accuracy / (METERS_PER_DEGREE
                          * max(math.cos(math.radians(latitude)), 0.01))
    # Lingkaran akurasi dalam derajat (elips karena 1 derajat bujur
    # mengecil mendekati kutub).
    circle = affinity.scale(point.buffer(1, 16), xfact=lon_deg,
                            yfact=lat_deg, origin=point)
    return "high" if geometry.covers(circle) else "approximate"


def validate_geometry(geojson):
    """Memvalidasi GeoJSON Polygon/MultiPolygon dari admin."""
    if not isinstance(geojson, dict):
        raise GeometryError("Polygon harus berupa objek GeoJSON.")
    if geojson.get("type") == "Feature":
        geojson = geojson.get("geometry") or {}
    if geojson.get("type") not in ALLOWED_GEOMETRY_TYPES:
        raise GeometryError("Tipe geometry harus Polygon atau MultiPolygon.")
    try:
        geom = shape(geojson)
    except (ValueError, TypeError, AttributeError, IndexError) as exc:
        raise GeometryError(f"GeoJSON tidak dapat dibaca: {exc}") from exc
    if geom.is_empty:
        raise GeometryError("Polygon kosong.")
    if get_num_coordinates(geom) > MAX_GEOMETRY_POINTS:
        raise GeometryError("Polygon terlalu detail, sederhanakan dahulu.")
    min_x, min_y, max_x, max_y = geom.bounds
    if min_x < -180 or max_x > 180 or min_y < -90 or max_y > 90:
        raise GeometryError(
            "Koordinat di luar jangkauan. Gunakan urutan "
            "[longitude, latitude]."
        )
    if not geom.is_valid:
        raise GeometryError(f"Polygon tidak valid: {explain_validity(geom)}")
    return geom.__geo_interface__


def _public_node(node):
    return {
        "id": node["id"],
        "name": node["name"],
        "type": node["type"].lower(),
        "code": node["code"],
        "parent_id": node["parent_id"],
    }
