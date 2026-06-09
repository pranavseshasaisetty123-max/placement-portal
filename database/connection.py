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
        # Check if skills column exists in the jobs table
        cursor = conn.execute("PRAGMA table_info(jobs)")
        columns = [row[1] for row in cursor.fetchall()]
        if columns and "skills" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN skills TEXT NOT NULL DEFAULT ''")

        # Check if resume_path column exists in the students table
        cursor = conn.execute("PRAGMA table_info(students)")
        columns = [row[1] for row in cursor.fetchall()]
        if columns and "resume_path" not in columns:
            conn.execute("ALTER TABLE students ADD COLUMN resume_path TEXT")

        # Check if is_active column exists in the recruiters table
        cursor = conn.execute("PRAGMA table_info(recruiters)")
        columns = [row[1] for row in cursor.fetchall()]
        if columns and "is_active" not in columns:
            conn.execute("ALTER TABLE recruiters ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")

        # Seed default admin if empty
        cursor = conn.execute("SELECT count(*) FROM admins")
        if cursor.fetchone()[0] == 0:
            from werkzeug.security import generate_password_hash
            hashed_pw = generate_password_hash("admin123")
            conn.execute(
                "INSERT INTO admins (username, email, password) VALUES ('admin', 'admin@placement.com', ?)",
                (hashed_pw,)
            )
        conn.commit()
