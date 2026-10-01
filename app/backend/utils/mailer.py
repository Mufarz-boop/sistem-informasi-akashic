"""Pengiriman email sederhana via SMTP (opsional)."""

import logging
import smtplib
from email.message import EmailMessage

from config import Config

logger = logging.getLogger(__name__)


def send_mail(to_address, subject, body):
    """Mengembalikan True jika email terkirim."""
    if not Config.mail_enabled():
        return False
    message = EmailMessage()
    message["From"] = Config.MAIL_SENDER
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT,
                          timeout=15) as smtp:
            if Config.MAIL_USE_TLS:
                smtp.starttls()
            if Config.MAIL_USERNAME:
                smtp.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            smtp.send_message(message)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Gagal mengirim email: %s", exc)
        return False
