from database.connection import get_db
from werkzeug.security import check_password_hash


class AdminError(Exception):
    """Custom exception class for administrative operations."""
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def authenticate_admin(email_or_username, password):
    """
    Authenticate administrative credentials.
    Works with either the admin email or username.
    """
    # Section 1: Query admin details
    with get_db() as conn:
        user = conn.execute(
            """
            SELECT admin_id, username, email, password
            FROM admins
            WHERE email = ? OR username = ?
            """,
            (email_or_username, email_or_username),
        ).fetchone()

    # Section 2: Validate password hash
    if user is None or not check_password_hash(user["password"], password):
        raise AdminError("Invalid admin credentials.")

    return {
        "user_id": user["admin_id"],
        "user_type": "admin",
        "display_name": f"Admin ({user['username']})",
        "email": user["email"],
    }


def get_dashboard_analytics():
    """
    Query database counts for dashboard statistics.
    Returns student, recruiter, job, and application totals.
    """
    # Section 1: Gather analytics totals
    with get_db() as conn:
        total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        total_recruiters = conn.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]
        total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        total_applications = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]

    return {
        "total_students": total_students,
        "total_recruiters": total_recruiters,
        "total_jobs": total_jobs,
        "total_applications": total_applications,
    }


def get_all_students():
    """
    Retrieve details of all registered students.
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT student_id, name, email, resume_path FROM students ORDER BY student_id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_all_recruiters():
    """
    Retrieve details of all recruiters.
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT recruiter_id, company_name, email, is_active FROM recruiters ORDER BY recruiter_id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def toggle_recruiter_status(recruiter_id, is_active):
    """
    Activate or deactivate recruiter accounts.
    Values: 1 for Active, 0 for Inactive.
    """
    # Section 1: Input conversion & database update
    status_val = 1 if is_active else 0
    with get_db() as conn:
        # Check existence
        recruiter = conn.execute(
            "SELECT 1 FROM recruiters WHERE recruiter_id = ?", (recruiter_id,)
        ).fetchone()
        if not recruiter:
            raise AdminError("Recruiter account not found.")

        conn.execute(
            "UPDATE recruiters SET is_active = ? WHERE recruiter_id = ?",
            (status_val, recruiter_id),
        )
        # Hook: Send account update notification to recruiter
        state_str = "activated" if is_active else "suspended"
        from app.services import notification_service
        notification_service.create_notification(
            recruiter_id,
            "recruiter",
            f"Your employer account has been {state_str} by the administrator.",
            conn=conn
        )
        conn.commit()


def get_all_jobs():
    """
    Retrieve all job listings with recruiter details.
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT j.job_id, j.title, j.description, j.location, j.skills,
                   r.company_name, r.email as recruiter_email
            FROM jobs j
            JOIN recruiters r ON j.recruiter_id = r.recruiter_id
            ORDER BY j.job_id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def delete_job_by_admin(job_id):
    """
    Delete a job listing directly (bypass ownership checks as Admin action).
    Cleans up candidate applications first.
    """
    # Section 1: Clean up and delete
    with get_db() as conn:
        # Check job existence
        job = conn.execute("SELECT title, recruiter_id FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if not job:
            raise AdminError("Job listing not found.")

        conn.execute("DELETE FROM applications WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        # Hook: Send moderation notification to recruiter
        from app.services import notification_service
        notification_service.create_notification(
            job["recruiter_id"],
            "recruiter",
            f"Your job listing '{job['title']}' has been removed by the administrator for moderation purposes.",
            conn=conn
        )
        conn.commit()


def get_all_applications(status_filter=None):
    """
    Audits applications system-wide, optionally filtered by application status.
    """
    # Section 1: Build base query and fetch applications
    query = """
        SELECT a.application_id, a.status,
               s.name as student_name, s.email as student_email,
               j.title as job_title, j.location,
               r.company_name
        FROM applications a
        JOIN students s ON a.student_id = s.student_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN recruiters r ON j.recruiter_id = r.recruiter_id
    """
    params = []

    if status_filter:
        query += " WHERE LOWER(a.status) = ?"
        params.append(status_filter.strip().lower())

    query += " ORDER BY a.application_id DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]
