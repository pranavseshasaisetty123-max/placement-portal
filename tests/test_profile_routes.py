import os
import unittest
import tempfile
import io
import shutil

from app import create_app
from app.services import profile_service, auth_service, job_service, application_service
from database.connection import get_db
from config import Config


class ProfileRoutesTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.temp_dir = tempfile.mkdtemp()
        
        # Override paths
        from config import Config
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

        from config import Config
        Config.DATABASE_PATH = self.old_database_path
        Config.UPLOAD_FOLDER = self.old_upload_folder

    def setup_seed_data(self):
        # Student 1 (Alice)
        auth_service.register_student("Alice Student", "alice@test.com", "password123")
        # Student 2 (Bob)
        auth_service.register_student("Bob Student", "bob@test.com", "password123")
        # Recruiter 1 (BigCorp)
        auth_service.register_recruiter("BigCorp", "recruiter@bigcorp.com", "password123")
        # Recruiter 2 (SmallCorp)
        auth_service.register_recruiter("SmallCorp", "recruiter@smallcorp.com", "password123")

        with get_db() as conn:
            self.alice_id = conn.execute("SELECT student_id FROM students WHERE email = 'alice@test.com'").fetchone()["student_id"]
            self.bob_id = conn.execute("SELECT student_id FROM students WHERE email = 'bob@test.com'").fetchone()["student_id"]
            self.recruiter_big_id = conn.execute("SELECT recruiter_id FROM recruiters WHERE email = 'recruiter@bigcorp.com'").fetchone()["recruiter_id"]
            self.recruiter_small_id = conn.execute("SELECT recruiter_id FROM recruiters WHERE email = 'recruiter@smallcorp.com'").fetchone()["recruiter_id"]

        # BigCorp posts job
        job_service.create_job("Frontend Dev", "Bootstrap developer", "CA", "HTML, CSS", self.recruiter_big_id)
        with get_db() as conn:
            self.job_big_id = conn.execute("SELECT job_id FROM jobs WHERE recruiter_id = ?", (self.recruiter_big_id,)).fetchone()["job_id"]

        # Alice applies to BigCorp's job
        application_service.apply_to_job(self.alice_id, self.job_big_id)

    def login_client(self, email, password, user_type):
        """Simulate browser login using the test client."""
        url = "/student-login" if user_type == "student" else "/recruiter-login"
        self.client.post(url, data={"email": email, "password": password})

    def logout_client(self):
        """Simulate browser logout using the test client."""
        self.client.get("/logout")

    def test_anonymous_access_redirect(self):
        """Verify that anonymous users are redirected to home/login."""
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/student-login", response.location)

    def test_student_profile_and_upload_success(self):
        """Verify student can view profile, upload a PDF resume, and view it."""
        self.login_client("alice@test.com", "password123", "student")
        
        # 1. View profile - check "No Resume" label
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No Resume Uploaded", response.data)

        # 2. View upload page
        response = self.client.get("/profile/resume/upload")
        self.assertEqual(response.status_code, 200)

        # 3. Post a valid PDF resume
        pdf_data = b"%PDF-1.4MockPDFContent"
        response = self.client.post(
            "/profile/resume/upload",
            data={"resume": (io.BytesIO(pdf_data), "cv.pdf")},
            content_type="multipart/form-data",
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Resume uploaded successfully!", response.data)
        self.assertIn(b"Resume Uploaded", response.data)

        # 4. View resume inline
        response = self.client.get(f"/profile/resume/view/{self.alice_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertEqual(response.data, pdf_data)

        # 5. Download resume as attachment
        response = self.client.get(f"/profile/resume/download/{self.alice_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("attachment", response.headers["Content-Disposition"])

    def test_student_upload_invalid_file(self):
        """Verify uploading an invalid text file is blocked and warns user."""
        self.login_client("alice@test.com", "password123", "student")
        
        # Post invalid text file
        response = self.client.post(
            "/profile/resume/upload",
            data={"resume": (io.BytesIO(b"Plain text info"), "cv.txt")},
            content_type="multipart/form-data",
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Only PDF resumes are accepted", response.data)

    def test_student_unauthorized_resume_access(self):
        """Verify Bob cannot view/download Alice's resume."""
        # Setup: Alice uploads resume
        self.login_client("alice@test.com", "password123", "student")
        self.client.post(
            "/profile/resume/upload",
            data={"resume": (io.BytesIO(b"%PDF-1.4AliceCV"), "cv.pdf")},
            content_type="multipart/form-data"
        )
        self.logout_client()

        # Login as Bob
        self.login_client("bob@test.com", "password123", "student")
        
        # Bob attempts to view Alice's resume -> redirects with unauthorized error
        response = self.client.get(f"/profile/resume/view/{self.alice_id}", follow_redirects=True)
        self.assertIn(b"You do not have permission", response.data)

    def test_recruiter_resume_access_permissions(self):
        """Verify recruiter access rules: BigCorp can access Alice's resume, SmallCorp cannot."""
        # Setup: Alice uploads resume
        self.login_client("alice@test.com", "password123", "student")
        self.client.post(
            "/profile/resume/upload",
            data={"resume": (io.BytesIO(b"%PDF-1.4AliceCV"), "cv.pdf")},
            content_type="multipart/form-data"
        )
        self.logout_client()

        # 1. Login as BigCorp (owns job Alice applied to) -> Should have access
        self.login_client("recruiter@bigcorp.com", "password123", "recruiter")
        response = self.client.get(f"/profile/resume/view/{self.alice_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"%PDF-1.4AliceCV")
        self.logout_client()

        # 2. Login as SmallCorp (does NOT own job Alice applied to) -> Access denied
        self.login_client("recruiter@smallcorp.com", "password123", "recruiter")
        response = self.client.get(f"/profile/resume/view/{self.alice_id}", follow_redirects=True)
        self.assertIn(b"You do not have permission", response.data)


if __name__ == "__main__":
    unittest.main()
