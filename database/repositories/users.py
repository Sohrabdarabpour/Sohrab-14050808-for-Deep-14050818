"""عملیات دیتابیس — کاربران

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def get_all_users_for_select(only_active=True):
    connection = get_connection()
    try:
        sql = "SELECT id, username, full_name, role, avatar FROM users"
        if only_active:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY full_name ASC"
        rows = connection.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def get_user(user_id):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_users_by_role(role_code, only_active=True):
    connection = get_connection()
    try:
        sql = "SELECT id, full_name, username, avatar FROM users WHERE role = ?"
        if only_active:
            sql += " AND is_active = 1"
        rows = connection.execute(sql, (role_code,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


__all__ = [
    "get_all_users_for_select",
    "get_user",
    "get_users_by_role",
]
