import os

from flask import Flask

from app.routes import admin_bp, applications_bp, auth_bp, jobs_bp, main_bp, profile_bp
from config import BASE_DIR, Config
from database.connection import init_db


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )
    app.config.from_object(Config)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)


    with app.app_context():
        init_db()

    return app
