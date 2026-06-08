from database.connection import get_db


class JobError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def _row_to_dict(row):
    return dict(row) if row else None


def _rows_to_dicts(rows):
    return [dict(row) for row in rows]


def create_job(recruiter_id, title, description, location):
    if not title or not description or not location:
        raise JobError("Title, description, and location are required.")

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO jobs (title, description, location, recruiter_id)
            VALUES (?, ?, ?, ?)
            """,
            (title, description, location, recruiter_id),
        )
        conn.commit()


def get_jobs_by_recruiter(recruiter_id):
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT job_id, title, description, location, recruiter_id
            FROM jobs
            WHERE recruiter_id = ?
            ORDER BY job_id DESC
            """,
            (recruiter_id,),
        ).fetchall()

    return _rows_to_dicts(rows)


def get_all_jobs():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT j.job_id, j.title, j.description, j.location,
                   j.recruiter_id, r.company_name
            FROM jobs j
            JOIN recruiters r ON j.recruiter_id = r.recruiter_id
            ORDER BY j.job_id DESC
            """
        ).fetchall()

    return _rows_to_dicts(rows)


def search_jobs(query):
    search_term = f"%{query.strip()}%"

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT j.job_id, j.title, j.description, j.location,
                   j.recruiter_id, r.company_name
            FROM jobs j
            JOIN recruiters r ON j.recruiter_id = r.recruiter_id
            WHERE j.title LIKE ? OR j.description LIKE ?
            ORDER BY j.job_id DESC
            """,
            (search_term, search_term),
        ).fetchall()

    return _rows_to_dicts(rows)


def get_job_by_id(job_id):
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT j.job_id, j.title, j.description, j.location,
                   j.recruiter_id, r.company_name
            FROM jobs j
            JOIN recruiters r ON j.recruiter_id = r.recruiter_id
            WHERE j.job_id = ?
            """,
            (job_id,),
        ).fetchone()

    return _row_to_dict(row)


def get_job_for_recruiter(job_id, recruiter_id):
    job = get_job_by_id(job_id)

    if job is None:
        raise JobError("Job not found.")

    if job["recruiter_id"] != recruiter_id:
        raise JobError("You do not have permission to modify this job.")

    return job


def update_job(job_id, recruiter_id, title, description, location):
    if not title or not description or not location:
        raise JobError("Title, description, and location are required.")

    get_job_for_recruiter(job_id, recruiter_id)

    with get_db() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET title = ?, description = ?, location = ?
            WHERE job_id = ? AND recruiter_id = ?
            """,
            (title, description, location, job_id, recruiter_id),
        )
        conn.commit()


def delete_job(job_id, recruiter_id):
    get_job_for_recruiter(job_id, recruiter_id)

    with get_db() as conn:
        conn.execute(
            "DELETE FROM jobs WHERE job_id = ? AND recruiter_id = ?",
            (job_id, recruiter_id),
        )
        conn.commit()
