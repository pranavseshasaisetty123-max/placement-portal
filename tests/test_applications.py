import os
import unittest
import tempfile
import sqlite3

from app import create_app
from app.services import application_service, auth_service, job_service
from database.connection import get_db


class ApplicationTestCase(unittest.TestCase):
    def setUp(self):
        # Create a temp database file path
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Override configuration for test database
        from config import Config
        self.old_database_path = Config.DATABASE_PATH
        Config.DATABASE_PATH = self.db_path
        
        # Setup application factory and push context
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Insert seed data
        self.setup_seed_data()

    def tearDown(self):
        self.app_context.pop()
        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
        except OSError:
            pass
        
        # Restore configuration
        from config import Config
        Config.DATABASE_PATH = self.old_database_path

    def setup_seed_data(self):
        # Register test student and recruiters using original services
        auth_service.register_student("John Doe", "student@test.com", "password123")
        auth_service.register_recruiter("Test Corp", "recruiter@test.com", "password123")
        auth_service.register_recruiter("Other Corp", "other@test.com", "password123")
        
        # Retrieve IDs
        with get_db() as conn:
            self.student_id = conn.execute(
                "SELECT student_id FROM students WHERE email = 'student@test.com'"
            ).fetchone()["student_id"]
            self.recruiter_id = conn.execute(
                "SELECT recruiter_id FROM recruiters WHERE email = 'recruiter@test.com'"
            ).fetchone()["recruiter_id"]
            self.other_recruiter_id = conn.execute(
                "SELECT recruiter_id FROM recruiters WHERE email = 'other@test.com'"
            ).fetchone()["recruiter_id"]
            
        # Create a job listing for test Corp
        job_service.create_job(
            "Software Engineer", "Develop software", "Remote", "Python, Flask", self.recruiter_id
        )
        
        with get_db() as conn:
            self.job_id = conn.execute(
                "SELECT job_id FROM jobs WHERE recruiter_id = ?", (self.recruiter_id,)
            ).fetchone()["job_id"]

    def test_apply_to_job_success(self):
        """Test that a student can successfully apply to a job."""
        application_service.apply_to_job(self.student_id, self.job_id)
        
        # Retrieve applications and verify fields
        apps = application_service.get_student_applications(self.student_id)
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["job_title"], "Software Engineer")
        self.assertEqual(apps[0]["company_name"], "Test Corp")
        self.assertEqual(apps[0]["status"], "pending")

    def test_duplicate_application_prevention(self):
        """Test duplicate prevention via both application logic and DB constraints."""
        # First application should succeed
        application_service.apply_to_job(self.student_id, self.job_id)
        
        # Second application should raise ApplicationError (application validation logic)
        with self.assertRaises(application_service.ApplicationError) as context:
            application_service.apply_to_job(self.student_id, self.job_id)
        self.assertIn("already applied", context.exception.message)
        
        # Direct insert to database should fail with IntegrityError (database UNIQUE constraint check)
        with self.assertRaises(sqlite3.IntegrityError):
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO applications (student_id, job_id, status) VALUES (?, ?, 'pending')",
                    (self.student_id, self.job_id)
                )

    def test_get_applicants_for_job_ownership(self):
        """Test that recruiters can view applicants and ownership checks are enforced."""
        # Apply to job
        application_service.apply_to_job(self.student_id, self.job_id)
        
        # Owner recruiter gets candidates list
        data = application_service.get_applicants_for_job(self.job_id, self.recruiter_id)
        self.assertEqual(data["job_title"], "Software Engineer")
        self.assertEqual(len(data["applicants"]), 1)
        self.assertEqual(data["applicants"][0]["student_name"], "John Doe")
        self.assertEqual(data["applicants"][0]["student_email"], "student@test.com")
        
        # Unauthorized recruiter attempts to view candidates -> ApplicationError
        with self.assertRaises(application_service.ApplicationError) as context:
            application_service.get_applicants_for_job(self.job_id, self.other_recruiter_id)
        self.assertIn("Unauthorized", context.exception.message)

    def test_update_application_status(self):
        """Test recruiter can update application status and ownership checks are enforced."""
        # Apply
        application_service.apply_to_job(self.student_id, self.job_id)
        
        with get_db() as conn:
            app_id = conn.execute("SELECT application_id FROM applications").fetchone()["application_id"]
            
        # Update status to 'Shortlisted' (success case)
        application_service.update_application_status(app_id, "Shortlisted", self.recruiter_id)
        
        # Verify status is updated in db
        apps = application_service.get_student_applications(self.student_id)
        self.assertEqual(apps[0]["status"], "shortlisted")
        
        # Invalid status update should raise ApplicationError
        with self.assertRaises(application_service.ApplicationError):
            application_service.update_application_status(app_id, "invalid_status", self.recruiter_id)
            
        # Unauthorized status update by other recruiter should raise ApplicationError
        with self.assertRaises(application_service.ApplicationError) as context:
            application_service.update_application_status(app_id, "Selected", self.other_recruiter_id)
        self.assertIn("Unauthorized", context.exception.message)

    def test_get_applicant_count_by_job(self):
        """Test candidate count tracking per job."""
        # Initial candidate count is 0
        counts = application_service.get_applicant_count_by_job(self.recruiter_id)
        self.assertEqual(counts.get(self.job_id, 0), 0)
        
        # Apply
        application_service.apply_to_job(self.student_id, self.job_id)
        
        # Candidate count is now 1
        counts = application_service.get_applicant_count_by_job(self.recruiter_id)
        self.assertEqual(counts.get(self.job_id), 1)


if __name__ == "__main__":
    unittest.main()
