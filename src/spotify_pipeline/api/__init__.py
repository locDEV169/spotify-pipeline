"""Flask application factory for the read-only dashboard API."""

from flask import Flask

from .routes import blueprint


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(blueprint)
    return app
