"""Model Web Push subscription.

Subscription hanya berisi endpoint + kunci enkripsi dari browser.
Tidak ada data identitas pengguna maupun koordinat.
"""

import hashlib

from database import execute, fetch_all, fetch_one
from models import in_clause


def endpoint_hash(endpoint):
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


def upsert_subscription(endpoint, p256dh, auth, region_id):
    execute(
        "INSERT INTO push_subscriptions "
        "(endpoint, endpoint_hash, p256dh_key, auth_key, region_id, status) "
        "VALUES (%s, %s, %s, %s, %s, 'ACTIVE') "
        "ON DUPLICATE KEY UPDATE p256dh_key = VALUES(p256dh_key), "
        "auth_key = VALUES(auth_key), region_id = VALUES(region_id), "
        "status = 'ACTIVE'",
        (endpoint, endpoint_hash(endpoint), p256dh, auth, region_id),
    )


def update_region(endpoint, region_id):
    return execute(
        "UPDATE push_subscriptions SET region_id = %s "
        "WHERE endpoint_hash = %s",
        (region_id, endpoint_hash(endpoint)),
    )


def delete_subscription(endpoint):
    return execute(
        "DELETE FROM push_subscriptions WHERE endpoint_hash = %s",
        (endpoint_hash(endpoint),),
    )


def deactivate(subscription_id):
    execute(
        "UPDATE push_subscriptions SET status = 'INACTIVE' WHERE id = %s",
        (subscription_id,),
    )


def list_targets(region_ids):
    """Subscription aktif yang wilayahnya termasuk `region_ids`.

    Jika region_ids kosong (notifikasi umum), semua subscription aktif
    menjadi target.
    """
    sql = (
        "SELECT id, endpoint, p256dh_key, auth_key FROM push_subscriptions "
        "WHERE status = 'ACTIVE'"
    )
    params = []
    if region_ids:
        clause, values = in_clause("region_id", region_ids)
        sql += f" AND {clause}"
        params += values
    return fetch_all(sql, params)


def count_active():
    return fetch_one(
        "SELECT COUNT(*) AS total FROM push_subscriptions "
        "WHERE status = 'ACTIVE'"
    )["total"]
