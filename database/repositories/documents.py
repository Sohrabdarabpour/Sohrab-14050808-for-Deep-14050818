"""عملیات دیتابیس — اسناد

این فایل بخشی از تفکیک ماژول بزرگ init_db.py است؛ برای اصلاح هر موضوع
فقط همین فایل را باز کنید.
"""

import os
from datetime import datetime

from config import Config

from ..connection import get_connection
from helpers.date_helper import now_tehran, now_tehran_str


def get_document(doc_id):
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT d.*,
                   s.title AS status_title,
                   s.code AS status_code,
                   s.color AS status_color,
                   u.full_name AS user_full_name,
                   dep.title AS department_title
            FROM documents d
            LEFT JOIN document_statuses s ON s.id = d.status_id
            LEFT JOIN users u ON u.id = d.user_id
            LEFT JOIN departments dep ON dep.id = d.department_id
            WHERE d.id = ?
        """, (doc_id,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_document_events(document_id):
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT e.*,
                   n.content AS note_content,
                   u.full_name AS user_full_name,
                   u.username AS user_username,
                   u.avatar AS user_avatar,
                   u.role AS user_role,
                   fs.title AS from_step_title,
                   ts.title AS to_step_title
            FROM note_events e
            INNER JOIN document_notes n ON n.id = e.note_id
            LEFT JOIN users u ON u.id = e.user_id
            LEFT JOIN workflow_steps fs ON fs.id = e.from_step_id
            LEFT JOIN workflow_steps ts ON ts.id = e.to_step_id
            WHERE n.document_id = ?
            ORDER BY e.created_at ASC, e.id ASC
        """, (document_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        connection.close()


def get_department_supervisor(department_id):
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT u.id, u.full_name, u.username, u.avatar
            FROM departments d
            JOIN users u ON u.id = d.supervisor_id
            WHERE d.id = ?
        """, (department_id,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_sla_inputs(document_id):
    """ورودی‌های محاسبهٔ مهلت: گروه/زیرگروه و تاریخ دریافت."""
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT id, group_id, subgroup_id, date_received
            FROM documents WHERE id = ?
            """,
            (document_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def update_sla(document_id, sla_days, sla_source, response_due_date):
    """ذخیرهٔ مهلت محاسبه‌شده روی سند."""
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            UPDATE documents
            SET sla_days = ?, sla_source = ?, response_due_date = ?
            WHERE id = ?
            """,
            (sla_days, sla_source, response_due_date, document_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


__all__ = [
    "get_document",
    "get_document_events",
    "get_department_supervisor",
    "get_sla_inputs",
    "update_sla",
]
