from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.services import auth_service
from app.utils.session import login_required, login_user, logout_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/student-login", methods=["GET", "POST"])
def student_login():
    if session.get("user_type") == "student":
        return redirect(url_for("auth.student_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("student_login.html")

        try:
            user_data = auth_service.authenticate_student(email, password)
            login_user(user_data)
            flash("Login successful.", "success")
            return redirect(url_for("auth.student_dashboard"))
        except auth_service.AuthError as error:
            flash(error.message, "danger")

    return render_template("student_login.html")


@auth_bp.route("/recruiter-login", methods=["GET", "POST"])
def recruiter_login():
    if session.get("user_type") == "recruiter":
        return redirect(url_for("auth.recruiter_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("recruiter_login.html")

        try:
            user_data = auth_service.authenticate_recruiter(email, password)
            login_user(user_data)
            flash("Login successful.", "success")
            return redirect(url_for("auth.recruiter_dashboard"))
        except auth_service.AuthError as error:
            flash(error.message, "danger")

    return render_template("recruiter_login.html")


@auth_bp.route("/register-student", methods=["GET", "POST"])
def register_student():
    if session.get("user_type") == "student":
        return redirect(url_for("auth.student_dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register_student.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register_student.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("register_student.html")

        try:
            auth_service.register_student(name, email, password)
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.student_login"))
        except auth_service.AuthError as error:
            flash(error.message, "danger")

    return render_template("register_student.html")


@auth_bp.route("/register-recruiter", methods=["GET", "POST"])
def register_recruiter():
    if session.get("user_type") == "recruiter":
        return redirect(url_for("auth.recruiter_dashboard"))

    if request.method == "POST":
        company_name = request.form.get("company_name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not company_name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register_recruiter.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register_recruiter.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("register_recruiter.html")

        try:
            auth_service.register_recruiter(company_name, email, password)
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.recruiter_login"))
        except auth_service.AuthError as error:
            flash(error.message, "danger")

    return render_template("register_recruiter.html")


@auth_bp.route("/student-dashboard")
@login_required(user_type="student")
def student_dashboard():
    return render_template("student_dashboard.html")


@auth_bp.route("/recruiter-dashboard")
@login_required(user_type="recruiter")
def recruiter_dashboard():
    return render_template("recruiter_dashboard.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))
