"""Model Information (konten internal buatan admin)."""

from database import execute, fetch_one
from models import SORT_DIRECTIONS, in_clause, paginate, unique_slug

SELECT_SQL = (
    "SELECT i.id, i.category_id, i.region_id, i.admin_id, i.title, i.slug, "
    "i.summary, i.content, i.image, i.priority, i.status, i.published_at, "
    "i.expired_at, i.created_at, i.updated_at, "
    "COALESCE(i.published_at, i.created_at) AS sort_at, "
    "c.name AS category_name, c.slug AS category_slug, "
    "r.name AS region_name, r.type AS region_type"
)
FROM_SQL = (
    "FROM informations i "
    "JOIN categories c ON c.id = i.category_id "
    "JOIN regions r ON r.id = i.region_id"
)
PUBLIC_CONDITION = (
    "i.status = 'PUBLISHED' "
    "AND (i.published_at IS NULL OR i.published_at <= UTC_TIMESTAMP()) "
    "AND (i.expired_at IS NULL OR i.expired_at > UTC_TIMESTAMP())"
)


def build_filters(filters):
    where, params = [], []
    if filters.get("public"):
        where.append(PUBLIC_CONDITION)
    elif filters.get("status"):
        where.append("i.status = %s")
        params.append(filters["status"])
    if filters.get("region_ids"):
        clause, values = in_clause("i.region_id", filters["region_ids"])
        where.append(clause)
        params += values
    if filters.get("category_id"):
        where.append("i.category_id = %s")
        params.append(filters["category_id"])
    if filters.get("q"):
        where.append("(i.title LIKE %s OR i.summary LIKE %s)")
        params += [f"%{filters['q']}%"] * 2
    if filters.get("date_from"):
        where.append("COALESCE(i.published_at, i.created_at) >= %s")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        where.append("COALESCE(i.published_at, i.created_at) < %s")
        params.append(filters["date_to"])
    return where, params


def list_information(filters, page=1, per_page=12):
    where, params = build_filters(filters)
    sort = filters.get("sort", "newest")
    if sort == "title":
        order = "i.title ASC, i.id ASC"
    else:
        order = f"sort_at {SORT_DIRECTIONS.get(sort, 'DESC')}, i.id DESC"
    return paginate(SELECT_SQL, FROM_SQL, where, params, order, page, per_page)


def get_information(information_id, public=False):
    sql = f"{SELECT_SQL} {FROM_SQL} WHERE i.id = %s"
    if public:
        sql += f" AND {PUBLIC_CONDITION}"
    return fetch_one(sql, (information_id,))


def create_information(data, admin_id):
    return execute(
        "INSERT INTO informations (category_id, region_id, admin_id, title, "
        "slug, summary, content, image, priority, status, published_at, "
        "expired_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (data["category_id"], data["region_id"], admin_id, data["title"],
         unique_slug("informations", data["title"]), data.get("summary"),
         data["content"], data.get("image"), data["priority"], data["status"],
         data.get("published_at"), data.get("expired_at")),
    )


def update_information(information_id, data):
    execute(
        "UPDATE informations SET category_id = %s, region_id = %s, "
        "title = %s, slug = %s, summary = %s, content = %s, image = %s, "
        "priority = %s, status = %s, published_at = %s, expired_at = %s "
        "WHERE id = %s",
        (data["category_id"], data["region_id"], data["title"],
         unique_slug("informations", data["title"], information_id),
         data.get("summary"), data["content"], data.get("image"),
         data["priority"], data["status"], data.get("published_at"),
         data.get("expired_at"), information_id),
    )


def delete_information(information_id):
    return execute("DELETE FROM informations WHERE id = %s", (information_id,))


def count_information():
    return fetch_one("SELECT COUNT(*) AS total FROM informations")["total"]
