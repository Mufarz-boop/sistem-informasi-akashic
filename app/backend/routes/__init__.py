"""Registrasi seluruh blueprint API."""

from routes.admin_routes import admin_bp
from routes.auth_routes import auth_bp
from routes.event_routes import event_bp
from routes.information_routes import information_bp
from routes.location_routes import location_bp
from routes.news_routes import news_bp
from routes.notification_routes import notification_bp
from routes.page_routes import page_bp
from routes.region_routes import region_bp

BLUEPRINTS = (
    page_bp,
    auth_bp,
    admin_bp,
    information_bp,
    event_bp,
    news_bp,
    region_bp,
    location_bp,
    notification_bp,
)


def register_blueprints(app):
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
