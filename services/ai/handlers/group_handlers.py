"""
Group Handlers - گروه‌ها و زیرگروه‌های سند
=============================================
★ نسخه Registry-based
★ استفاده از DocumentGroupService و DocumentSubgroupService
"""
from html import escape

from services.ai.registry import IntentRegistry
from services.ai.formatters import Formatters
from database.connection import get_connection

# ★ importهای درست (بر اساس ساختار واقعی پروژه)
from services.document_group.group_service import DocumentGroupService
from services.document_group.subgroup_service import DocumentSubgroupService


class GroupHandlers:
    """گروه‌ها و زیرگروه‌های سند"""

    # ============================================================
    # ★ ۱. تعداد گروه‌ها
    # ============================================================
    @IntentRegistry.register(
        name="count_groups",
        patterns=[
            r"(چند|تعداد|شمار)\s*(گروه|گروه‌های)\s*(سند|اسناد)?",
            r"(چند|تعداد)\s*(تا|مورد)?\s*گروه\s*(سند)?\s*(داریم|دارم|هست)",
            r"(آمار|وضعیت)\s*(گروه‌ها|گروه)",
        ],
        priority=88,
        confidence=0.9,
        description="شمارش گروه‌های سند",
    )
    @staticmethod
    def handle_count_groups(question, entities, user_id, is_admin):
        try:
            stats = DocumentGroupService.get_stats()
        except Exception as e:
            return Formatters.error_response(
                f"خطا در دریافت آمار گروه‌ها: {str(e)}"
            )

        total = stats.get("total_groups", 0)
        active = stats.get("active_groups", 0)
        inactive = stats.get("inactive_groups", 0)

        answer = (
            f'<i class="fa-solid fa-folder-tree" style="color:#3D8499"></i> '
            f'در حال حاضر <strong class="num-highlight">{total}</strong> '
            f'گروه سند در سیستم وجود دارد.\n\n'
            f'<i class="fa-solid fa-circle-check" style="color:#10b981"></i> '
            f'فعال: <strong>{active}</strong>\n'
            f'<i class="fa-solid fa-circle-pause" style="color:#94a3b8"></i> '
            f'غیرفعال: <strong>{inactive}</strong>'
        )

        return Formatters.response(
            answer,
            "count",
            [{"total": total, "active": active, "inactive": inactive}],
            suggestions=["لیست گروه‌ها", "توزیع گروه‌ها", "آمار کلی"],
        )

    # ============================================================
    # ★ ۲. لیست گروه‌ها
    # ============================================================
    @IntentRegistry.register(
        name="list_groups",
        patterns=[
            r"(لیست|نشون|نمایش|بگو|بیار)\s*(گروه|گروه‌های)\s*(سند|اسناد)?",
            r"گروه‌های\s*سند\s*(چیا|چی|چیه|کدوم)",
            r"(همه|کل)\s*گروه‌ها",
        ],
        priority=88,
        confidence=0.9,
        description="لیست گروه‌های سند",
    )
    @staticmethod
    def handle_list_groups(question, entities, user_id, is_admin):
        try:
            groups = DocumentGroupService.get_all()
        except Exception as e:
            return Formatters.error_response(
                f"خطا در دریافت گروه‌ها: {str(e)}"
            )

        if not groups:
            return Formatters.empty_response("هیچ گروه سندی تعریف نشده است.")

        lines = [
            f'<i class="fa-solid fa-folder-tree" style="color:#3D8499"></i> '
            f'<strong>گروه‌های سند</strong> '
            f'<span class="text-muted">({len(groups)} مورد)</span>\n'
        ]

        for i, g in enumerate(groups, 1):
            title = escape(g.get("title") or "بدون نام")
            code = escape(g.get("code") or "-")
            color = g.get("color") or "#3D8499"
            subgroups = g.get("subgroups_count", 0)
            is_active = g.get("is_active", 1)

            status_icon = (
                f'<i class="fa-solid fa-circle-check" '
                f'style="color:#10b981"></i>'
                if is_active
                else f'<i class="fa-solid fa-circle-pause" '
                     f'style="color:#94a3b8"></i>'
            )

            lines.append(
                f'{status_icon} '
                f'<i class="fa-solid fa-folder" style="color:{color}"></i> '
                f'<strong>{title}</strong> '
                f'<span class="text-muted">[{code}]</span> '
                f'— زیرگروه: <strong>{subgroups}</strong>'
            )

        return Formatters.response(
            "\n".join(lines),
            "list",
            groups,
            suggestions=["توزیع گروه‌ها", "زیرگروه‌ها", "آمار کلی"],
        )

    # ============================================================
    # ★ ۳. تعداد زیرگروه‌ها
    # ============================================================
    @IntentRegistry.register(
        name="count_subgroups",
        patterns=[
            r"(چند|تعداد|شمار)\s*(زیرگروه|زیرمجموعه|زیر شاخه)\s*(سند|اسناد)?",
            r"(چند|تعداد)\s*(تا|مورد)?\s*زیرگروه\s*(داریم|دارم|هست)",
        ],
        priority=88,
        confidence=0.9,
        description="شمارش زیرگروه‌های سند",
    )
    @staticmethod
    def handle_count_subgroups(question, entities, user_id, is_admin):
        try:
            subgroups = DocumentSubgroupService.get_all()
        except Exception as e:
            return Formatters.error_response(
                f"خطا در دریافت زیرگروه‌ها: {str(e)}"
            )

        total = len(subgroups)
        active = sum(1 for s in subgroups if s.get("is_active"))

        answer = (
            f'<i class="fa-solid fa-sitemap" style="color:#3D8499"></i> '
            f'در حال حاضر <strong class="num-highlight">{total}</strong> '
            f'زیرگروه سند در سیستم وجود دارد.\n\n'
            f'<i class="fa-solid fa-circle-check" style="color:#10b981"></i> '
            f'فعال: <strong>{active}</strong>\n'
            f'<i class="fa-solid fa-circle-pause" style="color:#94a3b8"></i> '
            f'غیرفعال: <strong>{total - active}</strong>'
        )

        return Formatters.response(
            answer,
            "count",
            [{"total": total, "active": active}],
            suggestions=["لیست زیرگروه‌ها", "لیست گروه‌ها", "آمار کلی"],
        )

    # ============================================================
    # ★ ۴. لیست زیرگروه‌ها
    # ============================================================
    @IntentRegistry.register(
        name="list_subgroups",
        patterns=[
            r"(لیست|نشون|نمایش|بگو|بیار)\s*(زیرگروه|زیرمجموعه|زیر شاخه)\s*(سند|اسناد)?",
            r"زیرگروه(?:‌|\s)?های\s*سند\s*(چیا|چی|چیه|کدوم)",
        ],
        priority=87,
        confidence=0.88,
        description="لیست زیرگروه‌های سند",
    )
    @staticmethod
    def handle_list_subgroups(question, entities, user_id, is_admin):
        try:
            subgroups = DocumentSubgroupService.get_all()
        except Exception as e:
            return Formatters.error_response(
                f"خطا در دریافت زیرگروه‌ها: {str(e)}"
            )

        if not subgroups:
            return Formatters.empty_response("هیچ زیرگروه سندی تعریف نشده است.")

        lines = [
            f'<i class="fa-solid fa-sitemap" style="color:#3D8499"></i> '
            f'<strong>زیرگروه‌های سند</strong> '
            f'<span class="text-muted">({len(subgroups)} مورد)</span>\n'
        ]

        # گروه‌بندی بر اساس گروه والد
        grouped = {}
        for s in subgroups:
            gtitle = s.get("group_title") or "بدون گروه"
            grouped.setdefault(gtitle, []).append(s)

        for gtitle, items in grouped.items():
            lines.append(
                f'\n<i class="fa-solid fa-folder-tree" '
                f'style="color:#667eea"></i> '
                f'<strong>{escape(gtitle)}</strong> '
                f'<span class="text-muted">({len(items)} زیرگروه)</span>'
            )
            for s in items:
                title = escape(s.get("title") or "بدون نام")
                days = s.get("days_review", 0)
                dept = s.get("department_title")
                dept_text = (
                    f' — دپارتمان: {escape(dept)}' if dept else ''
                )
                lines.append(
                    f'&nbsp;&nbsp;<i class="fa-solid fa-circle-dot" '
                    f'style="color:#3D8499;font-size:8px"></i> '
                    f'{title} '
                    f'<span class="text-muted">({days} روز{dept_text})</span>'
                )

        return Formatters.response(
            "\n".join(lines),
            "list",
            subgroups,
            suggestions=["لیست گروه‌ها", "توزیع گروه‌ها", "آمار کلی"],
        )

    # ============================================================
    # ★ ۵. زیرگروه‌های یک گروه خاص
    # ============================================================
    @IntentRegistry.register(
        name="subgroups_of_group",
        patterns=[
            r"زیرگروه(?:‌|\s)?های?\s*(?:گروه\s*)?(?P<group>[\u0600-\u06FF\w\s&]{2,30}?)\s*(چیا|چی|چیه|کدوم|چند)",
            r"(چند|چیا)\s*زیرگروه\s*(?:برای|در)\s*گروه\s+(?P<group>[\u0600-\u06FF\w\s&]{2,30})",
            r"گروه\s+(?P<group>[\u0600-\u06FF\w\s&]{2,30}?)\s*(چند|چیا)\s*زیرگروه",
        ],
        priority=90,
        confidence=0.9,
        description="زیرگروه‌های یک گروه خاص",
    )
    @staticmethod
    def handle_subgroups_of_group(question, entities, user_id, is_admin):
        group_name = (entities.get("group") or "").strip()
        if not group_name:
            return Formatters.error_response("نام گروه مشخص نشد.")

        try:
            # ★ پیدا کردن گروه با نام مشابه
            groups = DocumentGroupService.get_all(search=group_name)
        except Exception as e:
            return Formatters.error_response(
                f"خطا در جستجوی گروه: {str(e)}"
            )

        if not groups:
            return Formatters.error_response(
                f'گروهی با نام «{escape(group_name)}» پیدا نشد.',
                suggestions=["لیست گروه‌ها", "آمار کلی"],
            )

        # ★ اولین گروه مطابق
        group = groups[0]
        group_id = group["id"]
        group_title = escape(group.get("title") or "")

        try:
            subgroups = DocumentSubgroupService.get_all(
                group_id=group_id, active_only=True
            )
        except Exception as e:
            return Formatters.error_response(
                f"خطا در دریافت زیرگروه‌ها: {str(e)}"
            )

        if not subgroups:
            return Formatters.response(
                f'<i class="fa-solid fa-folder-open" '
                f'style="color:#94a3b8"></i> '
                f'گروه «<strong>{group_title}</strong>» '
                f'هیچ زیرگروه فعالی ندارد.',
                "list",
                [],
                suggestions=["لیست گروه‌ها", "زیرگروه‌ها"],
            )

        lines = [
            f'<i class="fa-solid fa-sitemap" style="color:#3D8499"></i> '
            f'زیرگروه‌های گروه «<strong>{group_title}</strong>» '
            f'<span class="text-muted">({len(subgroups)} مورد)</span>\n'
        ]

        for i, s in enumerate(subgroups, 1):
            title = escape(s.get("title") or "بدون نام")
            code = escape(s.get("code") or "-")
            days = s.get("days_review", 0)
            dept = s.get("department_title")
            dept_text = (
                f' | دپارتمان: {escape(dept)}' if dept else ''
            )

            lines.append(
                f'<span class="doc-num">{i}.</span> '
                f'<i class="fa-solid fa-circle-dot" '
                f'style="color:#3D8499"></i> '
                f'<strong>{title}</strong> '
                f'<span class="text-muted">[{code}'
                f' • {days} روز{dept_text}]</span>'
            )

        return Formatters.response(
            "\n".join(lines),
            "list",
            subgroups,
            suggestions=["لیست گروه‌ها", "توزیع گروه‌ها", "آمار کلی"],
        )

    # ============================================================
    # ★ ۶. توزیع اسناد بر اساس گروه
    # ============================================================
    @IntentRegistry.register(
        name="group_document_distribution",
        patterns=[
            r"(توزیع|پخش|تفکیک)\s*اسناد\s*(بر اساس|در)?\s*گروه",
            r"هر گروه\s*(چند|تعداد)\s*سند",
            r"گروه(?:‌|\s)?ها\s*(چند|تعداد)\s*سند\s*دارن",
        ],
        priority=87,
        confidence=0.9,
        description="توزیع اسناد بر اساس گروه",
    )
    @staticmethod
    def handle_group_document_distribution(question, entities, user_id, is_admin):
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

        except Exception as e:
            return Formatters.error_response(
                f"خطا در دریافت توزیع: {str(e)}"
            )
        finally:
            conn.close()

        if not rows:
            return Formatters.empty_response(
                "هیچ سندی به گروه‌ها متصل نیست."
            )

        items = [
            {
                "label": r["title"],
                "value": r["c"],
                "color": r["color"] or "#3D8499",
            }
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
                f'<i class="fa-solid fa-folder" style="color:{color}"></i> '
                f'<strong>{escape(it["label"])}</strong>: '
                f'<strong class="num-highlight">{it["value"]}</strong> سند'
            )

        return Formatters.response(
            "\n".join(lines),
            "chart",
            items,
            suggestions=["نمودار کامل", "آمار کلی", "لیست گروه‌ها"],
        )

    # ============================================================
    # ★ ۷. جستجوی گروه با نام
    # ============================================================
    @IntentRegistry.register(
        name="find_group",
        patterns=[
            r"(پیدا کن|بگرد|جستجو)\s*گروه\s+(?P<group>[\u0600-\u06FF\w\s&]{2,30})",
            r"گروه\s+(?P<group>[\u0600-\u06FF\w\s&]{2,30}?)\s*(هست|وجود داره|داریم)",
        ],
        priority=85,
        confidence=0.88,
        description="جستجوی گروه با نام",
    )
    @staticmethod
    def handle_find_group(question, entities, user_id, is_admin):
        group_name = (entities.get("group") or "").strip()
        if not group_name:
            return Formatters.error_response("نام گروه مشخص نشد.")

        try:
            groups = DocumentGroupService.get_all(search=group_name)
        except Exception as e:
            return Formatters.error_response(
                f"خطا در جستجو: {str(e)}"
            )

        if not groups:
            return Formatters.error_response(
                f'گروهی با نام «{escape(group_name)}» پیدا نشد.',
                suggestions=["لیست گروه‌ها", "آمار کلی"],
            )

        lines = [
            f'<i class="fa-solid fa-magnifying-glass" '
            f'style="color:#3D8499"></i> '
            f'<strong>نتایج جستجو برای «{escape(group_name)}»</strong> '
            f'<span class="text-muted">({len(groups)} مورد)</span>\n'
        ]

        for g in groups:
            title = escape(g.get("title") or "")
            code = escape(g.get("code") or "-")
            color = g.get("color") or "#3D8499"
            subgroups = g.get("subgroups_count", 0)

            lines.append(
                f'<i class="fa-solid fa-folder" style="color:{color}"></i> '
                f'<strong>{title}</strong> '
                f'<span class="text-muted">[{code}] — '
                f'{subgroups} زیرگروه</span>'
            )

        return Formatters.response(
            "\n".join(lines),
            "list",
            groups,
            suggestions=["زیرگروه‌ها", "توزیع گروه‌ها", "آمار کلی"],
        )