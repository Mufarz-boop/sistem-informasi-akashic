"""Halaman HTML (frontend) yang disajikan oleh Flask."""

from flask import Blueprint, redirect, render_template, request, \
    send_from_directory, url_for

from config import FRONTEND_DIR
from utils.security import current_admin

page_bp = Blueprint("pages", __name__)

PUBLIC_PAGES = {
    "/": ("landing/index.html", "home"),
    "/about": ("landing/about.html", "about"),
    "/information": ("landing/information.html", "information"),
    "/contact": ("legal/contact.html", "contact"),
    "/disclaimer": ("legal/disclaimer.html", "disclaimer"),
    "/system-description": ("legal/system-description.html", "system"),
}
AUTH_PAGES = {
    "/auth/login": "auth/login.html",
    "/auth/register": "auth/register.html",
    "/auth/forgot-password": "auth/forgot-password.html",
    "/auth/reset-password": "auth/reset-password.html",
}
ADMIN_PAGES = {
    "/admin/dashboard": ("admin/dashboard-admin.html", "dashboard"),
    "/admin/information": ("admin/information.html", "information"),
    "/admin/events": ("admin/events.html", "events"),
    "/admin/news": ("admin/news.html", "news"),
    "/admin/regions": ("admin/regions.html", "regions"),
    "/admin/profile": ("admin/profile.html", "profile"),
    "/admin/settings": ("admin/setting.html", "settings"),
}


def _public_view(template, active):
    def view():
        return render_template(template, active_page=active)
    return view


def _auth_view(template):
    def view():
        return render_template(template)
    return view


def _admin_view(template, active):
    def view():
        if not current_admin():
            return redirect(url_for("pages.auth_login", next=request.path))
        return render_template(template, active_page=active)
    return view


for path, (template, active) in PUBLIC_PAGES.items():
    page_bp.add_url_rule(path, f"public_{active}",
                         _public_view(template, active))
for path, template in AUTH_PAGES.items():
    page_bp.add_url_rule(path, path.strip("/").replace("/", "_")
                         .replace("-", "_"), _auth_view(template))
for path, (template, active) in ADMIN_PAGES.items():
    page_bp.add_url_rule(path, f"admin_{active}",
                         _admin_view(template, active))


@page_bp.get("/admin")
def admin_index():
    return redirect(url_for("pages.admin_dashboard"))


@page_bp.get("/service_worker.js")
def service_worker():
    """Disajikan dari root agar scope service worker mencakup '/'."""
    response = send_from_directory(FRONTEND_DIR / "assets",
                                   "service_worker.js",
                                   mimetype="application/javascript",
                                   max_age=0)
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response
