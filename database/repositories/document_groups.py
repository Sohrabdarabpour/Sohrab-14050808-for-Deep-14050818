"""عملیات دیتابیس گروه/زیرگروه سند — خوانش‌های مورد نیاز مهلت پاسخ."""

from database.connection import get_connection


def get_days_review(group_id=None, subgroup_id=None):
    """(روزهای بررسی گروه، روزهای بررسی زیرگروه)."""
    group_days = subgroup_days = 0

    connection = get_connection()
    try:
        if subgroup_id:
            row = connection.execute(
                "SELECT days_review FROM document_subgroups WHERE id = ?",
                (subgroup_id,),
            ).fetchone()
            subgroup_days = row["days_review"] if row else 0

        if group_id:
            row = connection.execute(
                "SELECT days_review FROM document_groups WHERE id = ?",
                (group_id,),
            ).fetchone()
            group_days = row["days_review"] if row else 0
    finally:
        connection.close()

    return group_days or 0, subgroup_days or 0


def list_groups_with_sla():
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT id, title, code, COALESCE(days_review, 0) AS days_review
            FROM document_groups
            WHERE is_active = 1
            ORDER BY sort_order, title
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def list_subgroups_with_sla(group_id=None):
    connection = get_connection()
    try:
        if group_id:
            rows = connection.execute(
                """
                SELECT sg.id, sg.title, sg.code,
                       COALESCE(sg.days_review, 0) AS days_review
                FROM document_subgroups sg
                INNER JOIN group_subgroups gs ON gs.subgroup_id = sg.id
                WHERE gs.group_id = ? AND sg.is_active = 1
                ORDER BY sg.sort_order, sg.title
                """,
                (group_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, title, code, COALESCE(days_review, 0) AS days_review
                FROM document_subgroups
                WHERE is_active = 1
                ORDER BY sort_order, title
                """
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
