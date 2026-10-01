import os

from flask import Flask, jsonify, render_template

FULL_NAME = "Thomas Soubirou-Pouey"


def create_app(version=None):
    app = Flask(__name__)
    app.config["APP_VERSION"] = version if version is not None else os.getenv("APP_VERSION", "local")

    @app.get("/")
    def index():
        return render_template("index.html", full_name=FULL_NAME, version=app.config["APP_VERSION"])

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.get("/who")
    def who():
        return app.response_class(FULL_NAME, mimetype="text/plain")

    @app.get("/version")
    def version_info():
        return jsonify(version=app.config["APP_VERSION"])

    return app


app = create_app()
