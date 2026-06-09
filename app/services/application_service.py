import sqlite3
from database.connection import get_db


class ApplicationError(Exception):
    """Exception class for application-related errors."""
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def apply_to_job(student_id, job_id):
    """
    Apply to a job for a student.
    Ensures that the job exists and prevents duplicate applications
    using both application-level validation and database-level unique constraints.
    """
    # Section 1: Input validation & existence check
    with get_db() as conn:
        job = conn.execute("SELECT job_id FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if not job:
            raise ApplicationError("Job not found.")

        # Section 2: Application-level check for duplicate application
        existing = conn.execute(
            "SELECT 1 FROM applications WHERE student_id = ? AND job_id = ?",
            (student_id, job_id)
        ).fetchone()
        if existing:
            raise ApplicationError("You have already applied for this job.")

        # Section 3: Insert application record & handle database-level constraint violations
        try:
            conn.execute(
                "INSERT INTO applications (student_id, job_id, status) VALUES (?, ?, 'pending')",
                (student_id, job_id)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Secondary check in case of race conditions (UNIQUE constraint violated)
            raise ApplicationError("You have already applied for this job.")


def get_student_applications(student_id):
    """
    Retrieve all job applications submitted by a student.
    Includes job title, company name, location, and the status.
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT a.application_id, a.status, j.job_id, j.title as job_title, j.location,
                   r.company_name
            FROM applications a
            JOIN jobs j ON a.job_id = j.job_id
            JOIN recruiters r ON j.recruiter_id = r.recruiter_id
            WHERE a.student_id = ?
            ORDER BY a.application_id DESC
            """,
            (student_id,)
        ).fetchall()
    return [dict(row) for row in rows]


def get_student_applied_job_ids(student_id):
    """
    Retrieve a set of job IDs that the student has already applied to.
    This is helper logic for rendering the search and detail pages.
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT job_id FROM applications WHERE student_id = ?",
            (student_id,)
        ).fetchall()
    return {row["job_id"] for row in rows}


def get_applicants_for_job(job_id, recruiter_id):
    """
    Retrieve all student applications for a specific job.
    Includes recruiter ownership check.
    """
    with get_db() as conn:
        # Section 1: Recruiter ownership validation
        job = conn.execute(
            "SELECT title, recruiter_id FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        
        if not job:
            raise ApplicationError("Job not found.")
        
        if job["recruiter_id"] != recruiter_id:
            raise ApplicationError("Unauthorized: You do not own this job listing.")

        # Section 2: Fetch applicant details
        rows = conn.execute(
            """
            SELECT a.application_id, a.status, s.student_id, s.name as student_name, s.email as student_email
            FROM applications a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.job_id = ?
            ORDER BY a.application_id DESC
            """,
            (job_id,)
        ).fetchall()
        
    return {
        "job_title": job["title"],
        "applicants": [dict(row) for row in rows]
    }


def update_application_status(application_id, status, recruiter_id):
    """
    Update the status of a job application.
    Enforces that only the job owner (recruiter) can modify the status
    and ensures only valid statuses are saved.
    """
    # Section 1: Status validation
    normalized_status = status.strip().lower()
    allowed_statuses = ["pending", "reviewed", "shortlisted", "rejected", "selected"]
    if normalized_status not in allowed_statuses:
        raise ApplicationError(f"Invalid application status: '{status}'.")

    with get_db() as conn:
        # Section 2: Application existence & ownership verification
        app_data = conn.execute(
            """
            SELECT a.application_id, j.recruiter_id
            FROM applications a
            JOIN jobs j ON a.job_id = j.job_id
            WHERE a.application_id = ?
            """,
            (application_id,)
        ).fetchone()

        if not app_data:
            raise ApplicationError("Application not found.")

        if app_data["recruiter_id"] != recruiter_id:
            raise ApplicationError("Unauthorized: You do not own the job for this application.")

        # Section 3: Perform database update
        conn.execute(
            "UPDATE applications SET status = ? WHERE application_id = ?",
            (normalized_status, application_id)
        )
        conn.commit()


def get_applicant_count_by_job(recruiter_id):
    """
    Retrieve a mapping of job_id to applicant count for all jobs owned by a recruiter.
    Used for listing on 'My Jobs' dashboard.
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT j.job_id, COUNT(a.application_id) as applicant_count
            FROM jobs j
            LEFT JOIN applications a ON j.job_id = a.job_id
            WHERE j.recruiter_id = ?
            GROUP BY j.job_id
            """,
            (recruiter_id,)
        ).fetchall()
    return {row["job_id"]: row["applicant_count"] for row in rows}
