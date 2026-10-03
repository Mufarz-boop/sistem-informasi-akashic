from flask import Blueprint, render_template

region_bp = Blueprint("region", __name__)

@region_bp.route("/regions")
def regions():
    return render_template("admin/regions.html")