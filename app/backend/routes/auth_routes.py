"""Autentikasi admin.

Pengguna publik tidak memerlukan akun; endpoint ini hanya untuk admin.
"""

import hashlib
import logging
import secrets

from flask import Blueprint, request
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from models import admin_model
from utils import validators as v
from utils.api import APIError, Conflict, success
from utils.mailer import send_mail
from utils.security import (
    admin_required,
    check_csrf,
    check_login_allowed,
    clear_failed_logins,
    client_ip,
    csrf_token,
    current_admin,
    log,
    login_admin,
    logout_admin,
    record_failed_login,
)

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Hash pembanding agar waktu respons login sama walau username tidak ada.
_DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(16))


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _session_payload(admin):
    return {"admin": admin, "csrf_token": csrf_token()}


@auth_bp.post("/login")
def login():
    data = v.json_body()
    login_name = v.string(data, "login", "Username atau email",
                          max_length=150) if data.get("login") else \
        v.string(data, "username", "Username atau email", max_length=150)
    password = data.get("password")
    if not isinstance(password, str) or not password:
        raise APIError("Password wajib diisi.")

    check_login_allowed(login_name)
    admin = admin_model.find_by_login(login_name)
    valid = check_password_hash(
        admin["password_hash"] if admin else _DUMMY_HASH, password
    )
    if not admin or not valid or admin["status"] != "ACTIVE":
        record_failed_login(login_name)
        raise APIError("Username/email atau password salah.", 401,
                       "invalid_credentials")

    clear_failed_logins(login_name)
    login_admin(admin)
    admin_model.touch_last_login(admin["id"])
    admin_model.log_activity(admin["id"], "LOGIN", "Admin login",
                             entity_type="admin", entity_id=admin["id"],
                             ip_address=client_ip())
    return success(_session_payload(admin_model.get_admin(admin["id"])),
                   "Login berhasil.")


@auth_bp.post("/logout")
def logout():
    admin = current_admin()
    if admin:
        admin_model.log_activity(admin["id"], "LOGOUT", "Admin logout",
                                 entity_type="admin", entity_id=admin["id"],
                                 ip_address=client_ip())
    logout_admin()
    return success(None, "Logout berhasil.")


@auth_bp.get("/me")
def me():
    admin = current_admin()
    if not admin:
        raise APIError("Belum login.", 401, "unauthorized")
    return success(_session_payload(admin))


@auth_bp.get("/status")
def status():
    """Info publik untuk halaman register (apakah sudah ada admin)."""
    return success({
        "has_admin": admin_model.count_admins() > 0,
        "logged_in": current_admin() is not None,
    })


@auth_bp.post("/register")
def register():
    """Admin pertama boleh mendaftar sendiri; selanjutnya hanya admin."""
    has_admin = admin_model.count_admins() > 0
    creator = current_admin()
    if has_admin and not creator:
        raise APIError(
            "Pendaftaran admin baru hanya dapat dilakukan oleh admin.",
            403, "forbidden",
        )
    if creator:
        check_csrf()

    data = v.json_body()
    username = v.username(data)
    email = v.email(data)
    full_name = v.string(data, "full_name", "Nama lengkap", max_length=150)
    password = v.password(data)
    if data.get("password_confirmation") not in (None, password):
        raise APIError("Konfirmasi password tidak sama.")
    if admin_model.username_or_email_taken(username, email):
        raise Conflict("Username atau email sudah digunakan.")

    admin_id = admin_model.create_admin(
        username, email, full_name, generate_password_hash(password)
    )
    admin_model.log_activity(
        creator["id"] if creator else admin_id, "CREATE",
        f"Admin baru: {username}", entity_type="admin", entity_id=admin_id,
        ip_address=client_ip(),
    )
    admin = admin_model.get_admin(admin_id)
    if not creator:
        login_admin(admin)
    return success(_session_payload(admin) if not creator else
                   {"admin": admin}, "Admin berhasil didaftarkan.", 201)


@auth_bp.post("/forgot-password")
def forgot_password():
    data = v.json_body()
    email = v.email(data)
    admin = admin_model.find_by_email(email)
    if admin and admin["status"] == "ACTIVE":
        token = secrets.token_urlsafe(32)
        admin_model.create_password_reset(
            admin["id"], _hash_token(token),
            Config.PASSWORD_RESET_TOKEN_MINUTES,
        )
        base = Config.PUBLIC_BASE_URL or request.host_url.rstrip("/")
        link = f"{base}/auth/reset-password?token={token}"
        sent = send_mail(
            admin["email"], "Reset password Akashic",
            "Gunakan tautan berikut untuk membuat password baru "
            f"(berlaku {Config.PASSWORD_RESET_TOKEN_MINUTES} menit):\n\n"
            f"{link}\n\nAbaikan email ini jika Anda tidak memintanya.",
        )
        if not sent:
            if Config.DEBUG:
                logger.warning("SMTP belum diatur. Tautan reset: %s", link)
            else:
                logger.warning("SMTP belum diatur; email reset tidak dikirim.")
        admin_model.log_activity(admin["id"], "PASSWORD_RESET_REQUEST",
                                 "Permintaan reset password",
                                 entity_type="admin", entity_id=admin["id"],
                                 ip_address=client_ip())
    # Respons selalu sama agar email terdaftar tidak bisa ditebak.
    return success(None, "Jika email terdaftar, tautan reset password "
                         "telah dikirim.")


@auth_bp.post("/reset-password")
def reset_password():
    data = v.json_body()
    token = v.string(data, "token", "Token", max_length=200)
    password = v.password(data)
    if data.get("password_confirmation") not in (None, password):
        raise APIError("Konfirmasi password tidak sama.")
    reset = admin_model.find_valid_reset(_hash_token(token))
    if not reset or not admin_model.consume_reset(
            reset["id"], reset["admin_id"], generate_password_hash(password)):
        raise APIError("Token reset tidak valid atau sudah kedaluwarsa.",
                       400, "invalid_token")
    admin_model.log_activity(reset["admin_id"], "PASSWORD_RESET",
                             "Password direset", entity_type="admin",
                             entity_id=reset["admin_id"],
                             ip_address=client_ip())
    return success(None, "Password berhasil diubah. Silakan login.")


@auth_bp.put("/profile")
@admin_required
def update_profile():
    admin = current_admin()
    data = v.json_body()
    username = v.username(data)
    email = v.email(data)
    full_name = v.string(data, "full_name", "Nama lengkap", max_length=150)
    if admin_model.username_or_email_taken(username, email, admin["id"]):
        raise Conflict("Username atau email sudah digunakan.")
    admin_model.update_profile(admin["id"], username, email, full_name)
    log("UPDATE", "Memperbarui profil", "admin", admin["id"])
    return success(admin_model.get_admin(admin["id"]), "Profil diperbarui.")


@auth_bp.put("/password")
@admin_required
def change_password():
    admin = admin_model.get_admin_with_password(current_admin()["id"])
    data = v.json_body()
    current = data.get("current_password")
    if not isinstance(current, str) or not check_password_hash(
            admin["password_hash"], current):
        raise APIError("Password saat ini salah.", 400, "invalid_password")
    new_password = v.password(data, "new_password", "Password baru")
    if data.get("password_confirmation") not in (None, new_password):
        raise APIError("Konfirmasi password tidak sama.")
    admin_model.update_password(admin["id"],
                                generate_password_hash(new_password))
    log("UPDATE", "Mengganti password", "admin", admin["id"])
    return success(None, "Password berhasil diganti.")
