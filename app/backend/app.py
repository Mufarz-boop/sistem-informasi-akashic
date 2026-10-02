import re
import secrets
import smtplib
import ssl
import time
from collections import defaultdict, deque
from email.message import EmailMessage
from pathlib import Path
from threading import Lock

from flask import Flask, abort, redirect, render_template, request, session, url_for

from config import Config

# =========================================================
# BASE DIRECTORY
# =========================================================
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
TEMPLATES_DIR = FRONTEND_DIR / "pages"
ASSETS_DIR = FRONTEND_DIR / "assets"

# =========================================================
# FLASK APPLICATION
# =========================================================
app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(ASSETS_DIR),
    static_url_path="/static",
)
app.config.from_object(Config)

# =========================================================
# CONTACT — KONFIGURASI & HELPER
# =========================================================
CONTACT_CATEGORIES = {
    "general": "General Question",
    "feedback": "Feedback",
    "technical": "Technical Issue",
    "content": "Content / Information",
    "privacy": "Privacy",
    "other": "Other",
}

CONTACT_LIMITS = {"name": 100, "email": 254, "subject": 150, "message": 5000}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

# Pembatasan sederhana (in-memory, per proses): 5 pesan / 10 menit / IP.
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 600
_rate_hits = defaultdict(deque)
_rate_lock = Lock()


def _csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _csrf_valid(submitted):
    expected = session.get("csrf_token", "")
    return bool(expected) and bool(submitted) and secrets.compare_digest(expected, submitted)


def _rate_limited(key):
    now = time.time()
    with _rate_lock:
        hits = _rate_hits[key]
        while hits and now - hits[0] > RATE_LIMIT_WINDOW:
            hits.popleft()
        if len(hits) >= RATE_LIMIT_MAX:
            return True
        hits.append(now)
        return False


def _single_line(value, limit):
    """Bersihkan karakter kontrol (mencegah header injection) dan batasi panjang."""
    return CONTROL_CHARS.sub(" ", value or "").strip()[:limit]


def _read_contact_form():
    form = {
        "name": _single_line(request.form.get("name"), CONTACT_LIMITS["name"]),
        "email": _single_line(request.form.get("email"), CONTACT_LIMITS["email"]),
        "category": _single_line(request.form.get("category"), 30),
        "subject": _single_line(request.form.get("subject"), CONTACT_LIMITS["subject"]),
        "message": (request.form.get("message") or "").replace("\r\n", "\n").strip()[: CONTACT_LIMITS["message"]],
    }
    errors = []
    if not form["name"]:
        errors.append("Isi nama Anda.")
    if not form["email"]:
        errors.append("Isi alamat email Anda.")
    elif not EMAIL_PATTERN.match(form["email"]):
        errors.append("Gunakan format email yang valid.")
    if form["category"] not in CONTACT_CATEGORIES:
        errors.append("Pilih salah satu kategori.")
    if not form["message"]:
        errors.append("Tulis pesan Anda.")
    return form, errors


def _send_contact_email(form):
    """Kirim pesan ke CONTACT_RECIPIENT lewat SMTP. Melempar exception jika gagal."""
    cfg = app.config
    required = ("MAIL_SERVER", "MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_SENDER", "CONTACT_RECIPIENT")
    missing = [key for key in required if not cfg.get(key)]
    if missing:
        raise RuntimeError("Konfigurasi email belum lengkap: " + ", ".join(missing))

    category_label = CONTACT_CATEGORIES[form["category"]]
    subject = form["subject"] or "Tanpa subjek"

    msg = EmailMessage()
    msg["From"] = cfg["MAIL_SENDER"]
    msg["To"] = cfg["CONTACT_RECIPIENT"]
    msg["Reply-To"] = form["email"]
    msg["Subject"] = f"[Akashic Contact · {category_label}] {subject}"
    msg.set_content(
        "Pesan baru dari form Contact Akashic\n"
        "------------------------------------\n"
        f"Nama     : {form['name']}\n"
        f"Email    : {form['email']}\n"
        f"Kategori : {category_label}\n"
        f"Subjek   : {subject}\n"
        "------------------------------------\n\n"
        f"{form['message']}\n"
    )

    context = ssl.create_default_context()
    port = int(cfg.get("MAIL_PORT", 587))
    if cfg.get("MAIL_USE_SSL"):
        with smtplib.SMTP_SSL(cfg["MAIL_SERVER"], port, timeout=15, context=context) as smtp:
            smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(cfg["MAIL_SERVER"], port, timeout=15) as smtp:
            smtp.starttls(context=context)
            smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            smtp.send_message(msg)


def _render_contact(status=None, errors=None, form=None):
    return render_template(
        "landing/contact.html",
        status=status,
        errors=errors or [],
        form=form or {},
        csrf_token=_csrf_token(),
    )


# =========================================================
# LANDING PAGE
# =========================================================
@app.route("/")
def index():
    return render_template("landing/index.html")


@app.route("/about")
def about():
    return render_template("landing/about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "GET":
        # Status "sent" dibawa lewat session setelah redirect (Post/Redirect/Get),
        # sehingga refresh halaman tidak mengirim ulang pesan.
        return _render_contact(status=session.pop("contact_status", None))

    # --- POST ---
    if not _csrf_valid(request.form.get("csrf_token", "")):
        return _render_contact(status="csrf", form=request.form.to_dict()), 400

    # Honeypot: bot mengisi field tersembunyi. Pura-pura sukses, jangan kirim apa pun.
    if request.form.get("website"):
        session["contact_status"] = "sent"
        return redirect(url_for("contact") + "#contact-form")

    client_ip = request.remote_addr or "unknown"
    if _rate_limited(client_ip):
        return _render_contact(status="rate", form=request.form.to_dict()), 429

    form, errors = _read_contact_form()
    if errors:
        return _render_contact(status="invalid", errors=errors, form=form), 400

    try:
        _send_contact_email(form)
    except Exception:
        app.logger.exception("Gagal mengirim email contact")
        return _render_contact(status="failed", form=form), 502

    session["contact_status"] = "sent"
    return redirect(url_for("contact") + "#contact-form")


@app.route("/information")
def information():
    return render_template("landing/information.html")


# =========================================================
# LEGAL PAGES
# =========================================================
@app.route("/disclaimer")
def disclaimer():
    return render_template("legal/disclaimer.html")


@app.route("/privacy")
def privacy():
    return render_template("legal/privacy.html")


@app.route("/terms")
def terms():
    return render_template("legal/terms.html")


# =========================================================
# ERROR HANDLERS
# =========================================================
@app.errorhandler(404)
def page_not_found(error):
    return render_template("error/404.html"), 404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template("error/500.html"), 500


# =========================
# ERROR TESTING
# =========================
@app.route("/test-500")
def test_500():
    abort(500)


# =========================================================
# RUN APPLICATION
# =========================================================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=app.config["FLASK_DEBUG"],
    )