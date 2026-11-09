"""عملیات دیتابیس — پیمانکاران

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def create_contractor(
    name, code=None, national_id=None, economic_code=None,
    registration_number=None, manager_name=None,
    phone=None, mobile=None, email=None, address=None,
    postal_code=None, city=None, province=None,
    grade=None, is_active=1, sort_order=0, description=None,
):
    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO contractors (
                name, code, national_id, economic_code,
                registration_number, manager_name,
                phone, mobile, email, address,
                postal_code, city, province,
                grade, is_active, sort_order, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, code, national_id, economic_code,
            registration_number, manager_name,
            phone, mobile, email, address,
            postal_code, city, province,
            grade, is_active, sort_order, description
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"❌ خطا در ایجاد پیمانکار: {e}")
        return None
    finally:
        connection.close()


def get_contractor(contractor_id):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM contractors WHERE id = ?", (contractor_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_contractor_by_code(code):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM contractors WHERE code = ?", (code,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_all_contractors(only_active=False):
    connection = get_connection()
    try:
        sql = "SELECT * FROM contractors"
        if only_active:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY sort_order ASC, name ASC"
        rows = connection.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def update_contractor(contractor_id, **kwargs):
    if not kwargs:
        return False
    allowed_fields = {
        "name", "code", "national_id", "economic_code",
        "registration_number", "manager_name",
        "phone", "mobile", "email", "address",
        "postal_code", "city", "province",
        "grade", "is_active",
        "sort_order", "description",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not fields:
        return False
    fields["updated_at"] = now_tehran_str()      # ★ زمان ایران
    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [contractor_id]
    connection = get_connection()
    try:
        connection.execute(
            f"UPDATE contractors SET {set_clause} WHERE id = ?", values
        )
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


def delete_contractor(contractor_id):
    connection = get_connection()
    try:
        connection.execute(
            "DELETE FROM contractors WHERE id = ?", (contractor_id,)
        )
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


def search_contractors(query, only_active=False):
    connection = get_connection()
    try:
        sql = """
            SELECT * FROM contractors
            WHERE (name LIKE ? OR code LIKE ? OR manager_name LIKE ?
                   OR national_id LIKE ? OR phone LIKE ? OR mobile LIKE ?)
        """
        params = [f"%{query}%"] * 6
        if only_active:
            sql += " AND is_active = 1"
        sql += " ORDER BY name ASC"
        rows = connection.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


__all__ = [
    "create_contractor",
    "get_contractor",
    "get_contractor_by_code",
    "get_all_contractors",
    "update_contractor",
    "delete_contractor",
    "search_contractors",
]
