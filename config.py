import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DATABASE_PATH = os.path.join(BASE_DIR, "database", "placement_portal.db")
    SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    # Limit max payload size to 2MB (2 * 1024 * 1024 bytes)
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
