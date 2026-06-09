from database.connection import get_db


def create_notification(user_id, user_type, message, conn=None):
    """
    Insert a new notification row.
    """
    if conn is not None:
        conn.execute(
            "INSERT INTO notifications (user_id, user_type, message) VALUES (?, ?, ?)",
            (user_id, user_type, message),
        )
    else:
        with get_db() as conn_new:
            conn_new.execute(
                "INSERT INTO notifications (user_id, user_type, message) VALUES (?, ?, ?)",
                (user_id, user_type, message),
            )
            conn_new.commit()



def get_notifications_for_user(user_id, user_type, limit=None):
    """
    Fetch all notifications for the given user, sorted by created_at DESC.
    Optional limit argument helps query recent alerts.
    """
    query = """
        SELECT id, user_id, user_type, message, is_read, created_at
        FROM notifications
        WHERE user_id = ? AND user_type = ?
    """
    params = [user_id, user_type]
    
    query += " ORDER BY id DESC"
    
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_unread_count(user_id, user_type):
    """
    Returns the count of notifications where is_read = 0.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND user_type = ? AND is_read = 0",
            (user_id, user_type),
        ).fetchone()
    return row[0] if row else 0


def mark_as_read(notification_id, user_id, user_type):
    """
    Enforces ownership check and updates notification's is_read status to 1.
    """
    with get_db() as conn:
        # Verify ownership
        notif = conn.execute(
            "SELECT 1 FROM notifications WHERE id = ? AND user_id = ? AND user_type = ?",
            (notification_id, user_id, user_type),
        ).fetchone()
        
        if not notif:
            raise ValueError("Notification not found or unauthorized.")

        conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = ?",
            (notification_id,),
        )
        conn.commit()


def clear_all_for_user(user_id, user_type):
    """
    Deletes all notification records for the given user.
    """
    with get_db() as conn:
        conn.execute(
            "DELETE FROM notifications WHERE user_id = ? AND user_type = ?",
            (user_id, user_type),
        )
        conn.commit()
