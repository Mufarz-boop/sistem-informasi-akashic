from flask import Blueprint, render_template

information_bp = Blueprint("information", __name__)

@information_bp.route("/information_admin")
def information_admin():
    return render_template("admin/information_admin.html")