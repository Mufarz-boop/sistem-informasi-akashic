"""Validasi input request (JSON body & query string)."""

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from flask import request

from utils.api import APIError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise APIError("Body request harus berupa JSON object.")
    return data


def string(data, name, label, required=True, max_length=255,
           min_length=0):
    value = data.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise APIError(f"{label} wajib diisi.")
        return None
    if not isinstance(value, str):
        raise APIError(f"{label} harus berupa teks.")
    value = value.strip()
    if len(value) < min_length:
        raise APIError(f"{label} minimal {min_length} karakter.")
    if max_length and len(value) > max_length:
        raise APIError(f"{label} maksimal {max_length} karakter.")
    return value


def integer(value, label, required=True, minimum=1):
    if value is None or value == "":
        if required:
            raise APIError(f"{label} wajib diisi.")
        return None
    if isinstance(value, bool):
        raise APIError(f"{label} harus berupa angka.")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise APIError(f"{label} harus berupa angka.") from exc
    if minimum is not None and number < minimum:
        raise APIError(f"{label} minimal {minimum}.")
    return number


def number(value, label, minimum=None, maximum=None):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise APIError(f"{label} harus berupa angka.")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise APIError(f"{label} harus berupa angka.") from exc
    if (minimum is not None and result < minimum) or \
            (maximum is not None and result > maximum):
        raise APIError(f"{label} di luar jangkauan.")
    return result


def choice(value, label, choices, default=None):
    if value is None or value == "":
        if default is not None:
            return default
        raise APIError(f"{label} wajib diisi.")
    normalized = str(value).strip().upper()
    if normalized not in choices:
        raise APIError(f"{label} harus salah satu dari: {', '.join(choices)}.")
    return normalized


def email(data, name="email", required=True):
    value = string(data, name, "Email", required=required, max_length=150)
    if value is None:
        return None
    if not EMAIL_RE.match(value):
        raise APIError("Format email tidak valid.")
    return value.lower()


def username(data):
    value = string(data, "username", "Username", max_length=50)
    if not USERNAME_RE.match(value):
        raise APIError(
            "Username 3-50 karakter: huruf, angka, titik, garis bawah, "
            "atau tanda hubung."
        )
    return value


def password(data, name="password", label="Password"):
    value = data.get(name)
    if not isinstance(value, str) or not value:
        raise APIError(f"{label} wajib diisi.")
    if len(value) < 8 or len(value) > 128:
        raise APIError(f"{label} harus 8-128 karakter.")
    if not (re.search(r"[A-Za-z]", value) and re.search(r"\d", value)):
        raise APIError(f"{label} harus mengandung huruf dan angka.")
    return value


def url(data, name, label, required=False, max_length=1000):
    value = string(data, name, label, required=required,
                   max_length=max_length)
    if value is None:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise APIError(f"{label} harus URL http(s) yang valid.")
    return value


def datetime_value(value, label, required=False):
    """ISO 8601 -> datetime naive UTC (format penyimpanan database).

    Nilai tanpa zona waktu dianggap sudah UTC.
    """
    if value is None or value == "":
        if required:
            raise APIError(f"{label} wajib diisi.")
        return None
    if not isinstance(value, str):
        raise APIError(f"{label} harus berupa tanggal ISO 8601.")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise APIError(f"{label} harus berupa tanggal ISO 8601.") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def date_range(args):
    """Query ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD (inklusif)."""
    result = {}
    for key in ("date_from", "date_to"):
        raw = args.get(key)
        if not raw:
            continue
        try:
            value = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError as exc:
            raise APIError(f"{key} harus berformat YYYY-MM-DD.") from exc
        result[key] = value + timedelta(days=1) if key == "date_to" else value
    return result


def pagination(args, default_per_page=12, max_per_page=50):
    page = integer(args.get("page") or 1, "page")
    per_page = integer(args.get("per_page") or default_per_page, "per_page")
    return min(page, 1000), min(per_page, max_per_page)


def keywords(value):
    if value is None:
        return []
    if isinstance(value, str):
        value = value.split(",")
    if not isinstance(value, list):
        raise APIError("Keywords harus berupa daftar teks.")
    cleaned = []
    for item in value:
        if not isinstance(item, str):
            raise APIError("Keywords harus berupa daftar teks.")
        item = " ".join(item.split())
        if item and len(item) <= 150 and item.lower() not in \
                [k.lower() for k in cleaned]:
            cleaned.append(item)
    return cleaned[:30]
