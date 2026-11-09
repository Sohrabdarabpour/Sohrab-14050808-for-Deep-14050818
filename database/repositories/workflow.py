"""عملیات دیتابیس — گردش‌کار و یادداشت‌ها

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def get_all_workflow_steps(only_active=True):
    connection = get_connection()
    try:
        sql = "SELECT * FROM workflow_steps"
        if only_active:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY step_order ASC, id ASC"
        rows = connection.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def get_workflow_step(step_id):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM workflow_steps WHERE id = ?",
            (step_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_workflow_step_by_code(code):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM workflow_steps WHERE code = ?",
            (code,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_next_workflow_step(current_step_id):
    connection = get_connection()
    try:
        current = connection.execute(
            "SELECT step_order FROM workflow_steps WHERE id = ?",
            (current_step_id,)
        ).fetchone()
        if not current:
            return None
        row = connection.execute("""
            SELECT * FROM workflow_steps
            WHERE step_order > ? AND is_active = 1
            ORDER BY step_order ASC
            LIMIT 1
        """, (current["step_order"],)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_first_workflow_step():
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT * FROM workflow_steps
            WHERE is_active = 1
            ORDER BY step_order ASC
            LIMIT 1
        """).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def create_note(
    document_id, user_id, content,
    current_step_id=None, assigned_to=None, parent_note_id=None,
    created_at=None, updated_at=None,     # ★ اضافه شد
):
    """ایجاد یادداشت با زمان قابل تنظیم (پیش‌فرض: زمان ایران)"""
    now_str = now_tehran_str()
    created_at = created_at or now_str
    updated_at = updated_at or now_str

    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO document_notes
            (document_id, user_id, content, status,
             current_step_id, assigned_to, parent_note_id,
             created_at, updated_at)
            VALUES (?, ?, ?, 'in_review', ?, ?, ?, ?, ?)
        """, (
            document_id, user_id, content,
            current_step_id, assigned_to, parent_note_id,
            created_at, updated_at,
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"❌ خطا در ایجاد یادداشت: {e}")
        return None
    finally:
        connection.close()


def get_note(note_id):
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT n.*,
                   u.full_name AS user_full_name,
                   u.username AS user_username,
                   u.avatar AS user_avatar,
                   u.role AS user_role,
                   ws.title AS step_title,
                   ws.code AS step_code,
                   ws.assigned_role AS step_role,
                   ws.step_order AS step_order,
                   au.full_name AS assigned_to_name,
                   d.subject AS document_subject,
                   d.code_dfc AS document_code,
                   d.department_id AS document_department
            FROM document_notes n
            LEFT JOIN users u ON u.id = n.user_id
            LEFT JOIN workflow_steps ws ON ws.id = n.current_step_id
            LEFT JOIN users au ON au.id = n.assigned_to
            LEFT JOIN documents d ON d.id = n.document_id
            WHERE n.id = ?
        """, (note_id,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def update_note(note_id, **kwargs):
    if not kwargs:
        return False

    allowed = {
        "content", "status", "current_step_id",
        "assigned_to", "parent_note_id", "closed_at",
        "created_at", "updated_at",       # ★ اضافه شد
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False

    # ★ اگر updated_at ست نشده، الان ست کن
    if "updated_at" not in fields:
        fields["updated_at"] = now_tehran_str()

    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [note_id]

    connection = get_connection()
    try:
        connection.execute(
            f"UPDATE document_notes SET {set_clause} WHERE id = ?", values
        )
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        print(f"❌ خطا در به‌روزرسانی یادداشت: {e}")
        return False
    finally:
        connection.close()


def get_notes_for_user(user_id, status="in_review"):
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT n.*,
                   u.full_name AS user_full_name,
                   u.avatar AS user_avatar,
                   ws.title AS step_title,
                   ws.code AS step_code,
                   d.subject AS document_subject,
                   d.code_dfc AS document_code
            FROM document_notes n
            LEFT JOIN users u ON u.id = n.user_id
            LEFT JOIN workflow_steps ws ON ws.id = n.current_step_id
            LEFT JOIN documents d ON d.id = n.document_id
            WHERE n.assigned_to = ? AND n.status = ?
            ORDER BY n.created_at DESC
        """, (user_id, status)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def get_notes_for_role(role_code, status="in_review"):
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT n.*,
                   u.full_name AS user_full_name,
                   u.avatar AS user_avatar,
                   ws.title AS step_title,
                   ws.code AS step_code,
                   d.subject AS document_subject,
                   d.code_dfc AS document_code
            FROM document_notes n
            LEFT JOIN users u ON u.id = n.user_id
            LEFT JOIN workflow_steps ws ON ws.id = n.current_step_id
            LEFT JOIN documents d ON d.id = n.document_id
            WHERE ws.assigned_role = ? AND n.status = ?
            ORDER BY n.created_at DESC
        """, (role_code, status)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def create_note_event(
    note_id, user_id, event_type,
    message=None,
    from_step_id=None, to_step_id=None,
    from_user_id=None, to_user_id=None,
    created_at=None,                     # ★ اضافه شد
):
    """ایجاد رخداد با زمان قابل تنظیم (پیش‌فرض: زمان ایران)"""
    created_at = created_at or now_tehran_str()

    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO note_events
            (note_id, user_id, event_type, message,
             from_step_id, to_step_id, from_user_id, to_user_id,
             created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note_id, user_id, event_type, message,
            from_step_id, to_step_id, from_user_id, to_user_id,
            created_at,
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"❌ خطا در ثبت رخداد: {e}")
        return None
    finally:
        connection.close()


def get_note_events(note_id):
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT e.*,
                   u.full_name AS user_full_name,
                   u.username AS user_username,
                   u.avatar AS user_avatar,
                   u.role AS user_role,
                   fs.title AS from_step_title,
                   ts.title AS to_step_title,
                   fu.full_name AS from_user_name,
                   tu.full_name AS to_user_name
            FROM note_events e
            LEFT JOIN users u ON u.id = e.user_id
            LEFT JOIN workflow_steps fs ON fs.id = e.from_step_id
            LEFT JOIN workflow_steps ts ON ts.id = e.to_step_id
            LEFT JOIN users fu ON fu.id = e.from_user_id
            LEFT JOIN users tu ON tu.id = e.to_user_id
            WHERE e.note_id = ?
            ORDER BY e.created_at ASC, e.id ASC
        """, (note_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


__all__ = [
    "get_all_workflow_steps",
    "get_workflow_step",
    "get_workflow_step_by_code",
    "get_next_workflow_step",
    "get_first_workflow_step",
    "create_note",
    "get_note",
    "update_note",
    "get_notes_for_user",
    "get_notes_for_role",
    "create_note_event",
    "get_note_events",
]
