import os
import uuid

from werkzeug.utils import secure_filename

from config import Config
from database.connection import get_db


class ProfileError(Exception):
    """Custom exception class for profile and resume operations."""
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def get_student_profile(student_id):
    """
    Retrieve student profile details.
    """
    # Section 1: Fetch student by ID
    with get_db() as conn:
        row = conn.execute(
            "SELECT student_id, name, email, resume_path FROM students WHERE student_id = ?",
            (student_id,)
        ).fetchone()
    return dict(row) if row else None


def upload_resume(student_id, file):
    """
    Validate, securely store, and record a student's resume PDF.
    Deletes the old resume file if one exists to prevent storage leakage.
    """
    # Section 1: File presence and validation
    if not file or file.filename == '':
        raise ProfileError("No file selected.")

    # Validate file extension
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext != '.pdf':
        raise ProfileError("Invalid file type. Only PDF resumes are accepted.")

    # Validate MIME type
    if file.mimetype and file.mimetype != 'application/pdf':
        raise ProfileError("Invalid file type. Only PDF resumes are accepted.")

    # Validate size (application-level fallback check for 2MB limit)
    # Seek to end to measure size, then seek back
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > Config.MAX_CONTENT_LENGTH:
        raise ProfileError("File size exceeds the 2MB limit.")

    # Section 2: Create directories if not existing
    resumes_dir = os.path.join(Config.UPLOAD_FOLDER, "resumes")
    os.makedirs(resumes_dir, exist_ok=True)

    # Section 3: Manage replacement of old file
    with get_db() as conn:
        student = conn.execute(
            "SELECT resume_path FROM students WHERE student_id = ?",
            (student_id,)
        ).fetchone()

    if not student:
        raise ProfileError("Student profile not found.")

    old_path = student["resume_path"]
    if old_path:
        # Resolve path safely and remove old file if it exists
        full_old_path = os.path.join(Config.UPLOAD_FOLDER, "resumes", old_path)
        if os.path.exists(full_old_path):
            try:
                os.remove(full_old_path)
            except OSError:
                pass  # Silently proceed if deletion fails

    # Section 4: Generate unique, secure filename and save
    safe_name = secure_filename(filename)
    unique_name = f"resume_{student_id}_{uuid.uuid4().hex}.pdf"
    full_new_path = os.path.join(resumes_dir, unique_name)

    try:
        file.save(full_new_path)
    except Exception as e:
        raise ProfileError(f"Failed to save file: {str(e)}")

    # Section 5: Update database path record
    with get_db() as conn:
        conn.execute(
            "UPDATE students SET resume_path = ? WHERE student_id = ?",
            (unique_name, student_id)
        )
        # Hook: Send notification to student
        from app.services import notification_service
        notification_service.create_notification(
            student_id,
            "student",
            "Your resume has been successfully uploaded/updated.",
            conn=conn
        )
        conn.commit()

    return unique_name


def can_access_resume(user_id, user_type, student_id):
    """
    Access Control Enforcement:
    - Students can only view/download their own resume.
    - Recruiters can access resumes only for students who applied to jobs they own.
    """
    if not user_id or not user_type:
        return False

    # Section 0: Check Admin permission (Admins have global access)
    if user_type == "admin":
        return True

    # Section 1: Check Student permission
    if user_type == "student":
        return int(user_id) == int(student_id)

    # Section 2: Check Recruiter permission
    if user_type == "recruiter":
        with get_db() as conn:
            # Query if there exists an application by student_id to any job owned by recruiter_id
            application = conn.execute(
                """
                SELECT 1
                FROM applications a
                JOIN jobs j ON a.job_id = j.job_id
                WHERE a.student_id = ? AND j.recruiter_id = ?
                LIMIT 1
                """,
                (student_id, user_id)
            ).fetchone()
            return application is not None

    return False
