"""Model wilayah (regions) dan region keywords.

Geometry dipertukarkan sebagai GeoJSON ([longitude, latitude]).
MySQL mengonversi GeoJSON <-> GEOMETRY SRID 4326 secara langsung.
"""

import json

from database import execute, fetch_all, fetch_one, transaction

REGION_COLUMNS = (
    "r.id, r.parent_id, r.code, r.name, r.type, r.description, r.status, "
    "r.created_at, r.updated_at, p.name AS parent_name, "
    "(r.geometry IS NOT NULL) AS has_geometry"
)
REGION_FROM = "FROM regions r LEFT JOIN regions p ON p.id = r.parent_id"


def _decode_geometry(row):
    raw = row.pop("geometry_json", None)
    row["geometry"] = json.loads(raw) if raw else None
    return row


def list_regions(status=None, q=None, region_type=None):
    where, params = [], []
    if status:
        where.append("r.status = %s")
        params.append(status)
    if region_type:
        where.append("r.type = %s")
        params.append(region_type)
    if q:
        where.append("(r.name LIKE %s OR r.code LIKE %s)")
        params += [f"%{q}%", f"%{q}%"]
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    return fetch_all(
        f"SELECT {REGION_COLUMNS} {REGION_FROM}{where_sql} ORDER BY r.name",
        params,
    )


def get_region(region_id, include_geometry=False):
    geometry_sql = ""
    if include_geometry:
        geometry_sql = ", ST_AsGeoJSON(r.geometry, 7) AS geometry_json"
    row = fetch_one(
        f"SELECT {REGION_COLUMNS}{geometry_sql} {REGION_FROM} "
        "WHERE r.id = %s",
        (region_id,),
    )
    if row and include_geometry:
        _decode_geometry(row)
    return row


def list_hierarchy_nodes():
    """Semua wilayah (ringan, tanpa geometry) untuk membangun pohon."""
    return fetch_all(
        "SELECT id, parent_id, code, name, type, status "
        "FROM regions ORDER BY name"
    )


def list_active_geometries():
    """Wilayah aktif yang memiliki polygon, untuk Region Engine."""
    rows = fetch_all(
        "SELECT id, parent_id, code, name, type, "
        "ST_AsGeoJSON(geometry, 7) AS geometry_json "
        "FROM regions WHERE status = 'ACTIVE' AND geometry IS NOT NULL"
    )
    return [_decode_geometry(row) for row in rows]


def code_taken(code, exclude_id=None):
    sql = "SELECT id FROM regions WHERE code = %s"
    params = [code]
    if exclude_id is not None:
        sql += " AND id <> %s"
        params.append(exclude_id)
    return fetch_one(sql, params) is not None


def _geometry_sql(geometry):
    if geometry is None:
        return "NULL", []
    return "ST_GeomFromGeoJSON(%s, 1, 4326)", [json.dumps(geometry)]


def create_region(data):
    geom_sql, geom_params = _geometry_sql(data.get("geometry"))
    with transaction() as cursor:
        cursor.execute(
            "INSERT INTO regions (parent_id, code, name, type, geometry, "
            f"description, status) VALUES (%s, %s, %s, %s, {geom_sql}, %s, %s)",
            [data.get("parent_id"), data["code"], data["name"], data["type"]]
            + geom_params
            + [data.get("description"), data["status"]],
        )
        region_id = cursor.lastrowid
        _replace_keywords(cursor, region_id, data.get("keywords", []))
    return region_id


def update_region(region_id, data, update_geometry):
    fields = [
        "parent_id = %s", "code = %s", "name = %s", "type = %s",
        "description = %s", "status = %s",
    ]
    params = [
        data.get("parent_id"), data["code"], data["name"], data["type"],
        data.get("description"), data["status"],
    ]
    if update_geometry:
        geom_sql, geom_params = _geometry_sql(data.get("geometry"))
        fields.append(f"geometry = {geom_sql}")
        params += geom_params
    with transaction() as cursor:
        cursor.execute(
            f"UPDATE regions SET {', '.join(fields)} WHERE id = %s",
            params + [region_id],
        )
        if "keywords" in data:
            _replace_keywords(cursor, region_id, data["keywords"])


def delete_region(region_id):
    return execute("DELETE FROM regions WHERE id = %s", (region_id,))


def count_children(region_id):
    return fetch_one(
        "SELECT COUNT(*) AS total FROM regions WHERE parent_id = %s",
        (region_id,),
    )["total"]


def _replace_keywords(cursor, region_id, keywords):
    cursor.execute(
        "DELETE FROM region_keywords WHERE region_id = %s", (region_id,)
    )
    for keyword in keywords:
        cursor.execute(
            "INSERT IGNORE INTO region_keywords (region_id, keyword) "
            "VALUES (%s, %s)",
            (region_id, keyword),
        )


def get_keywords(region_id):
    rows = fetch_all(
        "SELECT keyword FROM region_keywords WHERE region_id = %s "
        "ORDER BY keyword",
        (region_id,),
    )
    return [row["keyword"] for row in rows]


def list_all_keywords():
    """Keyword wilayah aktif, untuk analisis berita eksternal."""
    return fetch_all(
        "SELECT k.region_id, k.keyword FROM region_keywords k "
        "JOIN regions r ON r.id = k.region_id WHERE r.status = 'ACTIVE'"
    )


def count_regions():
    return fetch_one("SELECT COUNT(*) AS total FROM regions")["total"]
