from functools import wraps

from flask import redirect, session, url_for


def login_user(user_data):
    """
    Persist authenticated user data in a Flask session.

    Flask sessions:
    - Data is stored server-side (default: signed cookie referencing server storage,
      or in this dev setup, a signed cookie containing the session payload).
    - The browser only receives an encrypted/signed session cookie.
    - SECRET_KEY in config.py is used to sign the cookie.
    - On each request, Flask decrypts the cookie and exposes session as a dict.

    We store only what the UI and authorization layer need:
    user_id, user_type, display_name
    """
    session.clear()
    session["user_id"] = user_data["user_id"]
    session["user_type"] = user_data["user_type"]
    session["display_name"] = user_data["display_name"]


def logout_user():
    """Remove all session data — effectively logs the user out."""
    session.clear()


def login_required(user_type=None):
    """
    Route decorator that enforces authentication.

    Usage:
        @login_required(user_type="student")  — only logged-in students
        @login_required(user_type="recruiter") — only logged-in recruiters

    If the user is not logged in, redirect to the appropriate login page.
    If the user is logged in but has the wrong role, redirect to home.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if "user_id" not in session:
                if user_type == "student":
                    return redirect(url_for("auth.student_login"))
                if user_type == "recruiter":
                    return redirect(url_for("auth.recruiter_login"))
                return redirect(url_for("main.home"))

            if user_type and session.get("user_type") != user_type:
                return redirect(url_for("main.home"))

            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator
