"""
لایه واسط بین LLM و سرویس‌های واقعی پروژه
★ همه تاریخ‌ها با DateHelper به شمسی تبدیل می‌شن
"""
import json
from html import escape
from datetime import datetime

from database.connection import get_connection
from helpers.date_helper import DateHelper
from services.ai.llm_tools_extra import EXTRA_TOOL_SCHEMAS, ExtraToolsMixin


class LLMTools(ExtraToolsMixin):
    """واسط بین LLM و سرویس‌های داخلی"""

    # ============================================================
    # ★ Helper: تبدیل تاریخ‌ها در dict
    # ============================================================
    @staticmethod
    def _to_jalali_dates(item, extra_fields=None):
        """
        هر dict رو می‌گیره، فیلدهای تاریخ رو شمسی می‌کنه
        """
        default_fields = {
            "deadline", "date_received", "date_referral",
            "date_letter", "response_announce_date",
            "created_at", "updated_at",
        }
        if extra_fields:
            default_fields = default_fields | set(extra_fields)

        result = {}
        for k, v in item.items():
            if k in default_fields and v:
                try:
                    result[k] = DateHelper.format_jalali(v)
                except Exception:
                    result[k] = v
            else:
                result[k] = v
        return result

    @staticmethod
    def _safe_escape(value):
        """escape با چک None"""
        if value is None:
            return ""
        return escape(str(value))

    # ============================================================
    # ★ Schema توابع
    # ============================================================
    @classmethod
    def get_tools_schema(cls, is_admin=False):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_performance_summary",
                    "description": "آمار کلی عملکرد اسناد (کل، تکمیل، باقی، نرخ تکمیل)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {"type": "string", "description": "'all' یا سال شمسی مثل '1403'"},
                            "department_id": {"type": "integer"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_department_ranking",
                    "description": "رتبه‌بندی دپارتمان‌ها. مثال: بهترین دپارتمان کدومه؟",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {"type": "string"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_monthly_trend",
                    "description": "روند ماهانه اسناد. مثال: روند ماهانه چطوره؟",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {"type": "string"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_departments",
                    "description": "لیست دپارتمان‌های موجود",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "count_documents_by_status",
                    "description": "شمارش اسناد بر اساس وضعیت",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status_code": {
                                "type": "string",
                                "enum": ["in_progress", "completed", "stopped", "deleted", "informational"]
                            },
                            "user_only": {"type": "boolean"}
                        },
                        "required": ["status_code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_documents",
                    "description": "جستجو در اسناد بر اساس موضوع، کد، پیمانکار یا پروژه",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_my_documents",
                    "description": "دریافت اسناد کاربر فعلی",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status_code": {"type": "string"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_overdue_documents",
                    "description": "اسناد با مهلت گذشته (دیرکرد)",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
        ]

        if is_admin:
            tools.append({
                "type": "function",
                "function": {
                    "name": "get_top_experts",
                    "description": "پرمشغله‌ترین کارشناسان",
                    "parameters": {"type": "object", "properties": {}}
                }
            })

        # ابزارهای پروژه، پیمانکار، ناحیه، جستجوی پیشرفته و اکسل
        tools.extend(EXTRA_TOOL_SCHEMAS)

        return tools

    # ============================================================
    # ★ اجرا
    # ============================================================
    @classmethod
    def execute(cls, function_name, arguments, user_id, is_admin):
        handler = getattr(cls, f"_fn_{function_name}", None)
        if not handler:
            return {"error": f"تابع {function_name} یافت نشد"}

        try:
            return handler(arguments, user_id, is_admin)
        except Exception as e:
            return {"error": f"خطا: {str(e)}"}

    # ============================================================
    # ── ۱. آمار کلی ──
    # ============================================================
    @classmethod
    def _fn_get_performance_summary(cls, args, user_id, is_admin):
        from services.departments.department_performance_service import DepartmentPerformanceService
        year = str(args.get("year") or "all")
        department_id = args.get("department_id")

        result = DepartmentPerformanceService.get_summary(
            year=year, department_id=department_id
        )

        return {
            "year": year,
            "total": result["total"],
            "completed": result["completed"],
            "pending": result["pending"],
            "excluded": result["excluded"],
            "completion_rate": result["completion_rate"],
            "status_breakdown": [
                {
                    "title": cls._safe_escape(s["title"]),
                    "count": s["count"],
                    "category": s["category"]
                }
                for s in result["status_breakdown"]
            ]
        }

    # ============================================================
    # ── ۲. رتبه‌بندی دپارتمان ──
    # ============================================================
    @classmethod
    def _fn_get_department_ranking(cls, args, user_id, is_admin):
        from services.departments.department_performance_service import DepartmentPerformanceService
        year = str(args.get("year") or "all")
        result = DepartmentPerformanceService.get_department_ranking(year=year)

        return {
            "year": year,
            "count": len(result),
            "best": {
                "title": cls._safe_escape(result[0]["department_title"]),
                "score": result[0]["score"],
                "rate": result[0]["completion_rate"]
            } if result else None,
            "ranking": [
                {
                    "rank": i,
                    "department": cls._safe_escape(d["department_title"]),
                    "total": d["total"],
                    "completed": d["completed"],
                    "pending": d["pending"],
                    "rate": d["completion_rate"],
                    "score": d["score"]
                }
                for i, d in enumerate(result[:10], 1)
            ]
        }

    # ============================================================
    # ── ۳. روند ماهانه ──
    # ============================================================
    @classmethod
    def _fn_get_monthly_trend(cls, args, user_id, is_admin):
        from services.departments.department_performance_service import DepartmentPerformanceService
        year = str(args.get("year") or "all")
        result = DepartmentPerformanceService.get_monthly_trend(year=year)

        compressed = []
        for i, label in enumerate(result["labels"]):
            if result["total"][i] > 0:
                # ★ label از قبل شمسی است (فروردین 1403)
                compressed.append({
                    "month": label,
                    "total": result["total"][i],
                    "completed": result["completed"][i],
                    "pending": result["pending"][i],
                })

        return {
            "year": year,
            "months": compressed,
            "total_sum": sum(result["total"]),
            "completed_sum": sum(result["completed"]),
        }

    # ============================================================
    # ── ۴. لیست دپارتمان‌ها ──
    # ============================================================
    @classmethod
    def _fn_list_departments(cls, args, user_id, is_admin):
        conn = get_connection()
        try:
            from services.departments.department_performance_service import DepartmentPerformanceService
            deps = DepartmentPerformanceService.get_departments(conn)
            return {
                "count": len(deps),
                "departments": [
                    {
                        "id": d["id"],
                        "title": cls._safe_escape(d["title"]),
                        "code": d["code"]
                    }
                    for d in deps
                ]
            }
        finally:
            conn.close()

    # ============================================================
    # ── ۵. شمارش بر اساس وضعیت ──
    # ============================================================
    @classmethod
    def _fn_count_documents_by_status(cls, args, user_id, is_admin):
        status_code = args.get("status_code")
        user_only = args.get("user_only", True)

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT id, title FROM document_statuses WHERE code = ?",
                (status_code,)
            ).fetchone()
            if not row:
                return {"error": f"وضعیت {status_code} پیدا نشد"}

            sid = row["id"]
            title = row["title"]

            sql = "SELECT COUNT(*) AS c FROM documents WHERE status_id = ?"
            params = [sid]
            if user_only and user_id:
                sql += " AND user_id = ?"
                params.append(user_id)

            c = conn.execute(sql, params).fetchone()["c"]

            return {
                "status": cls._safe_escape(title),
                "status_code": status_code,
                "count": c,
                "user_only": user_only
            }
        finally:
            conn.close()

    # ============================================================
    # ── ۶. جستجوی اسناد ★ با تاریخ شمسی ──
    # ============================================================
    @classmethod
    def _fn_search_documents(cls, args, user_id, is_admin):
        query = (args.get("query") or "").strip()
        if len(query) < 2:
            return {"error": "عبارت جستجو کوتاه است", "documents": []}

        conn = get_connection()
        try:
            sql = """
                SELECT d.id, d.subject, d.code_dfc, d.deadline,
                       d.date_received, d.date_referral,
                       d.contractor, d.project_name,
                       s.title AS status_title
                FROM documents d
                LEFT JOIN document_statuses s ON s.id = d.status_id
                WHERE (d.subject LIKE ? OR d.code_dfc LIKE ?
                       OR d.contractor LIKE ? OR d.project_name LIKE ?)
            """
            like = f"%{query}%"
            params = [like, like, like, like]

            if not is_admin:
                sql += " AND d.user_id = ?"
                params.append(user_id)

            sql += " ORDER BY d.id DESC LIMIT 15"
            rows = conn.execute(sql, params).fetchall()

            documents = []
            for r in rows:
                # ★ تبدیل به dict و شمسی کردن تاریخ‌ها
                doc = cls._to_jalali_dates(dict(r))

                # ★ escape متن‌ها
                doc["subject"] = cls._safe_escape(doc.get("subject"))
                doc["contractor"] = cls._safe_escape(doc.get("contractor"))
                doc["project_name"] = cls._safe_escape(doc.get("project_name"))
                doc["status"] = cls._safe_escape(doc.pop("status_title", ""))

                documents.append(doc)

            return {
                "query": query,
                "count": len(documents),
                "documents": documents
            }
        finally:
            conn.close()

    # ============================================================
    # ── ۷. اسناد کاربر ★ با تاریخ شمسی ──
    # ============================================================
    @classmethod
    def _fn_get_my_documents(cls, args, user_id, is_admin):
        if not user_id:
            return {"error": "ابتدا وارد شوید"}

        status_code = args.get("status_code")

        conn = get_connection()
        try:
            sql = """
                SELECT d.id, d.subject, d.code_dfc, d.deadline,
                       d.date_received, d.date_referral,
                       d.contractor, d.project_name,
                       s.title AS status_title
                FROM documents d
                LEFT JOIN document_statuses s ON s.id = d.status_id
                WHERE d.user_id = ?
            """
            params = [user_id]

            if status_code:
                sql += " AND s.code = ?"
                params.append(status_code)

            sql += " ORDER BY d.id DESC LIMIT 20"
            rows = conn.execute(sql, params).fetchall()

            documents = []
            for r in rows:
                doc = cls._to_jalali_dates(dict(r))
                doc["subject"] = cls._safe_escape(doc.get("subject"))
                doc["status"] = cls._safe_escape(doc.pop("status_title", ""))
                documents.append(doc)

            return {
                "count": len(documents),
                "filter_status": status_code or "همه",
                "documents": documents
            }
        finally:
            conn.close()

    # ============================================================
    # ── ۸. اسناد دیرکرد ★ با تاریخ شمسی ──
    # ============================================================
    @classmethod
    def _fn_get_overdue_documents(cls, args, user_id, is_admin):
        # ★ امروز به میلادی
        today_gregorian = datetime.now().strftime("%Y/%m/%d")

        conn = get_connection()
        try:
            sql = """
                SELECT d.id, d.subject, d.code_dfc, d.deadline,
                       d.date_received,
                       s.title AS status_title
                FROM documents d
                LEFT JOIN document_statuses s ON s.id = d.status_id
                WHERE d.deadline IS NOT NULL
                  AND d.deadline != ''
                  AND d.deadline < ?
                  AND s.code = 'in_progress'
            """
            params = [today_gregorian]

            if not is_admin:
                sql += " AND d.user_id = ?"
                params.append(user_id)

            sql += " ORDER BY d.deadline ASC LIMIT 20"
            rows = conn.execute(sql, params).fetchall()

            documents = []
            for r in rows:
                doc = cls._to_jalali_dates(dict(r))
                doc["subject"] = cls._safe_escape(doc.get("subject"))
                doc["status"] = cls._safe_escape(doc.pop("status_title", ""))
                documents.append(doc)

            return {
                "count": len(documents),
                "today": DateHelper.format_jalali(today_gregorian),
                "documents": documents
            }
        finally:
            conn.close()

    # ============================================================
    # ── ۹. پرمشغله‌ترین کارشناسان (ادمین) ──
    # ============================================================
    @classmethod
    def _fn_get_top_experts(cls, args, user_id, is_admin):
        if not is_admin:
            return {"error": "دسترسی ندارید"}

        conn = get_connection()
        try:
            rows = conn.execute("""
                SELECT u.full_name, COUNT(d.id) AS c
                FROM users u
                LEFT JOIN documents d ON d.user_id = u.id
                WHERE u.is_active = 1
                GROUP BY u.id
                HAVING c > 0
                ORDER BY c DESC LIMIT 5
            """).fetchall()

            return {
                "experts": [
                    {
                        "name": cls._safe_escape(r["full_name"]),
                        "count": r["c"]
                    }
                    for r in rows
                ]
            }
        finally:
            conn.close()