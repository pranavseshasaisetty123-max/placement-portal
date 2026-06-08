import sqlite3

from database.connection import get_db
from werkzeug.security import check_password_hash, generate_password_hash


class AuthError(Exception):
    """Raised when registration or login business rules fail."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)


def _email_exists(email):
    """
    Check both tables before registration.

    Duplicate email prevention happens at two levels:
    1. Application check (this function) — user-friendly error message
    2. Database UNIQUE constraint — safety net if two requests race
    """
    with get_db() as conn:
        student = conn.execute(
            "SELECT 1 FROM students WHERE email = ?",
            (email,),
        ).fetchone()
        recruiter = conn.execute(
            "SELECT 1 FROM recruiters WHERE email = ?",
            (email,),
        ).fetchone()

    return student is not None or recruiter is not None


def register_student(name, email, password):
    """
    Register a new student.

    Password hashing:
    - Never store plain-text passwords in the database.
    - generate_password_hash() uses a one-way hash + random salt.
    - The original password cannot be recovered from the hash.
    """
    if _email_exists(email):
        raise AuthError("Email is already registered.")

    # Hash password before it touches the database layer.
    hashed_password = generate_password_hash(password)

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO students (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed_password),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # UNIQUE constraint on email rejected a duplicate insert.
        raise AuthError("Email is already registered.") from None


def register_recruiter(company_name, email, password):
    """Register a new recruiter with the same hashing and duplicate rules."""
    if _email_exists(email):
        raise AuthError("Email is already registered.")

    hashed_password = generate_password_hash(password)

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO recruiters (company_name, email, password) VALUES (?, ?, ?)",
                (company_name, email, hashed_password),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise AuthError("Email is already registered.") from None


def authenticate_student(email, password):
    """
    Verify student login credentials.

    Login flow:
    1. Look up user by email in the students table
    2. Compare submitted password against stored hash via check_password_hash()
    3. Return a session payload if valid; raise AuthError if not

    check_password_hash() hashes the submitted password with the same salt
    embedded in the stored hash, then compares the results.
    """
    with get_db() as conn:
        user = conn.execute(
            "SELECT student_id, name, email, password FROM students WHERE email = ?",
            (email,),
        ).fetchone()

    if user is None or not check_password_hash(user["password"], password):
        raise AuthError("Invalid email or password.")

    return {
        "user_id": user["student_id"],
        "user_type": "student",
        "display_name": user["name"],
    }


def authenticate_recruiter(email, password):
    """Verify recruiter login credentials using the same hash comparison."""
    with get_db() as conn:
        user = conn.execute(
            "SELECT recruiter_id, company_name, email, password FROM recruiters WHERE email = ?",
            (email,),
        ).fetchone()

    if user is None or not check_password_hash(user["password"], password):
        raise AuthError("Invalid email or password.")

    return {
        "user_id": user["recruiter_id"],
        "user_type": "recruiter",
        "display_name": user["company_name"],
    }
