"""
Analytics Handlers - تحلیل‌ها
================================
★ نسخه Registry-based
"""
from datetime import datetime

from services.ai.registry import IntentRegistry
from services.ai.formatters import Formatters
from database.connection import get_connection
from helpers.date_helper import DateHelper


class AnalyticsHandlers:
    """تحلیل‌های پیشرفته"""

    @IntentRegistry.register(
        name="top_experts",
        patterns=[
            r"(پرمشغله|پرکار|فعال‌ترین|فعالترین|بهترین)",
            r"(کی|کدوم).{0,10}(بیشترین|بیشتر).{0,10}(سند|کار)",
            r"رتبه.{0,10}(کارشناس|همکار)",
        ],
        priority=88,
        confidence=0.9,
        description="پرمشغله‌ترین کارشناسان",
        admin_only=True,
    )
    @staticmethod
    def handle_top_experts(question, entities, user_id, is_admin):
        return AnalyticsHandlers._handle_top_experts(user_id, is_admin)

    @IntentRegistry.register(
        name="group_distribution",
        patterns=[
            r"(توزیع|نمودار|پخش|تفکیک).{0,10}(گروه|اسناد)",
            r"(هر گروه|گروه‌ها).{0,10}(چند|تعداد)",
        ],
        priority=85,
        confidence=0.85,
        description="توزیع اسناد بر اساس گروه",
    )
    @staticmethod
    def handle_group_distribution(question, entities, user_id, is_admin):
        return AnalyticsHandlers._handle_group_distribution(user_id, is_admin)

    @IntentRegistry.register(
        name="weekly_trend",
        patterns=[
            r"(روند|trend|تغییرات).{0,10}(هفتگی|هفته|اخیر)",
            r"(این هفته|هفته گذشته|هفت روز)",
            r"(آمار|وضعیت).{0,10}(هفتگی|هفته)",
        ],
        priority=85,
        confidence=0.85,
        description="روند هفتگی اسناد",
    )
    @staticmethod
    def handle_weekly_trend(question, entities, user_id, is_admin):
        return AnalyticsHandlers._handle_weekly_trend(user_id, is_admin)

    @IntentRegistry.register(
        name="deadline_alerts",
        patterns=[
            r"(هشدار|alert|نزدیک).{0,10}(مهلت|deadline|سر رسید)",
            r"(اسناد|کارها).{0,10}نزدیک.{0,10}(مهلت|سر رسید)",
        ],
        priority=87,
        confidence=0.88,
        description="هشدار مهلت",
    )
    @staticmethod
    def handle_deadline_alerts(question, entities, user_id, is_admin):
        return AnalyticsHandlers._handle_deadline_alerts(user_id, is_admin)

    # ============================================================
    # ★ پیاده‌سازی‌ها
    # ============================================================
    @classmethod
    def _handle_top_experts(cls, user_id, is_admin, limit=5):
        if not is_admin:
            return Formatters.error_response(
                "این گزارش فقط برای مدیران سیستم قابل دسترسی است.",
                suggestions=["کارهای من", "آمار کلی"]
            )

        conn = get_connection()
        try:
            rows = conn.execute("""
                SELECT u.id, u.full_name, u.username, COUNT(d.id) AS c
                FROM users u
                LEFT JOIN documents d ON d.user_id = u.id
                WHERE u.is_active = 1
                GROUP BY u.id
                HAVING c > 0
                ORDER BY c DESC LIMIT ?
            """, (limit,)).fetchall()

            if not rows:
                return Formatters.empty_response("داده‌ای موجود نیست.")

            items = [
                {"label": r["full_name"] or r["username"] or "بدون نام",
                 "value": r["c"]}
                for r in rows
            ]

            medals = [
                ("fa-medal", "#f59e0b"),
                ("fa-award", "#94a3b8"),
                ("fa-star", "#b45309"),
                ("fa-circle", "#3D8499"),
                ("fa-circle", "#3D8499"),
            ]

            lines = [
                '<i class="fa-solid fa-trophy" style="color:#f59e0b"></i> '
                '<strong>پرمشغله‌ترین کارشناسان</strong>\n'
            ]

            for i, it in enumerate(items):
                icon, color = medals[i] if i < len(medals) else ("fa-circle", "#3D8499")
                lines.append(
                    f'<i class="fa-solid {icon}" style="color:{color}"></i> '
                    f'<strong>{it["label"]}</strong>: '
                    f'<strong class="num-highlight">{it["value"]}</strong> سند'
                )

            return Formatters.response(
                "\n".join(lines), "stats", items,
                suggestions=["توزیع گروه‌ها", "روند هفتگی", "آمار کلی"]
            )
        finally:
            conn.close()

    @classmethod
    def _handle_group_distribution(cls, user_id, is_admin):
        conn = get_connection()
        try:
            sql = """
                SELECT g.title, g.color, COUNT(d.id) AS c
                FROM document_groups g
                LEFT JOIN documents d ON d.group_id = g.id
            """
            params = []
            if user_id and not is_admin:
                sql += " AND d.user_id = ?"
                params.append(user_id)
            sql += " GROUP BY g.id HAVING c > 0 ORDER BY c DESC"
            rows = conn.execute(sql, params).fetchall()

            if not rows:
                return Formatters.empty_response("هیچ گروهی با سند موجود نیست.")

            items = [
                {"label": r["title"], "value": r["c"],
                 "color": r["color"] or "#3D8499"}
                for r in rows
            ]

            scope = "شما" if not is_admin else "کل سیستم"
            total = sum(it["value"] for it in items)

            lines = [
                f'<i class="fa-solid fa-chart-pie" style="color:#667eea"></i> '
                f'<strong>توزیع اسناد بر اساس گروه</strong> '
                f'<span class="text-muted">({scope} — مجموع: </span>'
                f'<strong class="num-highlight">{total}</strong>'
                f'<span class="text-muted">)</span>\n'
            ]

            for it in items:
                color = it.get("color") or "#3D8499"
                lines.append(
                    f'<i class="fa-solid fa-folder-tree" style="color:{color}"></i> '
                    f'<strong>{it["label"]}</strong>: '
                    f'<strong class="num-highlight">{it["value"]}</strong>'
                )

            return Formatters.response(
                "\n".join(lines), "chart", items,
                suggestions=["نمودار کامل", "آمار کلی", "روند هفتگی"]
            )
        finally:
            conn.close()

    @classmethod
    def _handle_weekly_trend(cls, user_id, is_admin):
        conn = get_connection()
        try:
            sql = """
                SELECT DATE(created_at) AS day, COUNT(*) AS c
                FROM documents
                WHERE created_at >= date('now', '-7 days')
            """
            params = []
            if user_id and not is_admin:
                sql += " AND user_id = ?"
                params.append(user_id)
            sql += " GROUP BY DATE(created_at) ORDER BY day ASC"
            rows = conn.execute(sql, params).fetchall()

            if not rows:
                return Formatters.empty_response(
                    "در ۷ روز گذشته سند جدیدی ثبت نشده است."
                )

            items = []
            for r in rows:
                day_jalali = DateHelper.format_jalali(r["day"])
                items.append({
                    "label": day_jalali,
                    "value": r["c"],
                    "raw_date": r["day"],
                })

            total = sum(it["value"] for it in items)
            avg = round(total / len(items), 1) if items else 0
            best = max(items, key=lambda x: x["value"]) if items else None

            scope = "شما" if not is_admin else "کل سیستم"
            lines = [
                f'<i class="fa-solid fa-arrow-trend-up" style="color:#10b981"></i> '
                f'<strong>روند هفتگی اسناد</strong> '
                f'<span class="text-muted">({scope})</span>\n'
            ]

            for it in items:
                lines.append(
                    f'<i class="fa-solid fa-calendar-day" style="color:#3D8499"></i> '
                    f'{it["label"]}: '
                    f'<strong class="num-highlight">{it["value"]}</strong>'
                )

            lines.append("")
            lines.append(
                f'<i class="fa-solid fa-calculator" style="color:#667eea"></i> '
                f'مجموع: <strong>{total}</strong> | '
                f'میانگین: <strong>{avg}</strong>'
            )

            if best:
                lines.append(
                    f'<i class="fa-solid fa-crown" style="color:#f59e0b"></i> '
                    f'بیشترین: <strong>{best["label"]}</strong> '
                    f'با <strong>{best["value"]}</strong> سند'
                )

            return Formatters.response(
                "\n".join(lines), "chart", items,
                suggestions=["روند ماهانه", "آمار کلی", "پرمشغله‌ترین کارشناس کیست؟"],
                meta={"total": total, "average": avg}
            )
        finally:
            conn.close()

    @classmethod
    def _handle_deadline_alerts(cls, user_id, is_admin):
        today_gregorian = datetime.now().strftime("%Y/%m/%d")

        conn = get_connection()
        try:
            sql = """
                SELECT d.id, d.subject, d.code_dfc, d.deadline,
                       d.project_name, d.contractor,
                       s.title AS status_title, s.color AS status_color
                FROM documents d
                LEFT JOIN document_statuses s ON s.id = d.status_id
                WHERE s.code = 'in_progress'
                  AND d.deadline IS NOT NULL
                  AND d.deadline != ''
                  AND d.deadline >= ?
            """
            params = [today_gregorian]
            if user_id and not is_admin:
                sql += " AND d.user_id = ?"
                params.append(user_id)
            sql += " ORDER BY d.deadline ASC LIMIT 15"

            rows = conn.execute(sql, params).fetchall()
            docs = [dict(r) for r in rows]
        finally:
            conn.close()

        if not docs:
            return Formatters.response(
                '<i class="fa-solid fa-circle-check" style="color:#10b981"></i> '
                '<strong>هیچ سند نزدیک به مهلتی ندارید.</strong>',
                "list", [],
                suggestions=["کارهای من", "آمار کلی", "روند هفتگی"]
            )

        scope = "شما" if not is_admin else "سیستم"
        return Formatters.doc_list(
            docs, f"اسناد نزدیک به مهلت ({scope})",
            show_deadline=True, show_status=False,
        )