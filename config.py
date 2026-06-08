import os

# Project root directory — used to locate templates, static files, and the database.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # SECRET_KEY signs Flask session cookies so they cannot be tampered with.
    # In production, set this via an environment variable.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    DATABASE_PATH = os.path.join(BASE_DIR, "database", "placement_portal.db")
    SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")
