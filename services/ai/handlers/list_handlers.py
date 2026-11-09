"""
List Handlers - لیست اسناد
============================
"""
from datetime import datetime

from services.ai.registry import IntentRegistry
from services.ai.formatters import Formatters
from services.ai.handlers.status_handlers import StatusHandlers
from database.connection import get_connection
from helpers.date_helper import DateHelper


class ListHandlers:

    # ============================================================
    # ★ Helper: لیست بر اساس وضعیت
    # ============================================================
    @classmethod
    def _list_by_status(cls, status_code, user_id, is_admin, limit=20):
        sid = StatusHandlers._status_id(status_code)
        if sid is None:
            return []

        conn = get_connection()
        try:
            sql = """
                SELECT d.id, d.subject, d.code_dfc, d.deadline,
                       d.date_received, d.date_referral,
                       d.project_name, d.contractor,
                       s.title AS status_title, s.color AS status_color
                FROM documents d
                LEFT JOIN document_statuses s ON s.id = d.status_id
                WHERE d.status_id = ?
            """
            params = [sid]
            if user_id and not is_admin:
                sql += " AND d.user_id = ?"
                params.append(user_id)
            sql += " ORDER BY d.id DESC LIMIT ?"
            params.append(limit)
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    # ============================================================
    # ★ ثبت intentها
    # ============================================================

    @IntentRegistry.register(
        name="list_in_progress",
        patterns=[
            r"(لیست|نشون|نمایش|بگو|بهم بگو|بیار).{0,15}(در حال بررسی|جاری|باز)",
            r"(در حال بررسی|جاری|باز).{0,10}(چیا|چی|چیه|کدوم|لیست)",
        ],
        priority=88,
        confidence=0.92,
        description="لیست اسناد در حال بررسی",
    )
    @staticmethod
    def handle_list_in_progress(question, entities, user_id, is_admin):
        docs = ListHandlers._list_by_status("in_progress", user_id, is_admin)
        scope = "شما" if not is_admin else "سیستم"
        return Formatters.doc_list(
            docs,
            f"اسناد در حال بررسی ({scope})",
            show_deadline=True,
            show_status=False,
        )

    @IntentRegistry.register(
        name="list_completed",
        patterns=[
            r"(لیست|نشون|نمایش|بگو|بیار).{0,15}(تکمیل|تمام|بسته)",
            r"(تکمیل|تمام).{0,10}(چیا|چی|چیه|کدوم|لیست)",
        ],
        priority=88,
        confidence=0.92,
        description="لیست اسناد تکمیل شده",
    )
    @staticmethod
    def handle_list_completed(question, entities, user_id, is_admin):
        docs = ListHandlers._list_by_status("completed", user_id, is_admin)
        scope = "شما" if not is_admin else "سیستم"
        return Formatters.doc_list(
            docs, f"اسناد تکمیل شده ({scope})",
            show_deadline=False,
            show_status=False,
        )

    @IntentRegistry.register(
        name="list_my_documents",
        patterns=[
            r"(کارها|اسناد|پرونده)‌?\s*(من|خودم)",
            r"کارهای?\s*من",
            r"من\s*(چی|چیا|چیه)\s*(دارم|دارم?)",
            r"اسناد\s*من\s*(چی|چیا)",
            r"(نشون|بگو|بیار).{0,10}(کارها|اسناد)‌?\s*من",
        ],
        priority=92,
        confidence=0.95,
        description="اسناد کاربر فعلی",
    )
    @staticmethod
    def handle_my_documents(question, entities, user_id, is_admin):
        return ListHandlers._handle_my_documents(user_id, is_admin)

    @IntentRegistry.register(
        name="list_overdue",
        patterns=[
            r"(دیرکرد|دیرکرده|گذشت|گذشته|عقب افتاده)",
            r"(مهلت).{0,10}(گذشت|سر رسید|رسیده)",
            r"(کارها|اسناد).{0,10}(عقب|دیر)",
            r"deadline",
            r"سر\s*رسید",
        ],
        priority=88,
        confidence=0.9,
        description="اسناد دیرکرد",
    )
    @staticmethod
    def handle_list_overdue(question, entities, user_id, is_admin):
        return ListHandlers._handle_overdue(user_id, is_admin)

    @IntentRegistry.register(
        name="list_today",
        patterns=[
            r"(امروز|تحویل امروز|مهلت امروز)",
            r"(کارها|اسناد).{0,10}امروز",
        ],
        priority=85,
        confidence=0.85,
        description="اسناد امروز",
    )
    @staticmethod
    def handle_list_today(question, entities, user_id, is_admin):
        return ListHandlers._handle_today(user_id, is_admin)

    # ============================================================
    # ★ پیاده‌سازی‌ها
    # ============================================================
    @classmethod
    def _handle_my_documents(cls, user_id, is_admin):
        if not user_id:
            return Formatters.error_response(
                "ابتدا وارد سیستم شوید.",
                suggestions=["راهنما"]
            )
        conn = get_connection()
        try:
            sql = """
                SELECT d.id, d.subject, d.code_dfc, d.deadline,
                       d.date_received, d.project_name, d.contractor,
                       s.title AS status_title, s.color AS status_color
                FROM documents d
                LEFT JOIN document_statuses s ON s.id = d.status_id
                WHERE d.user_id = ?
                ORDER BY d.id DESC LIMIT 20
            """
            rows = conn.execute(sql, (user_id,)).fetchall()
            docs = [dict(r) for r in rows]
        finally:
            conn.close()

        return Formatters.doc_list(
            docs, "اسناد شما",
            show_deadline=True,
            show_status=True,
        )

    @classmethod
    def _handle_overdue(cls, user_id, is_admin):
        sid = StatusHandlers._status_id("in_progress")
        if sid is None:
            return Formatters.error_response("وضعیت تعریف نشده.")

        today_gregorian = datetime.now().strftime("%Y/%m/%d")

        conn = get_connection()
        try:
            sql = """
                SELECT d.id, d.subject, d.code_dfc, d.deadline,
                       d.project_name, d.contractor,
                       s.title AS status_title, s.color AS status_color
                FROM documents d
                LEFT JOIN document_statuses s ON s.id = d.status_id
                WHERE d.status_id = ?
                  AND d.deadline IS NOT NULL
                  AND d.deadline != ''
                  AND d.deadline < ?
            """
            params = [sid, today_gregorian]
            if user_id and not is_admin:
                sql += " AND d.user_id = ?"
                params.append(user_id)
            sql += " ORDER BY d.deadline ASC LIMIT 30"
            rows = conn.execute(sql, params).fetchall()
            docs = [dict(r) for r in rows]
        finally:
            conn.close()

        if not docs:
            return Formatters.response(
                '<i class="fa-solid fa-champagne-glasses" '
                'style="color:#10b981"></i> '
                '<strong>هیچ سند دیرکردی ندارید!</strong>',
                "list", [],
                suggestions=["کارهای من", "آمار کلی"]
            )

        scope = "شما" if not is_admin else "سیستم"
        return Formatters.doc_list(
            docs, f"اسناد دیرکرد ({scope})",
            show_deadline=True, show_status=False,
        )

    @classmethod
    def _handle_today(cls, user_id, is_admin):
        today_gregorian = datetime.now().strftime("%Y/%m/%d")
        today_jalali = DateHelper.format_jalali(today_gregorian)

        conn = get_connection()
        try:
            sql = """
                SELECT d.id, d.subject, d.code_dfc, d.deadline,
                       d.project_name, d.contractor,
                       s.title AS status_title, s.color AS status_color
                FROM documents d
                LEFT JOIN document_statuses s ON s.id = d.status_id
                WHERE d.deadline LIKE ?
            """
            params = [f"%{today_gregorian}%"]
            if user_id and not is_admin:
                sql += " AND d.user_id = ?"
                params.append(user_id)
            sql += " ORDER BY d.id DESC"
            rows = conn.execute(sql, params).fetchall()
            docs = [dict(r) for r in rows]
        finally:
            conn.close()

        if not docs:
            return Formatters.response(
                f'<i class="fa-solid fa-inbox" style="color:#94a3b8"></i> '
                f'<strong>امروز ({today_jalali}) سندی برای تحویل ندارید.</strong>',
                "list", [],
                suggestions=["کارهای من", "اسناد دیرکرد", "آمار کلی"]
            )

        return Formatters.doc_list(
            docs, f"اسناد امروز ({today_jalali})",
            show_deadline=False, show_status=True,
        )