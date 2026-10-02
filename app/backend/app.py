from pathlib import Path
from flask import Flask, abort, render_template
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
# LANDING PAGE
# =========================================================
@app.route("/")
def index():
    return render_template("landing/index.html")

@app.route("/about")
def about():
    return render_template("landing/about.html")

@app.route("/contact")
def contact():
    return render_template("landing/contact.html")

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