"""
Status Handlers - شمارش وضعیت‌ها
==================================
★ هر intent با دکوراتور ثبت می‌شه
"""
from services.ai.registry import IntentRegistry
from services.ai.formatters import Formatters
from services.ai.cache import cached
from database.connection import get_connection


class StatusHandlers:

    # ============================================================
    # ★ آیکون‌های هر وضعیت
    # ============================================================
    STATUS_ICONS = {
        "in_progress": {"icon": "fa-list-check", "color": "#3D8499"},
        "completed": {"icon": "fa-circle-check", "color": "#10b981"},
        "stopped": {"icon": "fa-circle-pause", "color": "#6366f1"},
        "deleted": {"icon": "fa-circle-xmark", "color": "#ef4444"},
        "informational": {"icon": "fa-circle-info", "color": "#f59e0b"},
    }

    # ============================================================
    # ★ Helper: status_id از code
    # ============================================================
    @staticmethod
    @cached(ttl=30)
    def _status_id(code):
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT id FROM document_statuses WHERE code = ?",
                (code,)
            ).fetchone()
            return row["id"] if row else None
        finally:
            conn.close()

    # ============================================================
    # ★ Helper: شمارش
    # ============================================================
    @classmethod
    def count_by_status(cls, status_code, user_id=None, is_admin=False):
        sid = cls._status_id(status_code)
        if sid is None:
            return 0
        conn = get_connection()
        try:
            sql = "SELECT COUNT(*) AS c FROM documents WHERE status_id = ?"
            params = [sid]
            if user_id and not is_admin:
                sql += " AND user_id = ?"
                params.append(user_id)
            return conn.execute(sql, params).fetchone()["c"]
        finally:
            conn.close()

    # ============================================================
    # ★ ثبت intentها با دکوراتور
    # ============================================================

    @IntentRegistry.register(
        name="count_in_progress",
        patterns=[
            r"(چند|تعداد|شمار)\s*(تا|مورد)?\s*(سند|کار|پرونده|مورد)?\s*(در حال بررسی|جاری|باز|ناتمام|در جریان|در دست)",
            r"(در حال بررسی|جاری|باز|ناتمام).{0,20}(چند|تعداد)",
            r"(چند|تعداد).{0,20}(در حال بررسی|جاری|باز)",
        ],
        priority=90,
        confidence=0.95,
        description="شمارش اسناد در حال بررسی",
        keywords=["در حال بررسی", "جاری", "باز"],
    )
    @staticmethod
    def handle_count_in_progress(question, entities, user_id, is_admin):
        return StatusHandlers._generic_count(
            "in_progress", "در حال بررسی", user_id, is_admin
        )

    @IntentRegistry.register(
        name="count_completed",
        patterns=[
            r"(چند|تعداد)\s*(تا|مورد)?\s*(سند|کار|پرونده)?\s*(تکمیل|تمام|بسته|خاتمه|انجام)",
            r"(تکمیل|تمام|بسته).{0,20}(چند|تعداد)",
            r"(چند|تعداد).{0,20}(تکمیل|تمام|بسته)",
        ],
        priority=90,
        confidence=0.95,
        description="شمارش اسناد تکمیل شده",
    )
    @staticmethod
    def handle_count_completed(question, entities, user_id, is_admin):
        return StatusHandlers._generic_count(
            "completed", "تکمیل شده", user_id, is_admin
        )

    @IntentRegistry.register(
        name="count_stopped",
        patterns=[r"(چند|تعداد).{0,20}(متوقف|توقف|نگه داشته)"],
        priority=90,
        confidence=0.9,
        description="شمارش اسناد متوقف شده",
    )
    @staticmethod
    def handle_count_stopped(question, entities, user_id, is_admin):
        return StatusHandlers._generic_count(
            "stopped", "متوقف شده", user_id, is_admin
        )

    @IntentRegistry.register(
        name="count_deleted",
        patterns=[r"(چند|تعداد).{0,20}(ابطال|حذف|کنسل|لغو)"],
        priority=90,
        confidence=0.9,
        description="شمارش اسناد ابطال شده",
    )
    @staticmethod
    def handle_count_deleted(question, entities, user_id, is_admin):
        return StatusHandlers._generic_count(
            "deleted", "ابطال شده", user_id, is_admin
        )

    @IntentRegistry.register(
        name="count_informational",
        patterns=[r"(چند|تعداد).{0,20}(اطلاع|آگاهی)"],
        priority=90,
        confidence=0.9,
        description="شمارش اسناد جهت اطلاع",
    )
    @staticmethod
    def handle_count_informational(question, entities, user_id, is_admin):
        return StatusHandlers._generic_count(
            "informational", "جهت اطلاع", user_id, is_admin
        )

    @IntentRegistry.register(
        name="count_all",
        patterns=[
            r"(آمار|تعداد کل|کل|همه)\s*(اسناد|کار|پرونده|مورد)?",
            r"(چند|تعداد)\s*(سند|کار|پرونده)\s*(داریم|دارم|هست|وجود|موجود)",
            r"(چقدر|چند)\s*(سند|کار)\s*(کل)?\s*(دارم|هست)",
        ],
        priority=85,
        confidence=0.85,
        description="آمار کلی اسناد",
    )
    @staticmethod
    def handle_count_all(question, entities, user_id, is_admin):
        return StatusHandlers._handle_all(user_id, is_admin)

    # ============================================================
    # ★ پیاده‌سازی مشترک
    # ============================================================
    @classmethod
    def _generic_count(cls, status_code, status_title, user_id, is_admin):
        count = cls.count_by_status(status_code, user_id, is_admin)
        scope = "کارتابل شما" if not is_admin else "کل سیستم"

        meta = cls.STATUS_ICONS.get(status_code, {
            "icon": "fa-circle-dot",
            "color": "#3D8499",
        })

        answer = (
            f'<i class="fa-solid {meta["icon"]}" '
            f'style="color:{meta["color"]}"></i> '
            f'در حال حاضر <strong class="num-highlight">{count}</strong> '
            f'سند «<strong>{status_title}</strong>» '
            f'در <strong>{scope}</strong> وجود دارد.'
        )

        suggestions = []
        if count > 0:
            suggestions = [f"لیست {status_title}", "آمار کلی اسناد"]
        else:
            suggestions = ["اسناد در حال بررسی", "کارهای من"]

        return Formatters.response(
            answer,
            "count",
            [{"status": status_code, "count": count}],
            suggestions=suggestions,
        )

    @classmethod
    def _handle_all(cls, user_id, is_admin):
        conn = get_connection()
        try:
            sql = "SELECT COUNT(*) AS c FROM documents WHERE 1=1"
            params = []
            if user_id and not is_admin:
                sql += " AND user_id = ?"
                params.append(user_id)
            total = conn.execute(sql, params).fetchone()["c"]

            sql2 = """
                SELECT s.title, s.code, s.color, COUNT(d.id) AS c
                FROM document_statuses s
                LEFT JOIN documents d ON d.status_id = s.id
            """
            if user_id and not is_admin:
                sql2 += " AND d.user_id = ?"
            sql2 += " GROUP BY s.id ORDER BY s.sort_order"

            rows = conn.execute(
                sql2, params if user_id and not is_admin else []
            ).fetchall()

            items = [
                {"label": r["title"], "value": r["c"],
                 "color": r["color"], "code": r["code"]}
                for r in rows
            ]

            scope_text = "کارتابل شما" if not is_admin else "کل سیستم"
            lines = [
                f'<i class="fa-solid fa-chart-pie" style="color:#667eea"></i> '
                f'<strong>آمار کلی اسناد</strong> '
                f'<span class="text-muted">({scope_text} — مجموع: </span>'
                f'<strong class="num-highlight">{total}</strong>'
                f'<span class="text-muted">)</span>\n'
            ]

            for it in items:
                icon_data = cls.STATUS_ICONS.get(it["code"], {
                    "icon": "fa-circle-dot",
                    "color": it.get("color", "#3D8499"),
                })
                lines.append(
                    f'<i class="fa-solid {icon_data["icon"]}" '
                    f'style="color:{icon_data["color"]}"></i> '
                    f'{it["label"]}: <strong>{it["value"]}</strong>'
                )

            return Formatters.response(
                "\n".join(lines),
                "stats",
                items,
                suggestions=["نمودار آماری", "اسناد در حال بررسی", "اسناد دیرکرد"],
                meta={"total": total},
            )
        finally:
            conn.close()