import sqlite3

from config import Config


def get_db():
    """
    Open a SQLite connection for a single request/operation.

    Database interaction pattern:
    1. Route receives HTTP request
    2. Service calls get_db()
    3. Service runs parameterized SQL (prevents SQL injection)
    4. Connection commits changes and closes automatically via context manager

    row_factory = sqlite3.Row lets us access columns by name (row["email"]).
    """
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Bootstrap the database on application startup.

    Reads schema.sql and creates tables if they do not already exist.
    Safe to run on every app start because of IF NOT EXISTS.
    """
    with open(Config.SCHEMA_PATH, encoding="utf-8") as schema_file:
        schema = schema_file.read()

    with get_db() as conn:
        conn.executescript(schema)
        conn.commit()
