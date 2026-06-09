import os
import unittest
import tempfile

from app import create_app
from app.services import admin_service, auth_service, job_service, application_service
from database.connection import get_db
from config import Config


class AdminTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Override paths
        from config import Config
        self.old_database_path = Config.DATABASE_PATH
        Config.DATABASE_PATH = self.db_path

        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        self.setup_seed_data()

    def tearDown(self):
        self.app_context.pop()
        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

        from config import Config
        Config.DATABASE_PATH = self.old_database_path

    def setup_seed_data(self):
        # Default admin is seeded automatically in create_app -> init_db
        # Register extra student and recruiter
        auth_service.register_student("Alice Student", "alice@test.com", "password123")
        auth_service.register_recruiter("BigCorp", "recruiter@bigcorp.com", "password123")

        with get_db() as conn:
            self.student_id = conn.execute("SELECT student_id FROM students WHERE email = 'alice@test.com'").fetchone()["student_id"]
            self.recruiter_id = conn.execute("SELECT recruiter_id FROM recruiters WHERE email = 'recruiter@bigcorp.com'").fetchone()["recruiter_id"]

        # Post a job
        job_service.create_job("Staff Engineer", "Clean Python", "Austin", "Python", self.recruiter_id)
        with get_db() as conn:
            self.job_id = conn.execute("SELECT job_id FROM jobs").fetchone()["job_id"]

        # Apply
        application_service.apply_to_job(self.student_id, self.job_id)

    def login_client(self, email, password, user_type):
        url = "/student-login" if user_type == "student" else "/recruiter-login"
        self.client.post(url, data={"email": email, "password": password})

    def logout_client(self):
        self.client.get("/logout")

    def test_admin_authenticate_success(self):
        """Verify admin credentials authentication succeeds."""
        # Seeded username is admin, email admin@placement.com, password admin123
        admin_data = admin_service.authenticate_admin("admin", "admin123")
        self.assertEqual(admin_data["user_type"], "admin")
        self.assertEqual(admin_data["email"], "admin@placement.com")

        admin_data = admin_service.authenticate_admin("admin@placement.com", "admin123")
        self.assertEqual(admin_data["user_type"], "admin")

    def test_admin_authenticate_failure(self):
        """Verify invalid credentials authentication fails."""
        with self.assertRaises(admin_service.AdminError):
            admin_service.authenticate_admin("admin", "wrongpassword")
        with self.assertRaises(admin_service.AdminError):
            admin_service.authenticate_admin("nonexistent", "admin123")

    def test_admin_route_guards(self):
        """Verify route guards: students and recruiters cannot access admin console."""
        # 1. Anonymous access -> redirects to admin login
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.location)

        # 2. Student logged in -> redirected to home
        self.login_client("alice@test.com", "password123", "student")
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("/admin/login", response.location)  # redirects to home
        self.logout_client()

        # 3. Recruiter logged in -> redirected to home
        self.login_client("recruiter@bigcorp.com", "password123", "recruiter")
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 302)
        self.logout_client()

    def test_recruiter_suspension_flow(self):
        """Verify recruiter deactivation and reactivation blocks/unblocks login."""
        # Active recruiter can login
        auth_service.authenticate_recruiter("recruiter@bigcorp.com", "password123")

        # Deactivate recruiter
        admin_service.toggle_recruiter_status(self.recruiter_id, is_active=False)

        # Verification: AuthError is raised
        with self.assertRaises(auth_service.AuthError) as context:
            auth_service.authenticate_recruiter("recruiter@bigcorp.com", "password123")
        self.assertIn("deactivated", context.exception.message)

        # Reactivate recruiter
        admin_service.toggle_recruiter_status(self.recruiter_id, is_active=True)

        # Verification: Can login again
        auth_service.authenticate_recruiter("recruiter@bigcorp.com", "password123")

    def test_job_moderation_deletion(self):
        """Verify admin can delete inappropriate jobs and clear related applications."""
        # Check job count is 1
        analytics = admin_service.get_dashboard_analytics()
        self.assertEqual(analytics["total_jobs"], 1)
        self.assertEqual(analytics["total_applications"], 1)

        # Delete job
        admin_service.delete_job_by_admin(self.job_id)

        # Check counts updated to 0
        analytics = admin_service.get_dashboard_analytics()
        self.assertEqual(analytics["total_jobs"], 0)
        self.assertEqual(analytics["total_applications"], 0)

    def test_applications_status_filtering(self):
        """Verify applications status filters query logic."""
        # Check all applications (1)
        apps = admin_service.get_all_applications()
        self.assertEqual(len(apps), 1)

        # Filter by pending (1)
        apps = admin_service.get_all_applications(status_filter="pending")
        self.assertEqual(len(apps), 1)

        # Filter by selected (0)
        apps = admin_service.get_all_applications(status_filter="selected")
        self.assertEqual(len(apps), 0)


if __name__ == "__main__":
    unittest.main()
