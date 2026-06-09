from app.routes.applications import applications_bp
from app.routes.auth import auth_bp
from app.routes.jobs import jobs_bp
from app.routes.main import main_bp

__all__ = ["auth_bp", "main_bp", "jobs_bp", "applications_bp"]

