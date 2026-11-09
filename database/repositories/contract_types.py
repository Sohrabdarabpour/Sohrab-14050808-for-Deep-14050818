"""عملیات دیتابیس — انواع قرارداد

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def get_all_contract_types(only_active=False):
    connection = get_connection()
    try:
        sql = "SELECT * FROM contract_types"
        if only_active:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY sort_order ASC, title ASC"
        rows = connection.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def get_contract_type(contract_type_id):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM contract_types WHERE id = ?",
            (contract_type_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_contract_type_by_code(code):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM contract_types WHERE code = ?", (code,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def create_contract_type(title, code=None, color="#1b698b",
                         description=None, sort_order=0, is_active=1):
    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO contract_types
            (title, code, color, description, sort_order, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, code, color, description, sort_order, is_active))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"❌ خطا در ایجاد نوع قرارداد: {e}")
        return None
    finally:
        connection.close()


def update_contract_type(contract_type_id, **kwargs):
    if not kwargs:
        return False
    allowed = {"title", "code", "color", "description",
               "sort_order", "is_active"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [contract_type_id]
    connection = get_connection()
    try:
        connection.execute(
            f"UPDATE contract_types SET {set_clause} WHERE id = ?", values
        )
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


def delete_contract_type(contract_type_id):
    connection = get_connection()
    try:
        connection.execute(
            "DELETE FROM contract_types WHERE id = ?", (contract_type_id,)
        )
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


__all__ = [
    "get_all_contract_types",
    "get_contract_type",
    "get_contract_type_by_code",
    "create_contract_type",
    "update_contract_type",
    "delete_contract_type",
]
