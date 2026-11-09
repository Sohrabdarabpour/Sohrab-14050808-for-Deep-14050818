"""عملیات دیتابیس — اعضای پروژه

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def get_project_members(project_id):
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT pm.*,
                u.full_name, u.username, u.avatar,
                u.email AS user_email, u.phone AS user_phone,
                pr.title AS role_title, pr.code AS role_code,
                pr.color AS role_color,
                pr.is_exclusive, pr.is_required
            FROM project_members pm
            JOIN users u ON u.id = pm.user_id
            JOIN project_roles pr ON pr.id = pm.role_id
            WHERE pm.project_id = ? AND pm.is_active = 1
            ORDER BY pr.sort_order ASC, u.full_name ASC
        """, (project_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def get_user_projects(user_id):
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT p.*,
                pr.title AS role_title,
                pr.code  AS role_code,
                pr.color AS role_color
            FROM project_members pm
            JOIN projects p ON p.id = pm.project_id
            JOIN project_roles pr ON pr.id = pm.role_id
            WHERE pm.user_id = ? AND pm.is_active = 1
            ORDER BY p.created_at DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def get_project_role_members(project_id, role_id):
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT pm.*, u.full_name
            FROM project_members pm
            JOIN users u ON u.id = pm.user_id
            WHERE pm.project_id = ?
              AND pm.role_id = ?
              AND pm.is_active = 1
        """, (project_id, role_id)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def is_project_member(project_id, user_id, role_id):
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT id FROM project_members
            WHERE project_id = ? AND user_id = ?
              AND role_id = ? AND is_active = 1
        """, (project_id, user_id, role_id)).fetchone()
        return bool(row)
    finally:
        connection.close()


def add_project_member(project_id, user_id, role_id,
                       responsibility=None, notes=None,
                       assigned_by=None):
    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO project_members
            (project_id, user_id, role_id,
             responsibility, notes, assigned_by, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (project_id, user_id, role_id,
              responsibility, notes, assigned_by))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"❌ خطا در افزودن عضو: {e}")
        return None
    finally:
        connection.close()


def update_project_member(member_id, **kwargs):
    if not kwargs:
        return False
    allowed = {"role_id", "responsibility", "notes", "is_active"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [member_id]
    connection = get_connection()
    try:
        connection.execute(
            f"UPDATE project_members SET {set_clause} WHERE id = ?", values
        )
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


def remove_project_member(member_id):
    connection = get_connection()
    try:
        connection.execute("""
            UPDATE project_members
            SET is_active = 0,
                removed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (member_id,))
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


def hard_delete_project_member(member_id):
    connection = get_connection()
    try:
        connection.execute(
            "DELETE FROM project_members WHERE id = ?", (member_id,)
        )
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


__all__ = [
    "get_project_members",
    "get_user_projects",
    "get_project_role_members",
    "is_project_member",
    "add_project_member",
    "update_project_member",
    "remove_project_member",
    "hard_delete_project_member",
]
