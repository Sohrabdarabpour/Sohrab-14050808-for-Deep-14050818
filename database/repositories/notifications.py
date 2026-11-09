"""عملیات دیتابیس — اعلان‌ها

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def create_notification(
    user_id,
    title,
    message=None,
    link=None,
    notification_type="info",
    document_id=None,
    note_id=None,
    created_at=None,                     # ★ اضافه شد
):
    """ایجاد نوتیفیکیشن با زمان قابل تنظیم"""
    created_at = created_at or now_tehran_str()

    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO notifications
            (user_id, title, message, link,
             notification_type, document_id, note_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, title, message, link,
            notification_type, document_id, note_id, created_at,
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"❌ خطا در ایجاد نوتیفیکیشن: {e}")
        return None
    finally:
        connection.close()


def get_user_notifications(user_id, unread_only=False, limit=50):
    connection = get_connection()
    try:
        sql = """
            SELECT n.*,
                   d.subject AS document_subject,
                   d.code_dfc AS document_code
            FROM notifications n
            LEFT JOIN documents d ON d.id = n.document_id
            WHERE n.user_id = ? AND n.is_dismissed = 0
        """
        params = [user_id]
        if unread_only:
            sql += " AND n.is_read = 0"
        sql += " ORDER BY n.created_at DESC LIMIT ?"
        params.append(limit)
        rows = connection.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def get_unread_notifications_count(user_id):
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT COUNT(*) AS cnt
            FROM notifications
            WHERE user_id = ? AND is_read = 0 AND is_dismissed = 0
        """, (user_id,)).fetchone()
        return int(row["cnt"] or 0)
    finally:
        connection.close()


def mark_notification_read(notification_id):
    """علامت‌گذاری نوتیفیکیشن به عنوان خوانده‌شده"""
    connection = get_connection()
    try:
        connection.execute("""
            UPDATE notifications
            SET is_read = 1,
                read_at = ?
            WHERE id = ?
        """, (now_tehran_str(), notification_id))
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        print(f"❌ خطا در read notification: {e}")
        return False
    finally:
        connection.close()


def mark_all_notifications_read(user_id):
    connection = get_connection()
    try:
        connection.execute("""
            UPDATE notifications
            SET is_read = 1,
                read_at = ?
            WHERE user_id = ? AND is_read = 0
        """, (now_tehran_str(), user_id))            # ★ زمان ایران
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


def dismiss_notification(notification_id):
    connection = get_connection()
    try:
        connection.execute("""
            UPDATE notifications
            SET is_dismissed = 1, is_read = 1
            WHERE id = ?
        """, (notification_id,))
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


def mark_notification_unread(notification_id):
    """
    علامت‌گذاری نوتیفیکیشن به عنوان نخوانده
    
    - is_read = 0
    - read_at = NULL
    """
    connection = get_connection()
    try:
        connection.execute("""
            UPDATE notifications
            SET is_read = 0,
                read_at = NULL
            WHERE id = ?
        """, (notification_id,))
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        print(f"❌ خطا در unread notification: {e}")
        return False
    finally:
        connection.close()


__all__ = [
    "create_notification",
    "get_user_notifications",
    "get_unread_notifications_count",
    "mark_notification_read",
    "mark_all_notifications_read",
    "dismiss_notification",
    "mark_notification_unread",
]
