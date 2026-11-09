"""
Search Handlers - جستجو
==========================
★ نسخه Registry-based
"""
from html import escape

from services.ai.registry import IntentRegistry
from services.ai.formatters import Formatters
from database.connection import get_connection


class SearchHandlers:

    MIN_QUERY_LENGTH = 2
    MAX_QUERY_LENGTH = 100
    MAX_RESULTS = 20

    SEARCH_FIELDS = [
        "subject",
        "code_dfc",
        "contractor",
        "project_name",
        "contract_number",
        "automation_number",
    ]

    @IntentRegistry.register(
        name="search",
        patterns=[
            r"(جستجو|بگرد|پیدا کن|سرچ|جست‌وجو)\s*(برای|در)?\s*(?P<query>.+)",
            r"(دنبال|به دنبال)\s*(?P<query>.+?)\s*(بگرد|هستم)",
        ],
        priority=80,
        confidence=0.88,
        description="جستجو در اسناد",
    )
    @staticmethod
    def handle_search(question, entities, user_id, is_admin):
        query = (entities.get("query") or "").strip()
        return SearchHandlers._search(query, user_id, is_admin)

    # ============================================================
    # ★ جستجو
    # ============================================================
    @classmethod
    def _search(cls, query, user_id, is_admin):
        query = cls._validate_query(query)
        if query is None:
            return Formatters.error_response(
                "عبارت جستجو باید حداقل ۲ کاراکتر باشد.",
                suggestions=["کارهای من", "آمار کلی", "راهنما"]
            )

        safe_query = escape(query)

        try:
            docs = cls._execute_search(query, user_id, is_admin)
        except Exception as e:
            return Formatters.error_response(f"خطا در جستجو: {str(e)}")

        if not docs:
            return Formatters.response(
                f'<i class="fa-solid fa-magnifying-glass" '
                f'style="color:#94a3b8"></i> '
                f'<strong>نتیجه‌ای برای «{safe_query}» پیدا نشد.</strong>',
                "list", [],
                suggestions=["جستجوی دیگر", "کارهای من", "آمار کلی"]
            )

        return Formatters.doc_list(
            docs,
            f"نتایج جستجو برای «{safe_query}»",
            show_deadline=True,
            show_status=True,
        )

    @classmethod
    def _validate_query(cls, query):
        if not query:
            return None
        query = str(query).strip()
        if len(query) < cls.MIN_QUERY_LENGTH:
            return None
        if len(query) > cls.MAX_QUERY_LENGTH:
            query = query[:cls.MAX_QUERY_LENGTH]

        query = query.replace("%", "").replace("_", " ")
        if len(query.strip()) < cls.MIN_QUERY_LENGTH:
            return None
        return query.strip()

    @classmethod
    def _execute_search(cls, query, user_id, is_admin):
        conn = get_connection()
        try:
            like = f"%{query}%"
            conditions = []
            params = []

            for field in cls.SEARCH_FIELDS:
                conditions.append(f"d.{field} LIKE ?")
                params.append(like)

            where_clause = " OR ".join(conditions)

            sql = f"""
                SELECT d.id, d.subject, d.code_dfc, d.deadline,
                       d.date_received, d.date_referral,
                       d.project_name, d.contractor, d.contract_number,
                       s.title AS status_title, s.color AS status_color
                FROM documents d
                LEFT JOIN document_statuses s ON s.id = d.status_id
                WHERE ({where_clause})
            """

            if user_id and not is_admin:
                sql += " AND d.user_id = ?"
                params.append(user_id)

            sql += """
                ORDER BY 
                    CASE 
                        WHEN d.code_dfc = ? THEN 0
                        WHEN d.code_dfc LIKE ? THEN 1
                        ELSE 2
                    END,
                    d.id DESC
                LIMIT ?
            """
            params.extend([query, f"{query}%", cls.MAX_RESULTS])

            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()