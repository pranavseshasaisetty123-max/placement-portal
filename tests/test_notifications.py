import os
import unittest
import tempfile
import io
import shutil
from werkzeug.datastructures import FileStorage

from app import create_app
from app.services import (
    notification_service,
    auth_service,
    job_service,
    application_service,
    profile_service,
    admin_service,
)
from database.connection import get_db
from config import Config


class NotificationsTestCase(unittest.TestCase):
    def setUp(self):
        # Create temp folder for files and temp database
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.temp_dir = tempfile.mkdtemp()

        # Override paths
        self.old_database_path = Config.DATABASE_PATH
        self.old_upload_folder = Config.UPLOAD_FOLDER

        Config.DATABASE_PATH = self.db_path
        Config.UPLOAD_FOLDER = self.temp_dir

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
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        Config.DATABASE_PATH = self.old_database_path
        Config.UPLOAD_FOLDER = self.old_upload_folder

    def setup_seed_data(self):
        # Register student & recruiter
        auth_service.register_student("John Student", "john@test.com", "password123")
        auth_service.register_recruiter("TechCorp", "recruiter@techcorp.com", "password123")

        with get_db() as conn:
            self.student_id = conn.execute("SELECT student_id FROM students WHERE email = 'john@test.com'").fetchone()["student_id"]
            self.recruiter_id = conn.execute("SELECT recruiter_id FROM recruiters WHERE email = 'recruiter@techcorp.com'").fetchone()["recruiter_id"]

    def login_client(self, email, password, user_type):
        """Simulate browser login using the test client."""
        url = "/student-login" if user_type == "student" else "/recruiter-login"
        self.client.post(url, data={"email": email, "password": password})

    def logout_client(self):
        """Simulate browser logout using the test client."""
        self.client.get("/logout")

    # ==========================================
    # SECTION 1: Service Operations Tests
    # ==========================================

    def test_notification_creation_and_retrieval(self):
        """Test creating a notification and retrieving it for a user."""
        notification_service.create_notification(self.student_id, "student", "Hello John")
        notification_service.create_notification(self.student_id, "student", "Another alert")

        # Get all notifications
        notifs = notification_service.get_notifications_for_user(self.student_id, "student")
        self.assertEqual(len(notifs), 2)
        self.assertEqual(notifs[0]["message"], "Another alert")  # DESC order check
        self.assertEqual(notifs[0]["is_read"], 0)
        self.assertEqual(notifs[1]["message"], "Hello John")

        # Test limit filter
        recent = notification_service.get_notifications_for_user(self.student_id, "student", limit=1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["message"], "Another alert")

    def test_unread_count(self):
        """Test correct tallying of unread notifications count."""
        self.assertEqual(notification_service.get_unread_count(self.student_id, "student"), 0)

        notification_service.create_notification(self.student_id, "student", "Alert 1")
        notification_service.create_notification(self.student_id, "student", "Alert 2")
        self.assertEqual(notification_service.get_unread_count(self.student_id, "student"), 2)

        # Mark one as read
        notifs = notification_service.get_notifications_for_user(self.student_id, "student")
        notification_service.mark_as_read(notifs[0]["id"], self.student_id, "student")
        self.assertEqual(notification_service.get_unread_count(self.student_id, "student"), 1)

    def test_mark_as_read_ownership(self):
        """Test marking a notification as read and enforcing ownership check."""
        notification_service.create_notification(self.student_id, "student", "Secret notification")
        notifs = notification_service.get_notifications_for_user(self.student_id, "student")
        notif_id = notifs[0]["id"]

        # Try marking read as recruiter (unauthorized)
        with self.assertRaises(ValueError) as context:
            notification_service.mark_as_read(notif_id, self.recruiter_id, "recruiter")
        self.assertIn("unauthorized", str(context.exception))

        # Mark read as student (authorized)
        notification_service.mark_as_read(notif_id, self.student_id, "student")
        notifs_after = notification_service.get_notifications_for_user(self.student_id, "student")
        self.assertEqual(notifs_after[0]["is_read"], 1)

    def test_clear_all_for_user(self):
        """Test deleting all notification records for a user."""
        notification_service.create_notification(self.student_id, "student", "Alert 1")
        notification_service.create_notification(self.student_id, "student", "Alert 2")

        notification_service.clear_all_for_user(self.student_id, "student")
        self.assertEqual(notification_service.get_unread_count(self.student_id, "student"), 0)
        notifs = notification_service.get_notifications_for_user(self.student_id, "student")
        self.assertEqual(len(notifs), 0)

    # ==========================================
    # SECTION 2: Service Hook Triggers Tests
    # ==========================================

    def test_hook_job_created(self):
        """Test notification is triggered for recruiter when a job is posted."""
        job_service.create_job("Software Engineer", "Write clean code", "San Francisco", "Python, Flask", self.recruiter_id)

        notifs = notification_service.get_notifications_for_user(self.recruiter_id, "recruiter")
        self.assertEqual(len(notifs), 1)
        self.assertIn("listing 'Software Engineer' has been successfully created", notifs[0]["message"])

    def test_hook_job_application_submitted(self):
        """Test notification triggers for both student and recruiter upon job application."""
        # Setup: Recruiter posts a job
        job_service.create_job("Software Engineer", "Flask Dev", "Remote", "Python", self.recruiter_id)
        with get_db() as conn:
            job_id = conn.execute("SELECT job_id FROM jobs LIMIT 1").fetchone()["job_id"]

        # Student applies
        application_service.apply_to_job(self.student_id, job_id)

        # Check Student Notification
        student_notifs = notification_service.get_notifications_for_user(self.student_id, "student")
        self.assertEqual(len(student_notifs), 1)
        self.assertIn("successfully applied for the job 'Software Engineer'", student_notifs[0]["message"])

        # Check Recruiter Notification
        recruiter_notifs = notification_service.get_notifications_for_user(self.recruiter_id, "recruiter")
        # Note: Recruiter gets 2 notifications (1 for job creation, 1 for applicant submission)
        self.assertEqual(len(recruiter_notifs), 2)
        # Sort or filter recruiter_notifs to find the applicant alert
        applicant_alert = next(n for n in recruiter_notifs if "New applicant" in n["message"])
        self.assertIn("John Student has applied for your job listing: 'Software Engineer'", applicant_alert["message"])

    def test_hook_application_status_updated(self):
        """Test notification triggers for student when recruiter updates application status."""
        job_service.create_job("Software Engineer", "Flask Dev", "Remote", "Python", self.recruiter_id)
        with get_db() as conn:
            job_id = conn.execute("SELECT job_id FROM jobs LIMIT 1").fetchone()["job_id"]

        application_service.apply_to_job(self.student_id, job_id)
        with get_db() as conn:
            app_id = conn.execute("SELECT application_id FROM applications LIMIT 1").fetchone()["application_id"]

        # Clear old student notifications to check new trigger clearly
        notification_service.clear_all_for_user(self.student_id, "student")

        # Recruiter updates status
        application_service.update_application_status(app_id, "shortlisted", self.recruiter_id)

        student_notifs = notification_service.get_notifications_for_user(self.student_id, "student")
        self.assertEqual(len(student_notifs), 1)
        self.assertIn("status for the job 'Software Engineer' has been updated to: Shortlisted", student_notifs[0]["message"])

    def test_hook_resume_uploaded(self):
        """Test notification triggers for student when a resume is uploaded/replaced."""
        pdf_data = b"%PDF-1.4MockPDFData"
        file = FileStorage(
            stream=io.BytesIO(pdf_data),
            filename="cv.pdf",
            content_type="application/pdf"
        )

        profile_service.upload_resume(self.student_id, file)

        student_notifs = notification_service.get_notifications_for_user(self.student_id, "student")
        self.assertEqual(len(student_notifs), 1)
        self.assertIn("resume has been successfully uploaded/updated", student_notifs[0]["message"])

    def test_hook_recruiter_toggled(self):
        """Test notification triggers for recruiter when account status is toggled by admin."""
        # Deactivate recruiter
        admin_service.toggle_recruiter_status(self.recruiter_id, is_active=False)
        notifs = notification_service.get_notifications_for_user(self.recruiter_id, "recruiter")
        self.assertEqual(len(notifs), 1)
        self.assertIn("account has been suspended by the administrator", notifs[0]["message"])

        # Reactivate recruiter
        admin_service.toggle_recruiter_status(self.recruiter_id, is_active=True)
        notifs_after = notification_service.get_notifications_for_user(self.recruiter_id, "recruiter")
        self.assertEqual(len(notifs_after), 2)
        self.assertIn("account has been activated by the administrator", notifs_after[0]["message"])

    def test_hook_job_deleted_by_admin(self):
        """Test notification triggers for recruiter when job listing is deleted by admin."""
        job_service.create_job("Frontend Developer", "Flask Dev", "Remote", "Python", self.recruiter_id)
        with get_db() as conn:
            job_id = conn.execute("SELECT job_id FROM jobs LIMIT 1").fetchone()["job_id"]

        # Admin deletes job
        admin_service.delete_job_by_admin(job_id)

        recruiter_notifs = notification_service.get_notifications_for_user(self.recruiter_id, "recruiter")
        # Expecting 2: job created + job removed
        self.assertEqual(len(recruiter_notifs), 2)
        deleted_alert = next(n for n in recruiter_notifs if "removed by the administrator" in n["message"])
        self.assertIn("job listing 'Frontend Developer' has been removed by the administrator for moderation", deleted_alert["message"])

    # ==========================================
    # SECTION 3: HTTP Route/Controller Tests
    # ==========================================

    def test_route_view_notifications(self):
        """Verify the notifications dashboard page displays alerts correctly."""
        notification_service.create_notification(self.student_id, "student", "Notification #1")

        self.login_client("john@test.com", "password123", "student")
        response = self.client.get("/notifications/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Notification #1", response.data)

    def test_route_mark_read(self):
        """Verify the POST route marks a notification as read and redirects."""
        notification_service.create_notification(self.student_id, "student", "Mark Me Read")
        notifs = notification_service.get_notifications_for_user(self.student_id, "student")
        notif_id = notifs[0]["id"]

        self.login_client("john@test.com", "password123", "student")
        response = self.client.post(f"/notifications/read/{notif_id}", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Check db state
        notifs_after = notification_service.get_notifications_for_user(self.student_id, "student")
        self.assertEqual(notifs_after[0]["is_read"], 1)

    def test_route_clear_all(self):
        """Verify the POST route clears all notifications for the user."""
        notification_service.create_notification(self.student_id, "student", "Mark Me Read")

        self.login_client("john@test.com", "password123", "student")
        response = self.client.post("/notifications/clear", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Check db state
        notifs_after = notification_service.get_notifications_for_user(self.student_id, "student")
        self.assertEqual(len(notifs_after), 0)

    def test_unread_navbar_badge(self):
        """Verify the navbar context processor injects the correct unread count."""
        notification_service.create_notification(self.student_id, "student", "Unread Alert 1")
        notification_service.create_notification(self.student_id, "student", "Unread Alert 2")

        # When logged in, Navbar shows the correct badge count
        self.login_client("john@test.com", "password123", "student")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        # Search for unread count indicator in the rendered page
        self.assertIn(b"2", response.data)  # checks count in navbar pill


if __name__ == "__main__":
    unittest.main()
