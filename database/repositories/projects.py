"""عملیات دیتابیس — پروژه‌ها

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def create_project(
    name,
    code=None,
    project_number=None,
    description=None,
    contractor_id=None,
    contract_type_id=None,
    area_id=None,
    created_by=None,
    contract_number=None,
    contract_amount=None,
    contract_number_foreign=None,
    contract_amount_foreign=None,
    currency="USD",
    contract_start_date=None,
    contract_end_date=None,
    start_date=None,
    planned_end_date=None,
    actual_end_date=None,
    duration_days=None,
    status="active",
    priority="medium",
    progress_percent=0,
    physical_progress=0,
    time_progress=0,
    financial_progress=0,
    financial_progress_rial=0,
    financial_progress_foreign=0,
    budget=None,
    total_paid=0,
    total_amendments_amount=0,
    location=None,
    province=None,
    city=None,
    latitude=None,
    longitude=None,
    tags=None,
    notes=None,
    is_active=1,
    sort_order=0,
):
    connection = get_connection()
    try:
        cursor = connection.execute("""
            INSERT INTO projects (
                name, code, project_number, description,
                contractor_id, contract_type_id, area_id, created_by,
                contract_number, contract_amount,
                contract_number_foreign, contract_amount_foreign, currency,
                contract_start_date, contract_end_date,
                start_date, planned_end_date, actual_end_date,
                duration_days,
                status, priority,
                progress_percent, physical_progress, time_progress,
                financial_progress, financial_progress_rial,
                financial_progress_foreign,
                budget, total_paid, total_amendments_amount,
                location, province, city, latitude, longitude,
                tags, notes,
                is_active, sort_order
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?,
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?
            )
        """, (
            name, code, project_number, description,
            contractor_id, contract_type_id, area_id, created_by,
            contract_number, contract_amount,
            contract_number_foreign, contract_amount_foreign, currency,
            contract_start_date, contract_end_date,
            start_date, planned_end_date, actual_end_date,
            duration_days,
            status, priority,
            progress_percent, physical_progress, time_progress,
            financial_progress, financial_progress_rial,
            financial_progress_foreign,
            budget, total_paid, total_amendments_amount,
            location, province, city, latitude, longitude,
            tags, notes,
            is_active, sort_order
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"❌ خطا در ایجاد پروژه: {e}")
        return None
    finally:
        connection.close()


def get_project(project_id):
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT
                p.*,
                c.name AS contractor_name,
                c.code AS contractor_code,
                ct.title AS contract_type_title,
                ct.code  AS contract_type_code,
                ct.color AS contract_type_color,
                a.title  AS area_title,
                a.code   AS area_code,
                u.full_name AS creator_name
            FROM projects p
            LEFT JOIN contractors c     ON c.id = p.contractor_id
            LEFT JOIN contract_types ct ON ct.id = p.contract_type_id
            LEFT JOIN areas a           ON a.id = p.area_id
            LEFT JOIN users u           ON u.id = p.created_by
            WHERE p.id = ?
        """, (project_id,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_project_by_code(code):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM projects WHERE code = ?", (code,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_all_projects(
    only_active=False,
    contractor_id=None,
    contract_type_id=None,
    area_id=None,
    status=None,
):
    connection = get_connection()
    try:
        sql = """
            SELECT
                p.*,
                c.name AS contractor_name,
                ct.title AS contract_type_title,
                ct.color AS contract_type_color,
                a.title AS area_title
            FROM projects p
            LEFT JOIN contractors c     ON c.id = p.contractor_id
            LEFT JOIN contract_types ct ON ct.id = p.contract_type_id
            LEFT JOIN areas a           ON a.id = p.area_id
            WHERE 1=1
        """
        params = []
        if only_active:
            sql += " AND p.is_active = 1"
        if contractor_id:
            sql += " AND p.contractor_id = ?"
            params.append(contractor_id)
        if contract_type_id:
            sql += " AND p.contract_type_id = ?"
            params.append(contract_type_id)
        if area_id:
            sql += " AND p.area_id = ?"
            params.append(area_id)
        if status:
            sql += " AND p.status = ?"
            params.append(status)
        sql += " ORDER BY p.sort_order ASC, p.created_at DESC"
        rows = connection.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def update_project(project_id, **kwargs):
    if not kwargs:
        return False
    allowed = {
        "name", "code", "project_number", "description",
        "contractor_id", "contract_type_id", "area_id",
        "contract_number", "contract_amount",
        "contract_number_foreign", "contract_amount_foreign", "currency",
        "contract_start_date", "contract_end_date",
        "start_date", "planned_end_date", "actual_end_date",
        "duration_days",
        "status", "priority",
        "progress_percent", "physical_progress", "time_progress",
        "financial_progress", "financial_progress_rial",
        "financial_progress_foreign",
        "budget", "total_paid", "total_amendments_amount",
        "location", "province", "city", "latitude", "longitude",
        "tags", "notes",
        "is_active", "sort_order",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [project_id]
    connection = get_connection()
    try:
        connection.execute(
            f"UPDATE projects SET {set_clause} WHERE id = ?", values
        )
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        print(f"❌ خطا در به‌روزرسانی پروژه: {e}")
        return False
    finally:
        connection.close()


def delete_project(project_id):
    connection = get_connection()
    try:
        connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        return False
    finally:
        connection.close()


def search_projects(query, only_active=False):
    connection = get_connection()
    try:
        sql = """
            SELECT
                p.*,
                c.name AS contractor_name,
                ct.title AS contract_type_title,
                a.title AS area_title
            FROM projects p
            LEFT JOIN contractors c     ON c.id = p.contractor_id
            LEFT JOIN contract_types ct ON ct.id = p.contract_type_id
            LEFT JOIN areas a           ON a.id = p.area_id
            WHERE (
                p.name LIKE ? OR p.code LIKE ?
                OR p.contract_number LIKE ?
                OR p.project_number LIKE ?
                OR c.name LIKE ?
            )
        """
        params = [f"%{query}%"] * 5
        if only_active:
            sql += " AND p.is_active = 1"
        sql += " ORDER BY p.created_at DESC"
        rows = connection.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def get_projects_statistics():
    connection = get_connection()
    try:
        total = connection.execute(
            "SELECT COUNT(*) AS c FROM projects"
        ).fetchone()["c"]
        active = connection.execute(
            "SELECT COUNT(*) AS c FROM projects WHERE is_active = 1"
        ).fetchone()["c"]
        by_status = connection.execute("""
            SELECT status, COUNT(*) AS count
            FROM projects GROUP BY status
        """).fetchall()
        by_contract_type = connection.execute("""
            SELECT ct.title AS title, ct.color AS color,
                   COUNT(p.id) AS count
            FROM contract_types ct
            LEFT JOIN projects p ON p.contract_type_id = ct.id
            GROUP BY ct.id HAVING count > 0
            ORDER BY count DESC
        """).fetchall()
        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "by_status": [dict(r) for r in by_status],
            "by_contract_type": [dict(r) for r in by_contract_type],
        }
    finally:
        connection.close()


__all__ = [
    "create_project",
    "get_project",
    "get_project_by_code",
    "get_all_projects",
    "update_project",
    "delete_project",
    "search_projects",
    "get_projects_statistics",
]
