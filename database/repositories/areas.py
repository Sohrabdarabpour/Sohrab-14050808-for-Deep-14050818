"""عملیات دیتابیس — نواحی

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def get_all_areas(only_active=True):
    connection = get_connection()
    try:
        sql = "SELECT * FROM areas"
        if only_active:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY sort_order ASC, title ASC"
        rows = connection.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def get_area(area_id):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM areas WHERE id = ?", (area_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def create_area(title, code=None, sort_order=0, is_active=1):
    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO areas (title, code, sort_order, is_active)
            VALUES (?, ?, ?, ?)
        """, (title, code, sort_order, is_active))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        return None
    finally:
        connection.close()


def update_area(area_id, **kwargs):
    if not kwargs:
        return False
    allowed = {"title", "code", "sort_order", "is_active"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [area_id]
    connection = get_connection()
    try:
        connection.execute(
            f"UPDATE areas SET {set_clause} WHERE id = ?", values
        )
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


def delete_area(area_id):
    connection = get_connection()
    try:
        connection.execute("DELETE FROM areas WHERE id = ?", (area_id,))
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


__all__ = [
    "get_all_areas",
    "get_area",
    "create_area",
    "update_area",
    "delete_area",
]
