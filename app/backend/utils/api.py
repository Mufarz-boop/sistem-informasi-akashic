"""Format respons standar API Akashic."""

from datetime import date, datetime, timezone
from decimal import Decimal

from flask import jsonify
from flask.json.provider import DefaultJSONProvider


class APIError(Exception):
    """Exception yang langsung diubah menjadi respons error JSON."""

    def __init__(self, message, status=400, error="bad_request"):
        super().__init__(message)
        self.message = message
        self.status = status
        self.error = error


class NotFound(APIError):
    def __init__(self, message="Data tidak ditemukan."):
        super().__init__(message, 404, "not_found")


class Conflict(APIError):
    def __init__(self, message):
        super().__init__(message, 409, "conflict")


def success(data=None, message="OK", status=200):
    return jsonify({"success": True, "data": data, "message": message}), status


def error(message, status=400, error_code="bad_request"):
    return jsonify({
        "success": False,
        "data": None,
        "message": message,
        "error": error_code,
    }), status


class AkashicJSONProvider(DefaultJSONProvider):
    """Datetime dari MySQL disimpan dalam UTC -> ISO 8601 dengan 'Z'."""

    @staticmethod
    def default(o):
        if isinstance(o, datetime):
            if o.tzinfo is not None:
                o = o.astimezone(timezone.utc).replace(tzinfo=None)
            return o.isoformat(timespec="seconds") + "Z"
        if isinstance(o, date):
            return o.isoformat()
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, (bytes, bytearray)):
            return None
        return DefaultJSONProvider.default(o)
