from flask import Flask, render_template
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "frontend", "pages"),
    static_folder=os.path.join(BASE_DIR, "frontend", "assets"),
    static_url_path="/static"
)


@app.route("/")
def index():
    return render_template("landing/index.html")


@app.route("/about")
def about():
    return render_template("landing/about.html")


@app.route("/information")
def information():
    return render_template("landing/information.html")


if __name__ == "__main__":
    app.run(debug=True)