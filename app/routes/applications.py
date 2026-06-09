from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.services import application_service
from app.utils.session import login_required

# Section 1: Blueprint definition with url_prefix
applications_bp = Blueprint("applications", __name__, url_prefix="/applications")


@applications_bp.route("/my-applications")
@login_required(user_type="student")
def my_applications():
    """
    Route for students to view all jobs they have applied for and their status.
    Uses the application_service to fetch student applications.
    """
    student_id = session.get("user_id")
    applications = application_service.get_student_applications(student_id)
    return render_template("my_applications.html", applications=applications)


@applications_bp.route("/job/<int:job_id>/applicants")
@login_required(user_type="recruiter")
def job_applicants(job_id):
    """
    Route for recruiters to view all applicants for a job they own.
    Performs ownership validation inside application_service and handles errors.
    """
    recruiter_id = session.get("user_id")
    try:
        data = application_service.get_applicants_for_job(job_id, recruiter_id)
        return render_template(
            "job_applicants.html",
            job_id=job_id,
            job_title=data["job_title"],
            applicants=data["applicants"],
        )
    except application_service.ApplicationError as error:
        flash(error.message, "danger")
        return redirect(url_for("jobs.my_jobs"))


@applications_bp.route("/status/<int:application_id>", methods=["POST"])
@login_required(user_type="recruiter")
def update_status(application_id):
    """
    Route for recruiters to update the status of an application.
    Checks and updates the status via application_service.
    Redirects back to the applicants page for the specific job.
    """
    recruiter_id = session.get("user_id")
    status = request.form.get("status", "").strip()
    job_id = request.form.get("job_id")  # For user-friendly redirect back to candidate list

    try:
        application_service.update_application_status(
            application_id, status, recruiter_id
        )
        flash("Application status updated successfully!", "success")
    except application_service.ApplicationError as error:
        flash(error.message, "danger")

    if job_id:
        return redirect(url_for("applications.job_applicants", job_id=job_id))
    return redirect(url_for("jobs.my_jobs"))
