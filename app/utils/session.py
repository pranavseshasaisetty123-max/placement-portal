from functools import wraps

from flask import redirect, session, url_for


def login_user(user_data):
    session.clear()
    session["user_id"] = user_data["user_id"]
    session["user_type"] = user_data["user_type"]
    session["display_name"] = user_data["display_name"]
    session["email"] = user_data["email"]


def logout_user():
    session.clear()


def login_required(user_type=None):
    """Restrict routes to authenticated users, optionally by role."""

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
