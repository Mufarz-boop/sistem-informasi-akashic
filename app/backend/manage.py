"""Perintah administrasi Akashic.

Contoh (dari folder app/backend):
    python manage.py create-admin
    python manage.py generate-vapid
    python manage.py collect-news
"""

import argparse
import base64
import getpass
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from werkzeug.security import generate_password_hash

from models import admin_model
from services import news_collector
from utils import validators as v
from utils.api import APIError


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate_vapid():
    key = ec.generate_private_key(ec.SECP256R1())
    private_raw = key.private_numbers().private_value.to_bytes(32, "big")
    public_raw = key.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    print("Salin ke app/.env (jangan di-commit):")
    print(f"VAPID_PUBLIC_KEY={_b64url(public_raw)}")
    print(f"VAPID_PRIVATE_KEY={_b64url(private_raw)}")


def create_admin():
    data = {
        "username": input("Username: ").strip(),
        "email": input("Email: ").strip(),
        "full_name": input("Nama lengkap: ").strip(),
        "password": getpass.getpass("Password: "),
    }
    if getpass.getpass("Ulangi password: ") != data["password"]:
        sys.exit("Password tidak sama.")
    try:
        username = v.username(data)
        email = v.email(data)
        full_name = v.string(data, "full_name", "Nama lengkap",
                             max_length=150)
        password = v.password(data)
    except APIError as exc:
        sys.exit(exc.message)
    if admin_model.username_or_email_taken(username, email):
        sys.exit("Username atau email sudah digunakan.")
    admin_id = admin_model.create_admin(username, email, full_name,
                                        generate_password_hash(password))
    admin_model.log_activity(admin_id, "CREATE", f"Admin dibuat via CLI: "
                             f"{username}", entity_type="admin",
                             entity_id=admin_id)
    print(f"Admin '{username}' dibuat (id {admin_id}).")


def collect_news():
    print(news_collector.collect_all())


COMMANDS = {
    "create-admin": create_admin,
    "generate-vapid": generate_vapid,
    "collect-news": collect_news,
}


def main():
    parser = argparse.ArgumentParser(description="Perintah Akashic")
    parser.add_argument("command", choices=sorted(COMMANDS))
    COMMANDS[parser.parse_args().command]()


if __name__ == "__main__":
    main()
