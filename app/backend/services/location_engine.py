"""Location Engine: validasi koordinat dari browser.

Koordinat hanya dipakai saat request berlangsung untuk mencari
wilayah. Koordinat TIDAK disimpan ke database maupun log.
"""

from config import Config
from services import region_engine


class LocationError(ValueError):
    """Data lokasi dari browser tidak valid."""


def _to_float(value, name):
    if isinstance(value, bool):
        raise LocationError(f"{name} harus berupa angka.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise LocationError(f"{name} harus berupa angka.") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise LocationError(f"{name} tidak valid.")
    return number


def validate(payload):
    if not isinstance(payload, dict):
        raise LocationError("Body request harus JSON.")
    if payload.get("latitude") is None or payload.get("longitude") is None:
        raise LocationError("latitude dan longitude wajib diisi.")

    latitude = _to_float(payload.get("latitude"), "latitude")
    longitude = _to_float(payload.get("longitude"), "longitude")
    if not -90 <= latitude <= 90:
        raise LocationError("latitude harus di antara -90 dan 90.")
    if not -180 <= longitude <= 180:
        raise LocationError("longitude harus di antara -180 dan 180.")

    accuracy = None
    if payload.get("accuracy") is not None:
        accuracy = _to_float(payload.get("accuracy"), "accuracy")
        if accuracy < 0:
            raise LocationError("accuracy tidak boleh negatif.")
        if accuracy > Config.LOCATION_MAX_ACCURACY_METERS:
            raise LocationError(
                "Akurasi lokasi terlalu rendah untuk menentukan wilayah."
            )
    return latitude, longitude, accuracy


def detect(payload):
    latitude, longitude, accuracy = validate(payload)
    match = region_engine.find_region(latitude, longitude, accuracy)
    result = {
        "location": {
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "accuracy": round(accuracy, 1) if accuracy is not None else None,
        },
        "region": None,
        "parent_region": None,
        "hierarchy": [],
        "confidence": None,
    }
    if match:
        result.update(match)
    return result
