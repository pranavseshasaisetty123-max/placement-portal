import sqlite3

from database.connection import get_db
from werkzeug.security import check_password_hash, generate_password_hash


class AuthError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def _email_exists(email):
    """Return True if email is already registered as student or recruiter."""
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
    if _email_exists(email):
        raise AuthError("Email is already registered.")

    hashed_password = generate_password_hash(password)

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO students (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed_password),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise AuthError("Email is already registered.") from None


def register_recruiter(company_name, email, password):
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
        "email": user["email"],
    }


def authenticate_recruiter(email, password):
    with get_db() as conn:
        user = conn.execute(
            "SELECT recruiter_id, company_name, email, password, is_active FROM recruiters WHERE email = ?",
            (email,),
        ).fetchone()

    if user is None or not check_password_hash(user["password"], password):
        raise AuthError("Invalid email or password.")

    if not user["is_active"]:
        raise AuthError("Your account has been deactivated. Please contact the administrator.")

    return {
        "user_id": user["recruiter_id"],
        "user_type": "recruiter",
        "display_name": user["company_name"],
        "email": user["email"],
    }
