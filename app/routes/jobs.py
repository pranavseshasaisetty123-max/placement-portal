from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.services import jobs_service
from app.utils.session import login_required

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/jobs/create", methods=["GET", "POST"])
@login_required(user_type="recruiter")
def create_job():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()

        try:
            jobs_service.create_job(session["user_id"], title, description, location)
            flash("Job posted successfully.", "success")
            return redirect(url_for("jobs.my_jobs"))
        except jobs_service.JobError as error:
            flash(error.message, "danger")

    return render_template("create_job.html")


@jobs_bp.route("/jobs/my-jobs")
@login_required(user_type="recruiter")
def my_jobs():
    jobs = jobs_service.get_jobs_by_recruiter(session["user_id"])
    return render_template("my_jobs.html", jobs=jobs)


@jobs_bp.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
@login_required(user_type="recruiter")
def edit_job(job_id):
    try:
        job = jobs_service.get_job_for_recruiter(job_id, session["user_id"])
    except jobs_service.JobError as error:
        flash(error.message, "danger")
        return redirect(url_for("jobs.my_jobs"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()

        try:
            jobs_service.update_job(
                job_id,
                session["user_id"],
                title,
                description,
                location,
            )
            flash("Job updated successfully.", "success")
            return redirect(url_for("jobs.my_jobs"))
        except jobs_service.JobError as error:
            flash(error.message, "danger")

    return render_template("edit_job.html", job=job)


@jobs_bp.route("/jobs/<int:job_id>/delete", methods=["POST"])
@login_required(user_type="recruiter")
def delete_job(job_id):
    try:
        jobs_service.delete_job(job_id, session["user_id"])
        flash("Job deleted successfully.", "success")
    except jobs_service.JobError as error:
        flash(error.message, "danger")

    return redirect(url_for("jobs.my_jobs"))


@jobs_bp.route("/jobs/browse")
@login_required(user_type="student")
def browse_jobs():
    query = request.args.get("q", "").strip()

    if query:
        jobs = jobs_service.search_jobs(query)
    else:
        jobs = jobs_service.get_all_jobs()

    return render_template("browse_jobs.html", jobs=jobs, query=query)


@jobs_bp.route("/jobs/<int:job_id>")
@login_required(user_type="student")
def job_detail(job_id):
    job = jobs_service.get_job_by_id(job_id)

    if job is None:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs.browse_jobs"))

    return render_template("job_detail.html", job=job)
