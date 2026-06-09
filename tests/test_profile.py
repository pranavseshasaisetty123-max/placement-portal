import os
import unittest
import tempfile
import io
import shutil
from werkzeug.datastructures import FileStorage

from app import create_app
from app.services import profile_service, auth_service, job_service, application_service
from database.connection import get_db
from config import Config


class ProfileTestCase(unittest.TestCase):
    def setUp(self):
        # Create temp folder for files and temp database
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.temp_dir = tempfile.mkdtemp()
        
        # Override configuration paths
        from config import Config
        self.old_database_path = Config.DATABASE_PATH
        self.old_upload_folder = Config.UPLOAD_FOLDER
        
        Config.DATABASE_PATH = self.db_path
        Config.UPLOAD_FOLDER = self.temp_dir

        # Setup application factory and contexts
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
        
        # Clean up temp directories
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Restore configuration
        from config import Config
        Config.DATABASE_PATH = self.old_database_path
        Config.UPLOAD_FOLDER = self.old_upload_folder

    def setup_seed_data(self):
        # Register students
        auth_service.register_student("Alice Student", "alice@test.com", "password123")
        auth_service.register_student("Bob Student", "bob@test.com", "password123")
        
        # Register recruiters
        auth_service.register_recruiter("BigCorp", "recruiter@bigcorp.com", "password123")
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

    def test_upload_resume_success(self):
        """Test uploading a valid PDF resume successfully."""
        pdf_data = b"%PDF-1.4MockPDFData"
        file = FileStorage(
            stream=io.BytesIO(pdf_data),
            filename="resume.pdf",
            content_type="application/pdf"
        )
        
        unique_name = profile_service.upload_resume(self.alice_id, file)
        self.assertTrue(unique_name.endswith(".pdf"))

        # Verify file is saved in the correct uploads sub-directory
        saved_file_path = os.path.join(self.temp_dir, "resumes", unique_name)
        self.assertTrue(os.path.exists(saved_file_path))
        with open(saved_file_path, "rb") as f:
            self.assertEqual(f.read(), pdf_data)

        # Verify DB updated
        profile = profile_service.get_student_profile(self.alice_id)
        self.assertEqual(profile["resume_path"], unique_name)

    def test_upload_resume_invalid_extension(self):
        """Test uploading a non-PDF file is rejected."""
        txt_data = b"Some plain text resume content"
        file = FileStorage(
            stream=io.BytesIO(txt_data),
            filename="resume.txt",
            content_type="text/plain"
        )
        with self.assertRaises(profile_service.ProfileError) as context:
            profile_service.upload_resume(self.alice_id, file)
        self.assertIn("Only PDF resumes are accepted", context.exception.message)

    def test_upload_resume_too_large(self):
        """Test uploading an oversized file is rejected."""
        large_data = b"0" * (Config.MAX_CONTENT_LENGTH + 100)
        file = FileStorage(
            stream=io.BytesIO(large_data),
            filename="large_resume.pdf",
            content_type="application/pdf"
        )
        with self.assertRaises(profile_service.ProfileError) as context:
            profile_service.upload_resume(self.alice_id, file)
        self.assertIn("exceeds the 2MB limit", context.exception.message)

    def test_replace_resume_deletes_old_file(self):
        """Test that replacing a resume deletes the old physical file."""
        file1 = FileStorage(stream=io.BytesIO(b"%PDF-1.4FirstResume"), filename="cv1.pdf", content_type="application/pdf")
        name1 = profile_service.upload_resume(self.alice_id, file1)
        path1 = os.path.join(self.temp_dir, "resumes", name1)
        self.assertTrue(os.path.exists(path1))

        # Upload replacement
        file2 = FileStorage(stream=io.BytesIO(b"%PDF-1.4SecondResume"), filename="cv2.pdf", content_type="application/pdf")
        name2 = profile_service.upload_resume(self.alice_id, file2)
        path2 = os.path.join(self.temp_dir, "resumes", name2)
        
        self.assertTrue(os.path.exists(path2))
        self.assertFalse(os.path.exists(path1))  # Old file must be deleted

    def test_access_permissions(self):
        """Test granular student and recruiter access controls."""
        # Setup: Alice has a resume
        file = FileStorage(stream=io.BytesIO(b"%PDF-1.4AliceCV"), filename="cv.pdf", content_type="application/pdf")
        profile_service.upload_resume(self.alice_id, file)

        # 1. Student self access: Alice accesses Alice (True)
        self.assertTrue(profile_service.can_access_resume(self.alice_id, "student", self.alice_id))
        
        # 2. Student non-owner access: Bob accesses Alice (False)
        self.assertFalse(profile_service.can_access_resume(self.bob_id, "student", self.alice_id))

        # 3. Recruiter owner access: BigCorp owns job Alice applied to (True)
        self.assertTrue(profile_service.can_access_resume(self.recruiter_big_id, "recruiter", self.alice_id))

        # 4. Recruiter non-owner access: SmallCorp owns no jobs Alice applied to (False)
        self.assertFalse(profile_service.can_access_resume(self.recruiter_small_id, "recruiter", self.alice_id))


if __name__ == "__main__":
    unittest.main()
