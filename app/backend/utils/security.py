"""Autentikasi admin: session, CSRF, dan pembatasan percobaan login."""

import hmac
import secrets
import threading
import time
from functools import wraps

from flask import g, request, session

from models import admin_model
from utils.api import APIError

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")
CSRF_HEADER = "X-CSRF-Token"
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60

_failed_logins = {}
_failed_lock = threading.Lock()


def client_ip():
    return (request.remote_addr or "")[:45] or None


def login_admin(admin):
    session.clear()
    session.permanent = True
    session["admin_id"] = admin["id"]
    session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def logout_admin():
    session.clear()


def csrf_token():
    if "admin_id" in session and "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session.get("csrf_token")


def current_admin():
    """Admin yang sedang login (aktif), atau None."""
    if "admin" in g:
        return g.admin
    admin = None
    admin_id = session.get("admin_id")
    if admin_id:
        admin = admin_model.get_admin(admin_id)
        if not admin or admin["status"] != "ACTIVE":
            session.clear()
            admin = None
    g.admin = admin
    return admin


def check_csrf():
    if request.method in SAFE_METHODS:
        return
    expected = session.get("csrf_token")
    provided = request.headers.get(CSRF_HEADER, "")
    if not expected or not hmac.compare_digest(expected, provided):
        raise APIError("Token CSRF tidak valid. Muat ulang halaman.",
                       403, "csrf_failed")


def admin_required(view):
    """Decorator endpoint khusus admin (session + CSRF)."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_admin():
            raise APIError("Silakan login sebagai admin.", 401,
                           "unauthorized")
        check_csrf()
        return view(*args, **kwargs)

    return wrapper


def is_admin_scope():
    """True jika request meminta data admin (?scope=admin) dan sah."""
    if request.args.get("scope") != "admin":
        return False
    if not current_admin():
        raise APIError("Silakan login sebagai admin.", 401, "unauthorized")
    return True


def log(action, description, entity_type=None, entity_id=None):
    admin = current_admin()
    admin_model.log_activity(
        admin["id"] if admin else None, action, description,
        entity_type=entity_type, entity_id=entity_id, ip_address=client_ip(),
    )


# ---------------------------------------------------------- rate limiting

def _key(login):
    return f"{client_ip()}|{(login or '').lower()}"


def check_login_allowed(login):
    now = time.time()
    with _failed_lock:
        attempts = [t for t in _failed_logins.get(_key(login), [])
                    if now - t < LOCKOUT_SECONDS]
        _failed_logins[_key(login)] = attempts
    if len(attempts) >= MAX_FAILED_LOGINS:
        raise APIError(
            "Terlalu banyak percobaan login. Coba lagi dalam 15 menit.",
            429, "too_many_requests",
        )


def record_failed_login(login):
    with _failed_lock:
        _failed_logins.setdefault(_key(login), []).append(time.time())


def clear_failed_logins(login):
    with _failed_lock:
        _failed_logins.pop(_key(login), None)
