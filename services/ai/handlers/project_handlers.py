"""Handlerهای پروژه، پیمانکار و ناحیه.

این handlerها همان سرویس‌های موجود پروژه را صدا می‌زنند
(`database/repositories/projects.py` و …) و به زبان طبیعی پاسخ می‌دهند.
"""

from services.ai.formatters import Formatters
from services.ai.handlers.base import BaseHandler
from services.ai.registry import IntentRegistry

PROJECT_STATUS_LABELS = {
    "active": "فعال",
    "inactive": "غیرفعال",
    "completed": "تکمیل‌شده",
    "on_hold": "متوقف",
    "paused": "متوقف",
    "cancelled": "لغو‌شده",
    "canceled": "لغو‌شده",
    "planning": "در برنامه‌ریزی",
    "in_progress": "در حال اجرا",
}

PROJECT_SUGGESTIONS = [
    "لیست پروژه‌ها",
    "چند پروژه فعال داریم؟",
    "لیست پیمانکارها",
    "راهنما",
]


def _status_label(value):
    if not value:
        return "-"
    return PROJECT_STATUS_LABELS.get(str(value).lower(), str(value))


class ProjectHandlers(BaseHandler):
    """دستیار: پروژه‌ها، پیمانکاران و نواحی"""

    # ============================================================
    # ★ ۱. شمارش پروژه‌ها
    # ============================================================
    @IntentRegistry.register(
        name="count_projects",
        patterns=[
            r"(چند|تعداد|شمار)\s*(تا|مورد)?\s*پروژه",
            r"پروژه.{0,20}(چند|تعداد)",
            # «آمار پروژه» یا «وضعیت پروژه» — فقط وقتی نامی دنبالش نیست،
            # وگرنه باید به intent جزئیات پروژه برود
            r"(آمار|وضعیت)\s*(کل\s*)?پروژه\s*(ها|های)?\s*[؟?!.]*$",
        ],
        priority=88,
        confidence=0.9,
        description="شمارش پروژه‌های ثبت‌شده",
    )
    @staticmethod
    def handle_count_projects(question, entities, user_id, is_admin):
        from database.repositories.projects import get_projects_statistics

        stats = get_projects_statistics()
        total = stats["total"]
        active = stats["active"]

        if not total:
            return Formatters.empty_response(
                "هنوز هیچ پروژه‌ای در سیستم ثبت نشده است.",
                suggestions=PROJECT_SUGGESTIONS,
            )

        answer = (
            f'<i class="fa-solid fa-diagram-project" style="color:#3D8499"></i> '
            f'در حال حاضر <strong class="num-highlight">{total}</strong> پروژه ثبت شده '
            f'که <strong class="num-highlight">{active}</strong> مورد '
            f'<strong>فعال</strong> است.'
        )

        if stats.get("by_status"):
            parts = [
                f'<span class="text-muted">{Formatters._safe(_status_label(row["status"]))}:</span> '
                f'<strong>{row["count"]}</strong>'
                for row in stats["by_status"]
            ]
            answer += "\n\n" + " · ".join(parts)

        if stats.get("by_contract_type"):
            top = stats["by_contract_type"][0]
            answer += (
                f'\n\n<span class="text-muted">بیشترین تعداد بر اساس نوع قرارداد: </span>'
                f'<strong>{Formatters._safe(top["title"])}</strong> '
                f'<span class="text-muted">({top["count"]} پروژه)</span>'
            )

        return Formatters.response(
            answer,
            "count",
            data=stats.get("by_status", []),
            suggestions=PROJECT_SUGGESTIONS,
        )

    # ============================================================
    # ★ ۲. لیست پروژه‌ها
    # ============================================================
    @IntentRegistry.register(
        name="list_projects",
        patterns=[
            r"(لیست|فهرست|همه)\s*(ی|ی‌)?\s*پروژه",
            r"پروژه\s*(ها|های)\s*(رو|را)?\s*(نشون|بگو|بده|بیار|لیست)",
            r"پروژه\s*(های)?\s*فعال",
        ],
        priority=87,
        confidence=0.9,
        description="لیست پروژه‌ها",
    )
    @staticmethod
    def handle_list_projects(question, entities, user_id, is_admin):
        from database.repositories.projects import get_all_projects

        projects = get_all_projects(only_active=True) or []

        if not projects:
            return Formatters.empty_response(
                "هیچ پروژه‌ی فعالی وجود ندارد.", suggestions=PROJECT_SUGGESTIONS
            )

        lines = [
            f'<i class="fa-solid fa-diagram-project" style="color:#3D8499"></i> '
            f'<strong>پروژه‌های فعال</strong> '
            f'<span class="text-muted">({len(projects)} مورد)</span>\n'
        ]

        for index, project in enumerate(projects[:10], 1):
            name = Formatters._safe(project.get("name") or "بدون نام")
            code = Formatters._safe(project.get("code") or "-")
            status = Formatters._safe(_status_label(project.get("status")))
            progress = project.get("progress_percent") or 0
            contractor = Formatters._safe(project.get("contractor_name") or "")

            lines.append(
                f'<span class="doc-num">{index}.</span> <strong>{name}</strong>'
            )

            meta = [f'<i class="fa-solid fa-circle-dot"></i> {status}']
            if code != "-":
                meta.append(f'<i class="fa-solid fa-bookmark"></i> {code}')
            if progress:
                meta.append(f'<i class="fa-solid fa-bars-progress"></i> {progress}%')
            if contractor:
                meta.append(f'<i class="fa-solid fa-building"></i> {contractor}')

            lines.append(
                '&nbsp;&nbsp;<span class="text-muted">' + " · ".join(meta) + "</span>"
            )

        if len(projects) > 10:
            lines.append(
                f'\n<span class="text-muted">و {len(projects) - 10} پروژه‌ی دیگر…</span>'
            )

        return Formatters.response(
            "\n".join(lines),
            "list",
            data=projects[:10],
            suggestions=["چند پروژه فعال داریم؟", "لیست پیمانکارها", "راهنما"],
        )

    # ============================================================
    # ★ ۳. جزئیات یک پروژه
    # ============================================================
    @IntentRegistry.register(
        name="project_details",
        patterns=[
            r"وضعیت\s*پروژه\s+(?P<name>.{2,40})",
            r"پروژه\s+(?P<name>.{2,40}?)\s*(?:چطوره|چطور|چیه|چیست|کیست|در چه وضعیت)",
            r"اطلاعات\s*پروژه\s+(?P<name>.{2,40})",
        ],
        priority=93,
        confidence=0.9,
        description="جزئیات یک پروژه با نام",
    )
    @staticmethod
    def handle_project_details(question, entities, user_id, is_admin):
        from database.repositories.projects import search_projects

        name = (entities or {}).get("name", "").strip(" ؟?.:")
        if not name:
            return Formatters.empty_response(
                "نام پروژه را متوجه نشدم. مثلاً: «وضعیت پروژه خط ۲»",
                suggestions=PROJECT_SUGGESTIONS,
            )

        matches = search_projects(name) or []

        if not matches:
            return Formatters.empty_response(
                f'پروژه‌ای با نام «{Formatters._safe(name)}» پیدا نشد.',
                suggestions=PROJECT_SUGGESTIONS,
            )

        if len(matches) > 1:
            titles = "، ".join(
                Formatters._safe(item.get("name")) for item in matches[:5]
            )
            return Formatters.response(
                f'<i class="fa-solid fa-circle-info" style="color:#3D8499"></i> '
                f'چند پروژه با این نام پیدا شد: <strong>{titles}</strong>\n\n'
                f'<span class="text-muted">نام دقیق‌تری بنویسید.</span>',
                "list",
                data=matches[:5],
                suggestions=PROJECT_SUGGESTIONS,
            )

        project = matches[0]
        rows = [
            ("وضعیت", _status_label(project.get("status"))),
            ("کد", project.get("code") or "-"),
            ("پیمانکار", project.get("contractor_name") or "-"),
            ("نوع قرارداد", project.get("contract_type_title") or "-"),
            ("ناحیه", project.get("area_title") or "-"),
            ("پیشرفت", f'{project.get("progress_percent") or 0}%'),
            ("تاریخ شروع", project.get("start_date") or "-"),
            ("پایان برنامه‌ریزی‌شده", project.get("planned_end_date") or "-"),
        ]

        answer = (
            f'<i class="fa-solid fa-diagram-project" style="color:#3D8499"></i> '
            f'<strong>{Formatters._safe(project.get("name"))}</strong>\n\n'
        )
        answer += "\n".join(
            f'<span class="text-muted">{label}:</span> <strong>{Formatters._safe(str(value))}</strong>'
            for label, value in rows
        )

        return Formatters.response(
            answer, "stats", data=[project], suggestions=PROJECT_SUGGESTIONS
        )

    # ============================================================
    # ★ ۴. شمارش پیمانکاران
    # ============================================================
    @IntentRegistry.register(
        name="count_contractors",
        patterns=[
            r"(چند|تعداد|شمار)\s*(تا|مورد)?\s*پیمانکار",
            r"پیمانکار.{0,20}(چند|تعداد)",
        ],
        priority=88,
        confidence=0.9,
        description="شمارش پیمانکاران",
    )
    @staticmethod
    def handle_count_contractors(question, entities, user_id, is_admin):
        from database.repositories.contractors import get_all_contractors

        contractors = get_all_contractors() or []
        active = [item for item in contractors if item.get("is_active")]

        if not contractors:
            return Formatters.empty_response(
                "هیچ پیمانکاری ثبت نشده است.",
                suggestions=["لیست پیمانکارها", "چند پروژه فعال داریم؟", "راهنما"],
            )

        return Formatters.response(
            f'<i class="fa-solid fa-building" style="color:#3D8499"></i> '
            f'در حال حاضر <strong class="num-highlight">{len(contractors)}</strong> '
            f'پیمانکار در سیستم ثبت شده که '
            f'<strong class="num-highlight">{len(active)}</strong> مورد فعال است.',
            "count",
            data=contractors,
            suggestions=["لیست پیمانکارها", "چند پروژه فعال داریم؟", "راهنما"],
        )

    # ============================================================
    # ★ ۵. لیست پیمانکاران
    # ============================================================
    @IntentRegistry.register(
        name="list_contractors",
        patterns=[
            r"(لیست|فهرست|همه)\s*(ی|ی‌)?\s*پیمانکار",
            r"پیمانکار\s*(ها|های)\s*(رو|را)?\s*(نشون|بگو|بده|بیار|لیست)",
        ],
        priority=87,
        confidence=0.9,
        description="لیست پیمانکاران",
    )
    @staticmethod
    def handle_list_contractors(question, entities, user_id, is_admin):
        from database.repositories.contractors import get_all_contractors

        contractors = [c for c in (get_all_contractors() or []) if c.get("is_active")]

        if not contractors:
            return Formatters.empty_response(
                "پیمانکار فعالی وجود ندارد.",
                suggestions=["چند پیمانکار داریم؟", "راهنما"],
            )

        lines = [
            f'<i class="fa-solid fa-building" style="color:#3D8499"></i> '
            f'<strong>پیمانکاران فعال</strong> '
            f'<span class="text-muted">({len(contractors)} مورد)</span>\n'
        ]

        for index, contractor in enumerate(contractors[:10], 1):
            name = Formatters._safe(contractor.get("name") or "-")
            manager = Formatters._safe(contractor.get("manager_name") or "")
            province = Formatters._safe(contractor.get("province") or "")

            meta = []
            if manager:
                meta.append(f'<i class="fa-solid fa-user"></i> {manager}')
            if province:
                meta.append(f'<i class="fa-solid fa-location-dot"></i> {province}')

            lines.append(f'<span class="doc-num">{index}.</span> <strong>{name}</strong>')
            if meta:
                lines.append(
                    '&nbsp;&nbsp;<span class="text-muted">' + " · ".join(meta) + "</span>"
                )

        if len(contractors) > 10:
            lines.append(
                f'\n<span class="text-muted">و {len(contractors) - 10} پیمانکار دیگر…</span>'
            )

        return Formatters.response(
            "\n".join(lines),
            "list",
            data=contractors[:10],
            suggestions=["چند پیمانکار داریم؟", "لیست پروژه‌ها", "راهنما"],
        )

    # ============================================================
    # ★ ۶. لیست نواحی
    # ============================================================
    @IntentRegistry.register(
        name="list_areas",
        patterns=[
            r"(لیست|فهرست|همه)\s*(ی|ی‌)?\s*(نواحی|مناطق|ناحیه)",
            r"(چند|تعداد)\s*(تا|مورد)?\s*(ناحیه|منطقه)",
            r"^\s*(نواحی|ناحیه‌ها|مناطق|ناحیه)\s*[؟?!.]*$",
            r"نواحی\s*(رو|را)?\s*(نشون|بگو|بده|بیار|لیست)",
        ],
        priority=86,
        confidence=0.9,
        description="لیست نواحی",
    )
    @staticmethod
    def handle_list_areas(question, entities, user_id, is_admin):
        from database.repositories.areas import get_all_areas

        areas = get_all_areas() or []

        if not areas:
            return Formatters.empty_response(
                "هیچ ناحیه‌ای تعریف نشده است.",
                suggestions=["چند پروژه فعال داریم؟", "راهنما"],
            )

        names = "، ".join(Formatters._safe(area.get("title")) for area in areas[:15])

        return Formatters.response(
            f'<i class="fa-solid fa-map-location-dot" style="color:#3D8499"></i> '
            f'<strong>{len(areas)}</strong> ناحیه تعریف شده است:\n\n'
            f'{names}',
            "list",
            data=areas,
            suggestions=["لیست پروژه‌ها", "چند پروژه فعال داریم؟", "راهنما"],
        )
