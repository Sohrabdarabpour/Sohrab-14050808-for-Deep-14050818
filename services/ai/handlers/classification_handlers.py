"""
Classification Handlers - طبقه‌بندی و گزارش‌ها
================================================
★ دستیار: گروه‌ها + زیرگروه‌ها + دپارتمان‌ها
★ خروجی: اکسل + پاورپوینت
"""
from html import escape

from services.ai.registry import IntentRegistry
from services.ai.formatters import Formatters
from database.connection import get_connection

# ★★★ مسیر درست (report رو یادت نره) ★★★
from services.document_group.report.excel_flat_service import (
    DocumentSubgroupExcelFlatService,
)


class ClassificationHandlers:
    """گزارش‌های طبقه‌بندی اسناد"""

    # ============================================================
    # ★ ۱. تعداد ترکیب‌های Flat
    # ============================================================
    @IntentRegistry.register(
        name="count_flat_combinations",
        patterns=[
            r"(چند|تعداد|شمار)\s*(ترکیب|ردیف)\s*(گروه|دپارتمان|گروه\s*و\s*دپارتمان)",
            r"(چند|تعداد)\s*(زیرگروه).{0,20}(گروه|دپارتمان)\s*(چند|تعداد)",
            r"کل\s*ترکیب‌?ها",
        ],
        priority=86,
        confidence=0.88,
        description="تعداد ترکیب‌های Flat گروه × دپارتمان",
    )
    @staticmethod
    def handle_count_flat_combinations(question, entities, user_id, is_admin):
        try:
            data = DocumentSubgroupExcelFlatService.get_flat_data()
        except Exception as e:
            return Formatters.error_response(
                f"خطا در دریافت داده‌ها: {str(e)}"
            )

        total = len(data)

        with_group = sum(1 for r in data if r.get("group_id"))
        with_dept = sum(1 for r in data if r.get("department_id"))
        both = sum(1 for r in data if r.get("group_id") and r.get("department_id"))

        unique_subgroups = len({r["subgroup_id"] for r in data})

        answer = (
            f'<i class="fa-solid fa-table-cells" style="color:#3D8499"></i> '
            f'در حال حاضر <strong class="num-highlight">{total}</strong> '
            f'ردیف ترکیبی (گروه × دپارتمان) وجود دارد.\n\n'
            f'<i class="fa-solid fa-folder-tree" style="color:#667eea"></i> '
            f'زیرگروه یکتا: <strong>{unique_subgroups}</strong>\n'
            f'<i class="fa-solid fa-diagram-project" style="color:#805AD5"></i> '
            f'دارای گروه: <strong>{with_group}</strong>\n'
            f'<i class="fa-solid fa-building-user" style="color:#D69E2E"></i> '
            f'دارای دپارتمان: <strong>{with_dept}</strong>\n'
            f'<i class="fa-solid fa-circle-check" style="color:#10b981"></i> '
            f'دارای هر دو: <strong>{both}</strong>'
        )

        return Formatters.response(
            answer,
            "count",
            [{"total": total, "subgroups": unique_subgroups}],
            suggestions=[
                "خروجی اکسل از زیرگروه‌ها بده",
                "توزیع گروه‌ها",
                "آمار کلی",
            ],
        )

    # ============================================================
    # ★ ۲. لیست زیرگروه‌های یک گروه با دپارتمان‌ها
    # ============================================================
    @IntentRegistry.register(
        name="subgroup_department_mapping",
        patterns=[
            r"(زیرگروه|زیرشاخه).{0,20}(دپارتمان|واحد).{0,20}(گروه)\s+(?P<group>[\u0600-\u06FF\w\s&]{2,30})",
            r"گروه\s+(?P<group>[\u0600-\u06FF\w\s&]{2,30}?)\s*(زیرگروه|دپارتمان)",
            r"نقشه\s*(گروه|طبقه‌بندی)",
        ],
        priority=87,
        confidence=0.88,
        description="نقشه زیرگروه‌ها با دپارتمان برای یک گروه",
    )
    @staticmethod
    def handle_subgroup_department_mapping(question, entities, user_id, is_admin):
        group_name = (entities.get("group") or "").strip()

        conn = get_connection()
        try:
            if group_name:
                group = conn.execute("""
                    SELECT id, title FROM document_groups
                    WHERE REPLACE(REPLACE(LOWER(title), 'ي', 'ی'), 'ك', 'ک')
                          LIKE ?
                    LIMIT 1
                """, (f"%{group_name.lower()}%",)).fetchone()
                if not group:
                    return Formatters.error_response(
                        f'گروهی با نام «{escape(group_name)}» پیدا نشد.'
                    )
                group_id = group["id"]
                group_title = group["title"]
            else:
                group_id = None
                group_title = "همه گروه‌ها"

        finally:
            conn.close()

        try:
            data = DocumentSubgroupExcelFlatService.get_flat_data(
                group_id=group_id,
            )
        except Exception as e:
            return Formatters.error_response(f"خطا: {str(e)}")

        if not data:
            return Formatters.empty_response(
                f'هیچ زیرگروهی برای «{escape(group_title)}» یافت نشد.'
            )

        by_subgroup = {}
        for row in data:
            sg_id = row["subgroup_id"]
            if sg_id not in by_subgroup:
                by_subgroup[sg_id] = {
                    "title": row["subgroup_title"],
                    "code": row["subgroup_code"],
                    "days": row["days_review"],
                    "departments": set(),
                    "groups": set(),
                }
            if row.get("department_title") and row["department_title"] != "—":
                by_subgroup[sg_id]["departments"].add(row["department_title"])
            if row.get("group_title") and row["group_title"] != "—":
                by_subgroup[sg_id]["groups"].add(row["group_title"])

        lines = [
            f'<i class="fa-solid fa-diagram-project" style="color:#3D8499"></i> '
            f'<strong>نقشه طبقه‌بندی</strong> '
            f'<span class="text-muted">({len(by_subgroup)} زیرگروه)</span>\n'
        ]

        for sg_id, sg in by_subgroup.items():
            deps = "، ".join(sg["departments"]) or "—"
            lines.append(
                f'<i class="fa-solid fa-folder" style="color:#667eea"></i> '
                f'<strong>{escape(sg["title"])}</strong> '
                f'<span class="text-muted">({sg["days"]} روز)</span>\n'
                f'&nbsp;&nbsp;<i class="fa-solid fa-building-user" '
                f'style="color:#D69E2E;font-size:9px"></i> '
                f'دپارتمان: {escape(deps)}'
            )

        return Formatters.response(
            "\n".join(lines),
            "list",
            data,
            suggestions=[
                "خروجی اکسل از زیرگروه‌ها بده",
                "توزیع گروه‌ها",
                "آمار کلی",
            ],
        )

    # ============================================================
    # ★ ۳. درخواست خروجی اکسل ★ (با دکمه)
    # ============================================================
    @IntentRegistry.register(
        name="export_subgroups_excel",
        patterns=[
            r"(خروجی|دانلود|بده|بساز).{0,15}(اکسل|excel|گزارش\s*اکسل).{0,20}(زیرگروه|گروه)",
            r"(اکسل|excel).{0,20}(زیرگروه|گروه|طبقه‌بندی)",
            r"گزارش\s*(اکسل|excel).{0,20}(گروه|زیرگروه)",
        ],
        priority=90,
        confidence=0.92,
        description="خروجی اکسل از زیرگروه‌ها",
    )
    @staticmethod
    def handle_export_subgroups_excel(question, entities, user_id, is_admin):
        download_url = "/assistant/export/subgroups-excel"

        answer = (
            f'<i class="fa-solid fa-file-excel" style="color:#10b981"></i> '
            f'<strong>خروجی اکسل آماده است!</strong>\n\n'
            f'<i class="fa-solid fa-circle-info" style="color:#3D8499"></i> '
            f'گزارش شامل تمام زیرگروه‌ها با ترکیب گروه و دپارتمان متولی است.\n\n'
            f'<button type="button" class="dl-btn dl-excel" '
            f'data-url="{download_url}" '
            f'data-filename="subgroups_flat.xlsx">'
            f'<i class="fa-solid fa-download"></i> دانلود فایل اکسل'
            f'</button>'
        )

        return Formatters.response(
            answer,
            "download",
            [{"url": download_url, "type": "xlsx", "label": "گزارش اکسل"}],
            suggestions=[
                "خروجی پاورپوینت",
                "توزیع گروه‌ها",
                "آمار کلی",
            ],
        )

    # ============================================================
    # ★ ۴. درخواست گزارش پاورپوینت ★ (با دکمه)
    # ============================================================
    @IntentRegistry.register(
        name="export_summary_powerpoint",
        patterns=[
            r"(خروجی|دانلود|بساز).{0,15}(پاورپوینت|powerpoint|ppt|پاور\s*پوینت)",
            r"گزارش\s*(پاورپوینت|ppt).{0,20}(طبقه‌بندی|گروه|زیرگروه)",
        ],
        priority=90,
        confidence=0.92,
        description="خروجی پاورپوینت گزارش طبقه‌بندی",
    )
    @staticmethod
    def handle_export_summary_powerpoint(question, entities, user_id, is_admin):
        download_url = "/assistant/export/summary-powerpoint"

        answer = (
            f'<i class="fa-solid fa-file-powerpoint" style="color:#d24726"></i> '
            f'<strong>گزارش پاورپوینت آماده است!</strong>\n\n'
            f'<i class="fa-solid fa-list-check" style="color:#3D8499"></i> '
            f'محتویات گزارش:\n'
            f'&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> خلاصه آماری\n'
            f'&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> توزیع گروه‌ها\n'
            f'&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> زیرگروه‌ها و دپارتمان‌ها\n'
            f'&nbsp;&nbsp;<i class="fa-solid fa-angle-left"></i> نمودارها\n\n'
            f'<button type="button" class="dl-btn dl-ppt" '
            f'data-url="{download_url}" '
            f'data-filename="classification_report.pptx">'
            f'<i class="fa-solid fa-download"></i> دانلود فایل پاورپوینت'
            f'</button>'
        )

        return Formatters.response(
            answer,
            "download",
            [{"url": download_url, "type": "pptx", "label": "گزارش پاورپوینت"}],
            suggestions=[
                "خروجی اکسل از زیرگروه‌ها بده",
                "توزیع گروه‌ها",
                "آمار کلی",
            ],
        )

    # ============================================================
    # ★ ۵. گزارش کامل طبقه‌بندی (خلاصه)
    # ============================================================
    @IntentRegistry.register(
        name="classification_report",
        patterns=[
            r"(گزارش|خلاصه)\s*(کامل|جامع)?\s*(طبقه‌بندی|گروه\s*و\s*زیرگروه)",
            r"طبقه‌بندی\s*(اسناد|گروه)",
        ],
        priority=88,
        confidence=0.88,
        description="گزارش کامل طبقه‌بندی",
    )
    @staticmethod
    def handle_classification_report(question, entities, user_id, is_admin):
        try:
            data = DocumentSubgroupExcelFlatService.get_flat_data()
        except Exception as e:
            return Formatters.error_response(f"خطا: {str(e)}")

        if not data:
            return Formatters.empty_response("هیچ داده طبقه‌بندی یافت نشد.")

        total_rows = len(data)
        unique_subgroups = len({r["subgroup_id"] for r in data})
        unique_groups = len({r["group_id"] for r in data if r.get("group_id")})
        unique_depts = len({r["department_id"] for r in data if r.get("department_id")})

        by_group = {}
        for r in data:
            g = r.get("group_title") or "—"
            by_group[g] = by_group.get(g, 0) + 1

        by_dept = {}
        for r in data:
            d = r.get("department_title") or "—"
            by_dept[d] = by_dept.get(d, 0) + 1

        by_subgroup_count = {}
        for r in data:
            st = r.get("subgroup_title") or "—"
            by_subgroup_count[st] = by_subgroup_count.get(st, 0) + 1

        top_subgroups = sorted(
            by_subgroup_count.items(), key=lambda x: -x[1]
        )[:5]

        lines = [
            f'<i class="fa-solid fa-chart-pie" style="color:#667eea"></i> '
            f'<strong>گزارش طبقه‌بندی اسناد</strong>\n',

            f'<i class="fa-solid fa-table-cells" style="color:#3D8499"></i> '
            f'کل ردیف‌ها: <strong class="num-highlight">{total_rows}</strong>',

            f'<i class="fa-solid fa-folder-tree" style="color:#10b981"></i> '
            f'زیرگروه یکتا: <strong>{unique_subgroups}</strong>',

            f'<i class="fa-solid fa-layer-group" style="color:#667eea"></i> '
            f'گروه یکتا: <strong>{unique_groups}</strong>',

            f'<i class="fa-solid fa-building-user" style="color:#D69E2E"></i> '
            f'دپارتمان یکتا: <strong>{unique_depts}</strong>\n',

            '<i class="fa-solid fa-folder" style="color:#667eea"></i> '
            '<strong>توزیع بر اساس گروه:</strong>',
        ]

        for g, count in sorted(by_group.items(), key=lambda x: -x[1])[:10]:
            lines.append(
                f'&nbsp;&nbsp;<i class="fa-solid fa-circle" '
                f'style="color:#667eea;font-size:8px"></i> '
                f'{escape(g)}: <strong>{count}</strong>'
            )

        lines.append('')
        lines.append(
            '<i class="fa-solid fa-building-user" style="color:#D69E2E"></i> '
            '<strong>توزیع بر اساس دپارتمان:</strong>'
        )

        for d, count in sorted(by_dept.items(), key=lambda x: -x[1])[:10]:
            lines.append(
                f'&nbsp;&nbsp;<i class="fa-solid fa-circle" '
                f'style="color:#D69E2E;font-size:8px"></i> '
                f'{escape(d)}: <strong>{count}</strong>'
            )

        if top_subgroups:
            lines.append('')
            lines.append(
                '<i class="fa-solid fa-star" style="color:#f59e0b"></i> '
                '<strong>پرتکرارترین زیرگروه‌ها:</strong>'
            )
            for s, count in top_subgroups:
                lines.append(
                    f'&nbsp;&nbsp;<i class="fa-solid fa-circle" '
                    f'style="color:#f59e0b;font-size:8px"></i> '
                    f'{escape(s)}: <strong>{count}</strong>'
                )

        return Formatters.response(
            "\n".join(lines),
            "stats",
            data,
            suggestions=[
                "خروجی اکسل از زیرگروه‌ها بده",
                "خروجی پاورپوینت",
                "لیست گروه‌ها",
            ],
        )