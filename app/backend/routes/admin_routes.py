from flask import Blueprint, render_template

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin")
def admin_dashboard():
    return render_template("admin/dashboard-admin.html")

@admin_bp.route("/events")
def admin_events():
    return render_template("admin/events.html")

@admin_bp.route("/information")
def admin_information():
    return render_template("admin/information.html")

@admin_bp.route("/news")
def admin_news():
    return render_template("admin/news.html")

@admin_bp.route("/profile")
def admin_profile():
    return render_template("admin/profile.html")

@admin_bp.route("/regions")
def admin_regions():
    return render_template("admin/regions.html")

@admin_bp.route("/setting")
def admin_setting():
    return render_template("admin/setting.html")