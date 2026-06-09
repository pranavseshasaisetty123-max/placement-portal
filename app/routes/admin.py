from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.services import admin_service
from app.utils.session import login_required, login_user

# Section 1: Blueprint registration
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Route for administrator authentication.
    GET: renders admin login form.
    POST: verifies credentials and creates session.
    """
    if session.get("user_type") == "admin":
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        email_or_username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not email_or_username or not password:
            flash("All fields are required.", "danger")
            return render_template("admin_login.html")

        try:
            admin_data = admin_service.authenticate_admin(email_or_username, password)
            login_user(admin_data)
            flash("Administrator login successful.", "success")
            return redirect(url_for("admin.dashboard"))
        except admin_service.AdminError as error:
            flash(error.message, "danger")

    return render_template("admin_login.html")


@admin_bp.route("/dashboard")
@login_required(user_type="admin")
def dashboard():
    """
    Route to render the administrator analytics dashboard.
    """
    analytics = admin_service.get_dashboard_analytics()
    admin_id = session.get("user_id")
    from app.services import notification_service
    recent_alerts = notification_service.get_notifications_for_user(admin_id, "admin", limit=3)
    return render_template("admin_dashboard.html", analytics=analytics, recent_alerts=recent_alerts)


@admin_bp.route("/students")
@login_required(user_type="admin")
def students():
    """
    Route to view and audit all student profiles.
    """
    students_list = admin_service.get_all_students()
    return render_template("admin_students.html", students=students_list)


@admin_bp.route("/recruiters")
@login_required(user_type="admin")
def recruiters():
    """
    Route to audit and toggle recruiter account activation states.
    """
    recruiters_list = admin_service.get_all_recruiters()
    return render_template("admin_recruiters.html", recruiters=recruiters_list)


@admin_bp.route("/recruiters/<int:recruiter_id>/toggle", methods=["POST"])
@login_required(user_type="admin")
def toggle_recruiter(recruiter_id):
    """
    POST route to activate or deactivate a recruiter account.
    """
    is_active = request.form.get("is_active") == "1"
    try:
        admin_service.toggle_recruiter_status(recruiter_id, is_active)
        state_str = "activated" if is_active else "deactivated"
        flash(f"Recruiter account has been successfully {state_str}.", "success")
    except admin_service.AdminError as error:
        flash(error.message, "danger")
    return redirect(url_for("admin.recruiters"))


@admin_bp.route("/jobs")
@login_required(user_type="admin")
def jobs():
    """
    Route for job listings moderation.
    """
    jobs_list = admin_service.get_all_jobs()
    return render_template("admin_jobs.html", jobs=jobs_list)


@admin_bp.route("/jobs/<int:job_id>/delete", methods=["POST"])
@login_required(user_type="admin")
def delete_job(job_id):
    """
    POST route for admins to delete inappropriate job listings.
    """
    try:
        admin_service.delete_job_by_admin(job_id)
        flash("Job listing deleted successfully.", "success")
    except admin_service.AdminError as error:
        flash(error.message, "danger")
    return redirect(url_for("admin.jobs"))


@admin_bp.route("/applications")
@login_required(user_type="admin")
def applications():
    """
    Route to monitor all candidate applications, filterable by status.
    """
    status_filter = request.args.get("status", "").strip()
    
    # Section 2: Fetch and render applications
    applications_list = admin_service.get_all_applications(
        status_filter=status_filter if status_filter else None
    )
    return render_template(
        "admin_applications.html",
        applications=applications_list,
        current_filter=status_filter
    )
