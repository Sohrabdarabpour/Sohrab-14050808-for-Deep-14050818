"""عملیات دیتابیس تعطیلات تقویم.

لایهٔ دسترسی به داده — بدون منطق کسب‌وکار و بدون پیام فارسی.
"""

import sqlite3

from database.connection import get_connection


def list_years():
    """سال‌های شمسی که تعطیلی دارند (نزولی)."""
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT DISTINCT jalali_year FROM calendar_holidays ORDER BY jalali_year DESC"
        ).fetchall()
        return [row["jalali_year"] for row in rows]
    finally:
        connection.close()


def list_for_year(year):
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT id, holiday_date, jalali_date, jalali_year, title, kind, reason, created_at
            FROM calendar_holidays
            WHERE jalali_year = ?
            ORDER BY holiday_date
            """,
            (year,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get(holiday_id):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM calendar_holidays WHERE id = ?", (holiday_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_by_date(holiday_date):
    """تعطیلی همان تاریخ (میلادی YYYY/MM/DD) یا None."""
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM calendar_holidays WHERE holiday_date = ?",
            (holiday_date,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def all_active_dates():
    """همهٔ تاریخ‌های تعطیل فعال (میلادی YYYY/MM/DD) برای محاسبهٔ روز کاری."""
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT holiday_date FROM calendar_holidays WHERE is_active = 1"
        ).fetchall()
        return {row["holiday_date"] for row in rows}
    finally:
        connection.close()


def all_dates():
    """همهٔ تاریخ‌های ثبت‌شده (برای جلوگیری از درج تکراری در seed)."""
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT holiday_date FROM calendar_holidays"
        ).fetchall()
        return {row["holiday_date"] for row in rows}
    finally:
        connection.close()


def create(
    holiday_date,
    jalali_date,
    jalali_year,
    title,
    kind,
    created_by=None,
    reason=None,
):
    """درج تعطیلی؛ خروجی: created | duplicate | error."""
    connection = get_connection()
    try:
        connection.execute(
            """
            INSERT INTO calendar_holidays
            (
                holiday_date, jalali_date, jalali_year, title, kind, reason,
                is_active, created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (holiday_date, jalali_date, jalali_year, title, kind, reason, created_by),
        )
        connection.commit()
        return "created"
    except sqlite3.IntegrityError:
        return "duplicate"
    except Exception:
        return "error"
    finally:
        connection.close()


def delete(holiday_id):
    connection = get_connection()
    try:
        cursor = connection.execute(
            "DELETE FROM calendar_holidays WHERE id = ?", (holiday_id,)
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()
