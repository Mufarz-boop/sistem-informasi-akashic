"""Notification Engine: Web Push berbasis wilayah.

Notifikasi dicatat di tabel notifications, lalu dikirim ke
subscription yang wilayahnya berada di dalam wilayah konten
(contoh: informasi untuk Aceh juga dikirim ke subscriber di Langsa).
Pengiriman berjalan di thread terpisah agar request admin tidak
menunggu push service.
"""

import json
import logging
import threading

from pywebpush import WebPushException, webpush

from config import Config
from models import notification_model, push_subscription_model
from services import region_engine

logger = logging.getLogger(__name__)

GONE_STATUS_CODES = (404, 410)


def notify_information(info):
    _notify(
        column="information_id",
        entity_id=info["id"],
        notification_type="INFORMATION",
        region_id=info["region_id"],
        title=f"Informasi baru di {info['region_name']}",
        message=info["title"],
        url=f"/information?type=information&id={info['id']}",
    )


def notify_event(event):
    _notify(
        column="event_id",
        entity_id=event["id"],
        notification_type="EVENT",
        region_id=event["region_id"],
        title=f"Event baru di {event['region_name']}",
        message=event["title"],
        url=f"/information?type=event&id={event['id']}",
    )


def notify_news(news):
    where = news["region_name"] or "Akashic"
    _notify(
        column="news_id",
        entity_id=news["id"],
        notification_type="NEWS",
        region_id=news["region_id"],
        title=f"Berita baru di {where}",
        message=news["title"],
        url=f"/information?type=news&id={news['id']}",
    )


def _notify(column, entity_id, notification_type, region_id, title,
            message, url):
    try:
        if notification_model.already_notified(column, entity_id):
            return
        notification_id = notification_model.create_notification({
            column: entity_id,
            "type": notification_type,
            "region_id": region_id,
            "title": title[:255],
            "message": message,
            "url": url,
        })
    except Exception:  # noqa: BLE001 - notifikasi tidak boleh gagalkan CRUD
        logger.exception("Gagal membuat notifikasi")
        return

    if not Config.push_enabled():
        logger.info("Web Push nonaktif (VAPID belum diatur).")
        return
    region_ids = region_engine.descendant_ids(region_id) if region_id else []
    payload = {
        "title": title,
        "body": message,
        "url": url,
        "tag": f"{notification_type.lower()}-{entity_id}",
    }
    thread = threading.Thread(
        target=_deliver, args=(notification_id, region_ids, payload),
        daemon=True,
    )
    thread.start()


def _deliver(notification_id, region_ids, payload):
    sent = failed = 0
    try:
        targets = push_subscription_model.list_targets(region_ids)
        for target in targets:
            if send_push(target, payload):
                sent += 1
            else:
                failed += 1
        notification_model.update_delivery(notification_id, sent, failed)
    except Exception:  # noqa: BLE001 - thread latar belakang
        logger.exception("Pengiriman notifikasi %s gagal", notification_id)


def send_push(subscription, payload):
    """Mengirim satu push. Subscription kedaluwarsa dinonaktifkan."""
    try:
        webpush(
            subscription_info={
                "endpoint": subscription["endpoint"],
                "keys": {
                    "p256dh": subscription["p256dh_key"],
                    "auth": subscription["auth_key"],
                },
            },
            data=json.dumps(payload),
            vapid_private_key=Config.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{Config.VAPID_CLAIMS_EMAIL}"},
            timeout=10,
        )
        return True
    except WebPushException as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in GONE_STATUS_CODES:
            push_subscription_model.deactivate(subscription["id"])
        logger.warning("Push gagal (status %s): %s", status, exc)
        return False
    except Exception as exc:  # noqa: BLE001 - jaringan, dsb.
        logger.warning("Push gagal: %s", exc)
        return False
