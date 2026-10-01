"""Helper bersama untuk seluruh model."""

import re
import unicodedata

from database import fetch_all, fetch_one

SORT_DIRECTIONS = {"newest": "DESC", "oldest": "ASC"}


def in_clause(column, values):
    """Membuat potongan SQL `column IN (%s, %s, ...)` yang aman."""
    placeholders = ", ".join(["%s"] * len(values))
    return f"{column} IN ({placeholders})", list(values)


def paginate(select_sql, from_sql, where, params, order_sql, page, per_page):
    """Menjalankan query list + count dengan LIMIT/OFFSET."""
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    total = fetch_one(
        f"SELECT COUNT(*) AS total {from_sql}{where_sql}", params
    )["total"]
    rows = fetch_all(
        f"{select_sql} {from_sql}{where_sql} ORDER BY {order_sql} "
        "LIMIT %s OFFSET %s",
        list(params) + [per_page, (page - 1) * per_page],
    )
    return {
        "items": rows,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if per_page else 0,
    }


def slugify(text):
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug[:200] or "item"


def unique_slug(table, text, exclude_id=None):
    """Slug unik untuk tabel `table` (nama tabel berasal dari kode)."""
    base = slugify(text)
    slug = base
    counter = 2
    while True:
        sql = f"SELECT id FROM {table} WHERE slug = %s"
        params = [slug]
        if exclude_id is not None:
            sql += " AND id <> %s"
            params.append(exclude_id)
        if not fetch_one(sql, params):
            return slug
        slug = f"{base}-{counter}"
        counter += 1
