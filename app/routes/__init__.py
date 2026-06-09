from app.routes.admin import admin_bp
from app.routes.applications import applications_bp
from app.routes.auth import auth_bp
from app.routes.jobs import jobs_bp
from app.routes.main import main_bp
from app.routes.notifications import notifications_bp
from app.routes.profile import profile_bp

__all__ = ["auth_bp", "main_bp", "jobs_bp", "applications_bp", "profile_bp", "admin_bp", "notifications_bp"]

