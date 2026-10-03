from flask import Blueprint, render_template

news_bp = Blueprint("news", __name__)

@news_bp.route("/news")
def news():
    return render_template("admin/news.html")