from flask import Flask, render_template

app = Flask(
    __name__,
    template_folder="../frontend/pages",
    static_folder="../frontend/static",
    static_url_path="/static"
)


@app.route("/")
def index():
    return render_template(
        "landing/index.html",
        active_page="home"
    )

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )