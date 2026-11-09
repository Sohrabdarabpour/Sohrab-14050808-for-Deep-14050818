"""ابزارهای تکمیلی LLM — پروژه، پیمانکار، ناحیه، جستجوی پیشرفته و خروجی اکسل.

این ماژول به‌صورت Mixin در کلاس `LLMTools` ترکیب می‌شود:
    class LLMTools(ExtraToolsMixin):
        ...

بنابراین `LLMTools.execute("list_projects", ...)` مستقیماً کار می‌کند.
"""

EXTRA_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_projects",
            "description": "لیست پروژه‌ها با وضعیت و درصد پیشرفت. مثال: پروژه‌های فعال کدام‌اند؟",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "فیلتر وضعیت: active | inactive | completed | on_hold | cancelled",
                    },
                    "only_active": {"type": "boolean"},
                    "limit": {"type": "integer", "description": "حداکثر تعداد (پیش‌فرض ۱۰)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_projects_summary",
            "description": "آمار پروژه‌ها: کل، فعال، تفکیک بر اساس وضعیت و نوع قرارداد",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_projects",
            "description": "جستجوی پروژه با نام یا کد",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "نام یا کد پروژه"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_contractors",
            "description": "لیست یا جستجوی پیمانکاران",
            "parameters": {
                "type": "object",
                "properties": {
                    "only_active": {"type": "boolean"},
                    "query": {"type": "string", "description": "بخشی از نام پیمانکار"},
                    "limit": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_areas",
            "description": "لیست نواحی/مناطق تعریف‌شده",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_contractor_documents",
            "description": "اسناد یک پیمانکار بر اساس نام",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "نام یا کد پیمانکار"},
                    "limit": {"type": "integer"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents_advanced",
            "description": (
                "جستجوی پیشرفته در اسناد با فیلتر پیمانکار، پروژه، ناحیه، گروه، "
                "کارشناس، وضعیت و بازه تاریخ. برای سؤال‌های ترکیبی از این ابزار "
                "استفاده کن. مثال: اسناد پیمانکار آبسان با وضعیت تکمیل در ناحیه برق"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "متن آزاد جستجو"},
                    "status_code": {
                        "type": "string",
                        "enum": [
                            "in_progress",
                            "completed",
                            "stopped",
                            "deleted",
                            "informational",
                        ],
                    },
                    "contractor_name": {"type": "string"},
                    "project_name": {"type": "string"},
                    "area_name": {"type": "string"},
                    "group_name": {"type": "string"},
                    "expert_name": {"type": "string"},
                    "date_from": {"type": "string", "description": "میلادی YYYY/MM/DD"},
                    "date_to": {"type": "string", "description": "میلادی YYYY/MM/DD"},
                    "limit": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_search_excel",
            "description": (
                "ساخت لینک دانلود فایل اکسل از نتایج جستجوی فیلترشده. "
                "وقتی کاربر گفت «خروجی اکسل» یا «دانلود اکسل» از این ابزار استفاده کن."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "status_code": {
                        "type": "string",
                        "enum": [
                            "in_progress",
                            "completed",
                            "stopped",
                            "deleted",
                            "informational",
                        ],
                    },
                    "contractor_name": {"type": "string"},
                    "project_name": {"type": "string"},
                    "area_name": {"type": "string"},
                    "date_from": {"type": "string"},
                    "date_to": {"type": "string"},
                },
            },
        },
    },
]


def _resolve_ids(args):
    """تبدیل نام‌های ورودی به شناسه، با استفاده از همان repositoryهای برنامه."""
    from database.repositories.areas import get_all_areas
    from database.repositories.contractors import search_contractors
    from database.repositories.projects import search_projects

    filters = {}

    contractor_name = (args.get("contractor_name") or "").strip()
    if contractor_name:
        found = search_contractors(contractor_name) or []
        if found:
            filters["contractor_id"] = found[0]["id"]

    project_name = (args.get("project_name") or "").strip()
    if project_name:
        found = search_projects(project_name) or []
        if len(found) == 1:
            filters["project_id"] = found[0]["id"]

    area_name = (args.get("area_name") or "").strip()
    if area_name:
        for area in get_all_areas() or []:
            title = area.get("title") or ""
            if area_name in title or title in area_name:
                filters["area_id"] = area["id"]
                break

    status_code = (args.get("status_code") or "").strip()
    if status_code:
        filters["status_code"] = status_code

    query = (args.get("query") or "").strip()
    if query:
        filters["query"] = query

    if args.get("date_from"):
        filters["date_from"] = args["date_from"]
    if args.get("date_to"):
        filters["date_to"] = args["date_to"]

    return filters


class ExtraToolsMixin:
    """ابزارهای پروژه/پیمانکار/ناحیه و جستجوی پیشرفته."""

    # ---------------------------------------------------------------- پروژه‌ها
    @classmethod
    def _fn_list_projects(cls, args, user_id, is_admin):
        from database.repositories.projects import get_all_projects

        limit = int(args.get("limit") or 10)
        projects = get_all_projects(
            only_active=bool(args.get("only_active")),
            status=args.get("status") or None,
        ) or []

        return {
            "count": len(projects),
            "projects": [
                {
                    "name": cls._safe_escape(item.get("name")),
                    "code": cls._safe_escape(item.get("code")),
                    "status": item.get("status"),
                    "progress_percent": item.get("progress_percent") or 0,
                    "contractor": cls._safe_escape(item.get("contractor_name")),
                    "area": cls._safe_escape(item.get("area_title")),
                    "planned_end_date": item.get("planned_end_date"),
                }
                for item in projects[:limit]
            ],
        }

    @classmethod
    def _fn_get_projects_summary(cls, args, user_id, is_admin):
        from database.repositories.projects import get_projects_statistics

        stats = get_projects_statistics()
        return {
            "total": stats["total"],
            "active": stats["active"],
            "inactive": stats["inactive"],
            "by_status": [
                {"status": row["status"], "count": row["count"]}
                for row in stats.get("by_status", [])
            ],
            "by_contract_type": [
                {"title": cls._safe_escape(row["title"]), "count": row["count"]}
                for row in stats.get("by_contract_type", [])
            ],
        }

    @classmethod
    def _fn_search_projects(cls, args, user_id, is_admin):
        from database.repositories.projects import search_projects

        query = (args.get("query") or "").strip()
        if not query:
            return {"error": "عبارت جستجو خالی است"}

        matches = search_projects(query) or []
        return {
            "query": cls._safe_escape(query),
            "count": len(matches),
            "projects": [
                {
                    "name": cls._safe_escape(item.get("name")),
                    "code": cls._safe_escape(item.get("code")),
                    "status": item.get("status"),
                    "progress_percent": item.get("progress_percent") or 0,
                }
                for item in matches[:5]
            ],
        }

    # ---------------------------------------------------------------- پیمانکاران
    @classmethod
    def _fn_list_contractors(cls, args, user_id, is_admin):
        from database.repositories.contractors import (
            get_all_contractors,
            search_contractors,
        )

        query = (args.get("query") or "").strip()
        limit = int(args.get("limit") or 10)
        only_active = bool(args.get("only_active", True))

        if query:
            contractors = search_contractors(query, only_active=only_active) or []
        else:
            contractors = get_all_contractors(only_active=only_active) or []

        return {
            "count": len(contractors),
            "contractors": [
                {
                    "name": cls._safe_escape(item.get("name")),
                    "code": cls._safe_escape(item.get("code")),
                    "manager_name": cls._safe_escape(item.get("manager_name")),
                    "province": cls._safe_escape(item.get("province")),
                    "is_active": bool(item.get("is_active")),
                }
                for item in contractors[:limit]
            ],
        }

    @classmethod
    def _fn_list_areas(cls, args, user_id, is_admin):
        from database.repositories.areas import get_all_areas

        areas = get_all_areas() or []
        return {
            "count": len(areas),
            "areas": [
                {
                    "title": cls._safe_escape(item.get("title")),
                    "code": cls._safe_escape(item.get("code")),
                }
                for item in areas
            ],
        }

    @classmethod
    def _fn_get_contractor_documents(cls, args, user_id, is_admin):
        from database.connection import get_connection
        from database.repositories.contractors import search_contractors

        name = (args.get("name") or "").strip()
        limit = int(args.get("limit") or 10)
        if not name:
            return {"error": "نام پیمانکار خالی است"}

        contractors = search_contractors(name) or []
        if not contractors:
            return {"error": f"پیمانکاری با نام «{name}» یافت نشد"}

        contractor = contractors[0]
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT d.id, d.subject, d.code_dfc, d.deadline,
                       s.title AS status_title
                FROM documents d
                LEFT JOIN document_statuses s ON s.id = d.status_id
                WHERE d.contractor_id = ?
                ORDER BY d.id DESC
                LIMIT ?
                """,
                (contractor["id"], limit),
            ).fetchall()
        finally:
            conn.close()

        return {
            "contractor": cls._safe_escape(contractor.get("name")),
            "count": len(rows),
            "documents": [
                {
                    "id": row["id"],
                    "subject": cls._safe_escape(row["subject"]),
                    "code_dfc": cls._safe_escape(row["code_dfc"]),
                    "status": cls._safe_escape(row["status_title"]),
                    "deadline": row["deadline"],
                }
                for row in rows
            ],
        }

    # ---------------------------------------------------------------- جستجوی پیشرفته
    @classmethod
    def _fn_search_documents_advanced(cls, args, user_id, is_admin):
        from services.search.search_service import search_documents

        filters = _resolve_ids(args or {})
        if not filters:
            return {"error": "هیچ فیلتری مشخص نشد"}

        limit = int((args or {}).get("limit") or 10)
        result = search_documents(**filters, page=1, per_page=limit)

        return {
            "total": result.get("total", 0),
            "filters": {key: value for key, value in filters.items()},
            "documents": [
                {
                    "id": record.get("id"),
                    "subject": cls._safe_escape(record.get("subject")),
                    "code_dfc": cls._safe_escape(record.get("code_dfc")),
                    "status": cls._safe_escape(record.get("status_title")),
                    "contractor": cls._safe_escape(record.get("contractor_name")),
                    "project": cls._safe_escape(record.get("project_title")),
                }
                for record in result.get("records", [])
            ],
        }

    @classmethod
    def _fn_export_search_excel(cls, args, user_id, is_admin):
        from services.search.search_filters import filters_to_query
        from services.search.search_service import search_documents

        filters = _resolve_ids(args or {})
        if not filters:
            return {"error": "برای خروجی اکسل حداقل یک فیلتر لازم است"}

        total = search_documents(**filters, page=1, per_page=1).get("total", 0)
        if not total:
            return {"error": "هیچ سندی با این فیلترها پیدا نشد", "filters": filters}

        return {
            "total": total,
            "download_url": filters_to_query(filters),
            "message": "لینک دانلود آماده است؛ آن را در پاسخ به کاربر بگذار.",
        }
