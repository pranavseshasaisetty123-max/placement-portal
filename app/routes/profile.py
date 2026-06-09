import os

from flask import Blueprint, flash, redirect, render_template, request, session, send_from_directory, url_for
from werkzeug.utils import secure_filename

from app.services import profile_service
from app.utils.session import login_required
from config import Config

# Section 1: Blueprint registration
profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/")
@login_required(user_type="student")
def view_profile():
    """
    Route to render the student profile page.
    Displays student info and resume status.
    """
    student_id = session.get("user_id")
    profile = profile_service.get_student_profile(student_id)
    if not profile:
        flash("Student profile not found.", "danger")
        return redirect(url_for("auth.logout"))
    return render_template("profile.html", student=profile)


@profile_bp.route("/resume/upload", methods=["GET", "POST"])
@login_required(user_type="student")
def upload_resume():
    """
    Route to handle uploading/replacing a resume.
    GET: renders form.
    POST: processes uploaded PDF file.
    """
    student_id = session.get("user_id")
    profile = profile_service.get_student_profile(student_id)

    if request.method == "POST":
        # Section 2: Fetch and validate the uploaded file from request
        if "resume" not in request.files:
            flash("No file part in request.", "danger")
            return render_template("upload_resume.html", student=profile)

        file = request.files["resume"]

        try:
            profile_service.upload_resume(student_id, file)
            flash("Resume uploaded successfully!", "success")
            return redirect(url_for("profile.view_profile"))
        except profile_service.ProfileError as error:
            flash(error.message, "danger")

    return render_template("upload_resume.html", student=profile)


@profile_bp.route("/resume/view/<int:student_id>")
@login_required()
def view_resume(student_id):
    """
    Secure route to preview a student's resume PDF inline.
    Performs recruiter/student authorization checks.
    """
    user_id = session.get("user_id")
    user_type = session.get("user_type")

    # Section 3: Access Control Verification
    if not profile_service.can_access_resume(user_id, user_type, student_id):
        flash("Unauthorized: You do not have permission to view this resume.", "danger")
        return redirect(url_for("main.home"))

    profile = profile_service.get_student_profile(student_id)
    if not profile or not profile.get("resume_path"):
        flash("Resume not found.", "danger")
        return redirect(url_for("main.home"))

    resumes_dir = os.path.join(Config.UPLOAD_FOLDER, "resumes")
    return send_from_directory(
        resumes_dir,
        profile["resume_path"],
        mimetype="application/pdf"
    )


@profile_bp.route("/resume/download/<int:student_id>")
@login_required()
def download_resume(student_id):
    """
    Secure route to download a student's resume PDF as attachment.
    Performs recruiter/student authorization checks.
    """
    user_id = session.get("user_id")
    user_type = session.get("user_type")

    # Section 3: Access Control Verification
    if not profile_service.can_access_resume(user_id, user_type, student_id):
        flash("Unauthorized: You do not have permission to download this resume.", "danger")
        return redirect(url_for("main.home"))

    profile = profile_service.get_student_profile(student_id)
    if not profile or not profile.get("resume_path"):
        flash("Resume not found.", "danger")
        return redirect(url_for("main.home"))

    resumes_dir = os.path.join(Config.UPLOAD_FOLDER, "resumes")
    safe_name = secure_filename(f"resume_{profile['name']}.pdf")
    return send_from_directory(
        resumes_dir,
        profile["resume_path"],
        as_attachment=True,
        download_name=safe_name
    )
