"""Model notifikasi yang dikirim melalui Web Push."""

from database import execute, fetch_all
from models import in_clause


def create_notification(data):
    return execute(
        "INSERT INTO notifications (region_id, information_id, event_id, "
        "news_id, type, title, message, url) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (data.get("region_id"), data.get("information_id"),
         data.get("event_id"), data.get("news_id"), data["type"],
         data["title"], data["message"], data.get("url")),
    )


def update_delivery(notification_id, sent, failed):
    execute(
        "UPDATE notifications SET sent_count = %s, failed_count = %s "
        "WHERE id = %s",
        (sent, failed, notification_id),
    )


def already_notified(column, entity_id):
    """Mencegah notifikasi ganda untuk konten yang sama."""
    allowed = {"information_id", "event_id", "news_id"}
    if column not in allowed:
        raise ValueError("Kolom notifikasi tidak valid")
    rows = fetch_all(
        f"SELECT id FROM notifications WHERE {column} = %s LIMIT 1",
        (entity_id,),
    )
    return bool(rows)


def list_notifications(region_ids=None, limit=20):
    sql = (
        "SELECT n.id, n.type, n.title, n.message, n.url, n.region_id, "
        "n.sent_count, n.failed_count, n.created_at, r.name AS region_name "
        "FROM notifications n LEFT JOIN regions r ON r.id = n.region_id"
    )
    params = []
    if region_ids:
        clause, values = in_clause("n.region_id", region_ids)
        sql += f" WHERE ({clause} OR n.region_id IS NULL)"
        params += values
    sql += " ORDER BY n.created_at DESC, n.id DESC LIMIT %s"
    return fetch_all(sql, params + [limit])
