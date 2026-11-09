"""عملیات دیتابیس — نقش‌های پروژه

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def get_all_project_roles(only_active=False):
    connection = get_connection()
    try:
        sql = "SELECT * FROM project_roles"
        if only_active:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY sort_order ASC, title ASC"
        rows = connection.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def get_project_roles(only_active=False):
    return get_all_project_roles(only_active=only_active)


def get_project_role(role_id):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM project_roles WHERE id = ?", (role_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_project_role_by_code(code):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM project_roles WHERE code = ?", (code,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def create_project_role(title, code=None, color="#1b698b",
                        description=None, is_exclusive=0,
                        is_required=0, sort_order=0, is_active=1):
    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO project_roles
            (title, code, color, description,
             is_exclusive, is_required, sort_order, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, code, color, description,
              is_exclusive, is_required, sort_order, is_active))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"❌ خطا در ایجاد نقش پروژه: {e}")
        return None
    finally:
        connection.close()


def update_project_role(role_id, **kwargs):
    if not kwargs:
        return False
    allowed = {"title", "code", "color", "description",
               "is_exclusive", "is_required",
               "sort_order", "is_active"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [role_id]
    connection = get_connection()
    try:
        connection.execute(
            f"UPDATE project_roles SET {set_clause} WHERE id = ?", values
        )
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


def delete_project_role(role_id):
    connection = get_connection()
    try:
        used = connection.execute(
            "SELECT COUNT(*) AS c FROM project_members WHERE role_id = ?",
            (role_id,)
        ).fetchone()
        if used and used["c"] > 0:
            print(f"⚠️  این نقش در {used['c']} پروژه استفاده شده")
            return False
        connection.execute("DELETE FROM project_roles WHERE id = ?", (role_id,))
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


__all__ = [
    "get_all_project_roles",
    "get_project_roles",
    "get_project_role",
    "get_project_role_by_code",
    "create_project_role",
    "update_project_role",
    "delete_project_role",
]
