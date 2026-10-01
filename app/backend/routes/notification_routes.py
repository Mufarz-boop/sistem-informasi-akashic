"""Web Push subscription dan daftar notifikasi publik.

Subscription bersifat anonim: hanya endpoint push service + kunci
enkripsi dari browser, dengan wilayah terakhir (opsional).
"""

from urllib.parse import urlparse

from flask import Blueprint, request

from config import Config
from models import notification_model, push_subscription_model, \
    region_model
from services import region_engine
from utils import validators as v
from utils.api import APIError, success

notification_bp = Blueprint("notifications", __name__,
                            url_prefix="/api/notifications")


def _endpoint(data):
    endpoint = data.get("endpoint")
    if not isinstance(endpoint, str) or len(endpoint) > 2000:
        raise APIError("Endpoint subscription tidak valid.")
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.netloc:
        raise APIError("Endpoint subscription harus URL https.")
    return endpoint


def _region(data):
    region_id = v.integer(data.get("region_id"), "Wilayah", required=False)
    if region_id:
        region = region_model.get_region(region_id)
        if not region or region["status"] != "ACTIVE":
            raise APIError("Wilayah tidak ditemukan.")
    return region_id


@notification_bp.get("")
def list_notifications():
    region_id = v.integer(request.args.get("region_id"), "region_id",
                          required=False)
    limit = min(v.integer(request.args.get("limit") or 20, "limit"), 50)
    region_ids = region_engine.ancestor_ids(region_id) if region_id else None
    return success(notification_model.list_notifications(region_ids, limit))


@notification_bp.get("/public-key")
def public_key():
    return success({
        "enabled": Config.push_enabled(),
        "public_key": Config.VAPID_PUBLIC_KEY if Config.push_enabled()
        else None,
    })


@notification_bp.post("/subscribe")
def subscribe():
    if not Config.push_enabled():
        raise APIError("Web Push belum dikonfigurasi di server.", 503,
                       "push_disabled")
    data = v.json_body()
    subscription = data.get("subscription")
    if not isinstance(subscription, dict):
        raise APIError("Data subscription wajib dikirim.")
    keys = subscription.get("keys")
    if not isinstance(keys, dict):
        raise APIError("Kunci subscription tidak lengkap.")
    p256dh = v.string(keys, "p256dh", "Kunci p256dh", max_length=255)
    auth = v.string(keys, "auth", "Kunci auth", max_length=255)
    push_subscription_model.upsert_subscription(
        _endpoint(subscription), p256dh, auth, _region(data)
    )
    return success(None, "Notifikasi wilayah diaktifkan.", 201)


@notification_bp.put("/region")
def update_region():
    data = v.json_body()
    push_subscription_model.update_region(_endpoint(data), _region(data))
    return success(None, "Wilayah notifikasi diperbarui.")


@notification_bp.delete("/unsubscribe")
def unsubscribe():
    data = v.json_body()
    push_subscription_model.delete_subscription(_endpoint(data))
    return success(None, "Notifikasi dinonaktifkan.")
