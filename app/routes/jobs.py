from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.services import application_service, job_service
from app.utils.session import login_required

jobs_bp = Blueprint("jobs", __name__, url_prefix="/jobs")


@jobs_bp.route("/create", methods=["GET", "POST"])
@login_required(user_type="recruiter")
def create():
    """Route to post a new job."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        skills = request.form.get("skills", "").strip()
        recruiter_id = session.get("user_id")

        try:
            job_service.create_job(title, description, location, skills, recruiter_id)
            flash("Job posted successfully!", "success")
            return redirect(url_for("jobs.my_jobs"))
        except job_service.JobError as error:
            flash(error.message, "danger")
            return render_template(
                "create_job.html",
                title=title,
                description=description,
                location=location,
                skills=skills,
            )

    return render_template("create_job.html")


@jobs_bp.route("/my-jobs")
@login_required(user_type="recruiter")
def my_jobs():
    """Route to show jobs posted by the logged-in recruiter."""
    recruiter_id = session.get("user_id")
    jobs = job_service.get_jobs_by_recruiter(recruiter_id)
    
    # Get the candidate application count for each job
    applicant_counts = application_service.get_applicant_count_by_job(recruiter_id)
    for job in jobs:
        job["applicant_count"] = applicant_counts.get(job["job_id"], 0)
        
    return render_template("my_jobs.html", jobs=jobs)


@jobs_bp.route("/<int:job_id>/edit", methods=["GET", "POST"])
@login_required(user_type="recruiter")
def edit(job_id):
    """Route to edit a job. Confirms recruiter owns the job before modification."""
    recruiter_id = session.get("user_id")
    job = job_service.get_job_by_id(job_id)

    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs.my_jobs"))

    if job["recruiter_id"] != recruiter_id:
        flash("Unauthorized: You do not own this job listing.", "danger")
        return redirect(url_for("jobs.my_jobs"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        skills = request.form.get("skills", "").strip()

        try:
            job_service.update_job(job_id, title, description, location, skills, recruiter_id)
            flash("Job updated successfully!", "success")
            return redirect(url_for("jobs.my_jobs"))
        except job_service.JobError as error:
            flash(error.message, "danger")
            # Create a dictionary representing form fields to preserve input
            form_job = {
                "job_id": job_id,
                "title": title,
                "description": description,
                "location": location,
                "skills": skills,
            }
            return render_template("create_job.html", job=form_job)

    return render_template("create_job.html", job=job)


@jobs_bp.route("/<int:job_id>/delete", methods=["POST"])
@login_required(user_type="recruiter")
def delete(job_id):
    """Route to delete a job. Confirms ownership."""
    recruiter_id = session.get("user_id")
    try:
        job_service.delete_job(job_id, recruiter_id)
        flash("Job deleted successfully!", "success")
    except job_service.JobError as error:
        flash(error.message, "danger")
    return redirect(url_for("jobs.my_jobs"))


@jobs_bp.route("/browse")
@login_required(user_type="student")
def browse():
    """Route for students to browse and search for jobs."""
    query = request.args.get("q", "").strip()
    jobs = job_service.search_jobs(query)
    return render_template("job_list.html", jobs=jobs, query=query)


@jobs_bp.route("/<int:job_id>")
@login_required(user_type="student")
def detail(job_id):
    """Route for students to view the details of a single job."""
    student_id = session.get("user_id")
    job = job_service.get_job_by_id(job_id)
    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs.browse"))

    # Check if student has already applied using application_service
    applied_jobs = application_service.get_student_applied_job_ids(student_id)
    has_applied = job_id in applied_jobs

    return render_template("job_detail.html", job=job, has_applied=has_applied)


@jobs_bp.route("/<int:job_id>/apply", methods=["POST"])
@login_required(user_type="student")
def apply(job_id):
    """Route for students to apply to a job using application_service."""
    student_id = session.get("user_id")
    try:
        application_service.apply_to_job(student_id, job_id)
        flash("Application submitted successfully!", "success")
    except application_service.ApplicationError as error:
        flash(error.message, "danger")
    return redirect(url_for("jobs.detail", job_id=job_id))
