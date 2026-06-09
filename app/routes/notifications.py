from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.services import notification_service
from app.utils.session import login_required

# Section 1: Blueprint registration
notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("/")
@login_required()
def view_notifications():
    """
    Renders the Activity Center view displaying all alerts for the logged-in user.
    """
    user_id = session.get("user_id")
    user_type = session.get("user_type")
    
    notifications = notification_service.get_notifications_for_user(user_id, user_type)
    return render_template("notifications.html", notifications=notifications)


@notifications_bp.route("/read/<int:notification_id>", methods=["POST"])
@login_required()
def mark_read(notification_id):
    """
    POST route to mark a specific notification as read.
    """
    user_id = session.get("user_id")
    user_type = session.get("user_type")
    
    try:
        notification_service.mark_as_read(notification_id, user_id, user_type)
        flash("Notification marked as read.", "success")
    except ValueError as error:
        flash(str(error), "danger")
        
    return redirect(url_for("notifications.view_notifications"))


@notifications_bp.route("/clear", methods=["POST"])
@login_required()
def clear_all():
    """
    POST route to delete all notifications for the active user.
    """
    user_id = session.get("user_id")
    user_type = session.get("user_type")
    
    notification_service.clear_all_for_user(user_id, user_type)
    flash("All notifications cleared successfully.", "info")
    return redirect(url_for("notifications.view_notifications"))
