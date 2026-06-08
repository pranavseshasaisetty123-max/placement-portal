import os

from flask import Flask

from app.routes import auth_bp, main_bp
from config import BASE_DIR, Config
from database.connection import init_db


def create_app():
    """
    Application factory pattern.

    Why use a factory instead of a global Flask(app) in run.py?
    - Keeps configuration, database init, and blueprint registration in one place
    - Makes the app testable (tests can call create_app() with test config)
    - Scales cleanly as new blueprints are added in future sprints

    template_folder and static_folder point to the project root because
    templates/ and static/ live outside the app/ package directory.
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )
    app.config.from_object(Config)

    # Register blueprints — each blueprint owns a group of related routes.
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    # Initialize the SQLite database inside an application context.
    with app.app_context():
        init_db()

    return app
