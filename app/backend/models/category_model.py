"""Model kategori."""

from database import execute, fetch_all, fetch_one
from models import unique_slug


def list_categories(active_only=False):
    sql = "SELECT * FROM categories"
    if active_only:
        sql += " WHERE status = 'ACTIVE'"
    return fetch_all(sql + " ORDER BY name")


def get_category(category_id):
    return fetch_one("SELECT * FROM categories WHERE id = %s", (category_id,))


def name_taken(name, exclude_id=None):
    sql = "SELECT id FROM categories WHERE name = %s"
    params = [name]
    if exclude_id is not None:
        sql += " AND id <> %s"
        params.append(exclude_id)
    return fetch_one(sql, params) is not None


def create_category(data):
    return execute(
        "INSERT INTO categories (name, slug, description, icon, status) "
        "VALUES (%s, %s, %s, %s, %s)",
        (data["name"], unique_slug("categories", data["name"]),
         data.get("description"), data.get("icon"), data["status"]),
    )


def update_category(category_id, data):
    execute(
        "UPDATE categories SET name = %s, slug = %s, description = %s, "
        "icon = %s, status = %s WHERE id = %s",
        (data["name"],
         unique_slug("categories", data["name"], exclude_id=category_id),
         data.get("description"), data.get("icon"), data["status"],
         category_id),
    )


def delete_category(category_id):
    return execute("DELETE FROM categories WHERE id = %s", (category_id,))
