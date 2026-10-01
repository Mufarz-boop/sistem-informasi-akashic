"""Model berita eksternal (news) dan sumber berita (news_sources)."""

from database import execute, fetch_all, fetch_one
from models import SORT_DIRECTIONS, in_clause, paginate

SELECT_SQL = (
    "SELECT n.id, n.source_id, n.region_id, n.category_id, n.title, "
    "n.summary, n.source_url, n.image_url, n.author, n.keywords, "
    "n.relevance_method, n.status, n.published_at, n.discovered_at, "
    "n.moderated_at, n.created_at, n.updated_at, "
    "COALESCE(n.published_at, n.discovered_at) AS sort_at, "
    "s.name AS source_name, s.website_url AS source_website, "
    "c.name AS category_name, c.slug AS category_slug, "
    "r.name AS region_name, r.type AS region_type"
)
FROM_SQL = (
    "FROM news n "
    "JOIN news_sources s ON s.id = n.source_id "
    "LEFT JOIN categories c ON c.id = n.category_id "
    "LEFT JOIN regions r ON r.id = n.region_id"
)
STATUSES = ("PENDING", "APPROVED", "REJECTED", "ARCHIVED")


def build_filters(filters):
    where, params = [], []
    if filters.get("public"):
        where.append("n.status = 'APPROVED'")
    elif filters.get("status"):
        where.append("n.status = %s")
        params.append(filters["status"])
    if filters.get("region_ids"):
        clause, values = in_clause("n.region_id", filters["region_ids"])
        where.append(clause)
        params += values
    if filters.get("category_id"):
        where.append("n.category_id = %s")
        params.append(filters["category_id"])
    if filters.get("source_id"):
        where.append("n.source_id = %s")
        params.append(filters["source_id"])
    if filters.get("q"):
        where.append("(n.title LIKE %s OR n.summary LIKE %s)")
        params += [f"%{filters['q']}%"] * 2
    if filters.get("date_from"):
        where.append("COALESCE(n.published_at, n.discovered_at) >= %s")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        where.append("COALESCE(n.published_at, n.discovered_at) < %s")
        params.append(filters["date_to"])
    return where, params


def list_news(filters, page=1, per_page=12):
    where, params = build_filters(filters)
    sort = filters.get("sort", "newest")
    if sort == "title":
        order = "n.title ASC, n.id ASC"
    else:
        order = f"sort_at {SORT_DIRECTIONS.get(sort, 'DESC')}, n.id DESC"
    return paginate(SELECT_SQL, FROM_SQL, where, params, order, page, per_page)


def get_news(news_id, public=False):
    sql = f"{SELECT_SQL} {FROM_SQL} WHERE n.id = %s"
    if public:
        sql += " AND n.status = 'APPROVED'"
    return fetch_one(sql, (news_id,))


def insert_news_if_new(item):
    """INSERT IGNORE: duplikat (external_id sama) dilewati.

    Mengembalikan id berita baru, atau None jika sudah ada.
    """
    new_id = execute(
        "INSERT IGNORE INTO news (source_id, region_id, category_id, "
        "external_id, title, summary, source_url, image_url, author, "
        "keywords, relevance_method, published_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (item["source_id"], item.get("region_id"), item.get("category_id"),
         item["external_id"], item["title"], item.get("summary"),
         item["source_url"], item.get("image_url"), item.get("author"),
         item.get("keywords"), item.get("relevance_method"),
         item.get("published_at")),
    )
    return new_id or None


def update_news(news_id, data, admin_id):
    execute(
        "UPDATE news SET title = %s, summary = %s, region_id = %s, "
        "category_id = %s, status = %s, moderated_by = %s, "
        "moderated_at = UTC_TIMESTAMP() WHERE id = %s",
        (data["title"], data.get("summary"), data.get("region_id"),
         data.get("category_id"), data["status"], admin_id, news_id),
    )


def delete_news(news_id):
    return execute("DELETE FROM news WHERE id = %s", (news_id,))


def count_news(status=None):
    if status:
        return fetch_one(
            "SELECT COUNT(*) AS total FROM news WHERE status = %s", (status,)
        )["total"]
    return fetch_one("SELECT COUNT(*) AS total FROM news")["total"]


# ---------------------------------------------------------------- sources

SOURCE_SELECT = (
    "SELECT s.*, r.name AS region_name, c.name AS category_name, "
    "(SELECT COUNT(*) FROM news n WHERE n.source_id = s.id) AS news_count "
    "FROM news_sources s "
    "LEFT JOIN regions r ON r.id = s.region_id "
    "LEFT JOIN categories c ON c.id = s.category_id"
)


def list_sources(active_only=False):
    sql = SOURCE_SELECT
    if active_only:
        sql += " WHERE s.status = 'ACTIVE'"
    return fetch_all(sql + " ORDER BY s.name")


def get_source(source_id):
    return fetch_one(SOURCE_SELECT + " WHERE s.id = %s", (source_id,))


def rss_url_taken(rss_url, exclude_id=None):
    sql = "SELECT id FROM news_sources WHERE rss_url = %s"
    params = [rss_url]
    if exclude_id is not None:
        sql += " AND id <> %s"
        params.append(exclude_id)
    return fetch_one(sql, params) is not None


def create_source(data):
    return execute(
        "INSERT INTO news_sources (name, website_url, rss_url, region_id, "
        "category_id, status) VALUES (%s, %s, %s, %s, %s, %s)",
        (data["name"], data["website_url"], data["rss_url"],
         data.get("region_id"), data.get("category_id"), data["status"]),
    )


def update_source(source_id, data):
    execute(
        "UPDATE news_sources SET name = %s, website_url = %s, rss_url = %s, "
        "region_id = %s, category_id = %s, status = %s WHERE id = %s",
        (data["name"], data["website_url"], data["rss_url"],
         data.get("region_id"), data.get("category_id"), data["status"],
         source_id),
    )


def delete_source(source_id):
    return execute("DELETE FROM news_sources WHERE id = %s", (source_id,))


def mark_source_checked(source_id, error=None):
    execute(
        "UPDATE news_sources SET last_checked_at = UTC_TIMESTAMP(), "
        "last_error = %s WHERE id = %s",
        ((error or "")[:500] or None, source_id),
    )
