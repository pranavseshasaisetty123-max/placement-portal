import sqlite3

from config import Config


def get_db():
    """Return a SQLite connection with row-based dict access."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables from schema.sql if they do not exist."""
    with open(Config.SCHEMA_PATH, encoding="utf-8") as schema_file:
        schema = schema_file.read()

    with get_db() as conn:
        conn.executescript(schema)
        conn.commit()
