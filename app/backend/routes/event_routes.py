from flask import Blueprint, render_template

event_bp = Blueprint("event", __name__)

@event_bp.route("/events")
def events():
    return render_template("admin/events.html")