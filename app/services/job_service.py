import sqlite3
from database.connection import get_db


class JobError(Exception):
    """Base exception for job operations."""
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def create_job(title, description, location, skills, recruiter_id):
    """Create a new job posting."""
    title = title.strip() if title else ""
    description = description.strip() if description else ""
    location = location.strip() if location else ""
    skills = skills.strip() if skills else ""

    if not title or not description or not location or not skills:
        raise JobError("All fields (Title, Description, Location, and Skills) are required.")

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO jobs (title, description, location, skills, recruiter_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, description, location, skills, recruiter_id),
        )
        # Hook: Send notification to recruiter
        from app.services import notification_service
        notification_service.create_notification(
            recruiter_id,
            "recruiter",
            f"Your job listing '{title}' has been successfully created.",
            conn=conn
        )
        conn.commit()


def get_job_by_id(job_id):
    """Retrieve details for a single job, including recruiter's company and email."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT j.job_id, j.title, j.description, j.location, j.skills, j.recruiter_id,
                   r.company_name, r.email as recruiter_email
            FROM jobs j
            JOIN recruiters r ON j.recruiter_id = r.recruiter_id
            WHERE j.job_id = ?
            """,
            (job_id,),
        ).fetchone()
    return dict(row) if row else None


def get_jobs_by_recruiter(recruiter_id):
    """Retrieve all jobs posted by a specific recruiter."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT job_id, title, location, skills, description
            FROM jobs
            WHERE recruiter_id = ?
            ORDER BY job_id DESC
            """,
            (recruiter_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_job(job_id, title, description, location, skills, recruiter_id):
    """Update an existing job posting. Verifies ownership first."""
    title = title.strip() if title else ""
    description = description.strip() if description else ""
    location = location.strip() if location else ""
    skills = skills.strip() if skills else ""

    if not title or not description or not location or not skills:
        raise JobError("All fields (Title, Description, Location, and Skills) are required.")

    with get_db() as conn:
        # Check ownership
        job = conn.execute(
            "SELECT recruiter_id FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()

        if not job:
            raise JobError("Job not found.")
        if job["recruiter_id"] != recruiter_id:
            raise JobError("Unauthorized: You do not own this job listing.")

        conn.execute(
            """
            UPDATE jobs
            SET title = ?, description = ?, location = ?, skills = ?
            WHERE job_id = ?
            """,
            (title, description, location, skills, job_id),
        )
        conn.commit()


def delete_job(job_id, recruiter_id):
    """Delete a job posting. Verifies ownership first."""
    with get_db() as conn:
        # Check ownership
        job = conn.execute(
            "SELECT recruiter_id FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()

        if not job:
            raise JobError("Job not found.")
        if job["recruiter_id"] != recruiter_id:
            raise JobError("Unauthorized: You do not own this job listing.")

        # Delete any associated applications first (to maintain foreign key/integrity constraints)
        conn.execute("DELETE FROM applications WHERE job_id = ?", (job_id,))
        # Delete the job
        conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        conn.commit()


def search_jobs(query=None):
    """Search for jobs by title, company name, skills, or location."""
    with get_db() as conn:
        if query:
            like_query = f"%{query.strip()}%"
            rows = conn.execute(
                """
                SELECT j.job_id, j.title, j.description, j.location, j.skills, j.recruiter_id,
                       r.company_name
                FROM jobs j
                JOIN recruiters r ON j.recruiter_id = r.recruiter_id
                WHERE j.title LIKE ? OR r.company_name LIKE ? OR j.skills LIKE ? OR j.location LIKE ?
                ORDER BY j.job_id DESC
                """,
                (like_query, like_query, like_query, like_query),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT j.job_id, j.title, j.description, j.location, j.skills, j.recruiter_id,
                       r.company_name
                FROM jobs j
                JOIN recruiters r ON j.recruiter_id = r.recruiter_id
                ORDER BY j.job_id DESC
                """
            ).fetchall()
    return [dict(row) for row in rows]


def apply_to_job(student_id, job_id):
    """Submit a job application for a student."""
    with get_db() as conn:
        # Verify job exists
        job = conn.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if not job:
            raise JobError("Job not found.")

        # Check for existing application
        existing = conn.execute(
            "SELECT 1 FROM applications WHERE student_id = ? AND job_id = ?",
            (student_id, job_id),
        ).fetchone()

        if existing:
            raise JobError("You have already applied for this job.")

        conn.execute(
            "INSERT INTO applications (student_id, job_id, status) VALUES (?, ?, 'pending')",
            (student_id, job_id),
        )
        conn.commit()


def get_student_applications(student_id):
    """Retrieve all job IDs that the student has applied for."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT job_id FROM applications WHERE student_id = ?",
            (student_id,),
        ).fetchall()
    return {row["job_id"] for row in rows}
