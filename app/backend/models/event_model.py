"""Model Event (kegiatan dengan waktu dan lokasi)."""

from database import execute, fetch_one
from models import SORT_DIRECTIONS, in_clause, paginate

SELECT_SQL = (
    "SELECT e.id, e.region_id, e.category_id, e.admin_id, e.title, "
    "e.description, e.location_name, e.latitude, e.longitude, e.start_at, "
    "e.end_at, e.status, e.created_at, e.updated_at, "
    "e.created_at AS sort_at, "
    "c.name AS category_name, c.slug AS category_slug, "
    "r.name AS region_name, r.type AS region_type"
)
FROM_SQL = (
    "FROM events e "
    "LEFT JOIN categories c ON c.id = e.category_id "
    "JOIN regions r ON r.id = e.region_id"
)
# Event publik = sudah dipublikasikan dan belum selesai.
PUBLIC_CONDITION = (
    "e.status = 'PUBLISHED' "
    "AND COALESCE(e.end_at, e.start_at) >= UTC_TIMESTAMP() - INTERVAL 1 DAY"
)


def build_filters(filters):
    where, params = [], []
    if filters.get("public"):
        where.append(PUBLIC_CONDITION)
    elif filters.get("status"):
        where.append("e.status = %s")
        params.append(filters["status"])
    if filters.get("region_ids"):
        clause, values = in_clause("e.region_id", filters["region_ids"])
        where.append(clause)
        params += values
    if filters.get("category_id"):
        where.append("e.category_id = %s")
        params.append(filters["category_id"])
    if filters.get("q"):
        where.append(
            "(e.title LIKE %s OR e.description LIKE %s "
            "OR e.location_name LIKE %s)"
        )
        params += [f"%{filters['q']}%"] * 3
    if filters.get("date_from"):
        where.append("e.start_at >= %s")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        where.append("e.start_at < %s")
        params.append(filters["date_to"])
    return where, params


def list_events(filters, page=1, per_page=12):
    where, params = build_filters(filters)
    sort = filters.get("sort", "newest")
    if sort == "title":
        order = "e.title ASC, e.id ASC"
    elif sort == "upcoming":
        order = "e.start_at ASC, e.id ASC"
    else:
        order = f"sort_at {SORT_DIRECTIONS.get(sort, 'DESC')}, e.id DESC"
    return paginate(SELECT_SQL, FROM_SQL, where, params, order, page, per_page)


def get_event(event_id, public=False):
    sql = f"{SELECT_SQL} {FROM_SQL} WHERE e.id = %s"
    if public:
        sql += f" AND {PUBLIC_CONDITION}"
    return fetch_one(sql, (event_id,))


def _values(data):
    return (
        data["region_id"], data.get("category_id"), data["title"],
        data.get("description"), data.get("location_name"),
        data.get("latitude"), data.get("longitude"), data["start_at"],
        data.get("end_at"), data["status"],
    )


def create_event(data, admin_id):
    return execute(
        "INSERT INTO events (region_id, category_id, title, description, "
        "location_name, latitude, longitude, start_at, end_at, status, "
        "admin_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        _values(data) + (admin_id,),
    )


def update_event(event_id, data):
    execute(
        "UPDATE events SET region_id = %s, category_id = %s, title = %s, "
        "description = %s, location_name = %s, latitude = %s, "
        "longitude = %s, start_at = %s, end_at = %s, status = %s "
        "WHERE id = %s",
        _values(data) + (event_id,),
    )


def delete_event(event_id):
    return execute("DELETE FROM events WHERE id = %s", (event_id,))


def count_events():
    return fetch_one("SELECT COUNT(*) AS total FROM events")["total"]
