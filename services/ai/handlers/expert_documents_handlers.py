"""
Expert Documents Handlers - اسناد کارشناسان
==============================================
★ سرویس: DepartmentExpertDocumentsService
★ برای سوالات «اسناد کارشناس X چیه؟»
"""
from html import escape

from services.ai.registry import IntentRegistry
from services.ai.formatters import Formatters
from database.connection import get_connection

from services.departments.department_expert_documents_service import (
    DepartmentExpertDocumentsService,
)


class ExpertDocumentsHandlers:
    """اسناد کارشناسان در دپارتمان‌ها"""

    # ============================================================
    # ★ Helper: پیدا کردن کارشناس با نام
    # ============================================================
    @staticmethod
    def _find_expert_by_name(name):
        """
        با نام کاربر، کارشناس رو پیدا می‌کنه
        Returns: dict یا None
        """
        if not name:
            return None

        conn = get_connection()
        try:
            # ★ جستجوی مشابه با نرمال‌سازی
            row = conn.execute("""
                SELECT id, full_name, username, department_id
                FROM users
                WHERE (
                    REPLACE(REPLACE(LOWER(full_name), 'ي', 'ی'), 'ك', 'ک')
                    LIKE ?
                    OR REPLACE(REPLACE(LOWER(username), 'ي', 'ی'), 'ك', 'ک')
                    LIKE ?
                )
                AND is_active = 1
                LIMIT 1
            """, (f"%{name.lower()}%", f"%{name.lower()}%")).fetchone()

            if row:
                return dict(row)

            # ★ اگه پیدا نشد، شاید با نام اول (first name) جستجو کرده
            first_word = name.split()[0] if name.split() else name
            row = conn.execute("""
                SELECT id, full_name, username, department_id
                FROM users
                WHERE full_name LIKE ?
                AND is_active = 1
                LIMIT 1
            """, (f"%{first_word}%",)).fetchone()

            return dict(row) if row else None
        finally:
            conn.close()

    # ============================================================
    # ★ ۱. شمارش اسناد کارشناس
    # ============================================================
    @IntentRegistry.register(
        name="count_expert_documents",
        patterns=[
            r"(چند|تعداد|شمار)\s*(سند|کار|پرونده)\s*(کارشناس|آقای|خانم|مهندس)\s+(?P<expert>[\u0600-\u06FF\w\s]{2,30})",
            r"(چند|تعداد)\s*(سند|کار)\s+(?P<expert>[\u0600-\u06FF\w\s]{2,30})\s*(داره|دارد|هست)",
        ],
        priority=87,
        confidence=0.88,
        description="شمارش اسناد یک کارشناس",
    )
    @staticmethod
    def handle_count_expert_documents(question, entities, user_id, is_admin):
        expert_name = (entities.get("expert") or "").strip()
        if not expert_name:
            return Formatters.error_response("نام کارشناس مشخص نشد.")

        expert = ExpertDocumentsHandlers._find_expert_by_name(expert_name)
        if not expert:
            return Formatters.error_response(
                f'کارشناسی با نام «{escape(expert_name)}» پیدا نشد.',
                suggestions=["پرمشغله‌ترین کارشناس کیست؟", "آمار کلی"],
            )

        department_id = expert.get("department_id")
        if not department_id:
            return Formatters.error_response(
                f'کارشناس «{escape(expert["full_name"])}» به دپارتمانی متصل نیست.'
            )

        try:
            meta = DepartmentExpertDocumentsService.get_documents_meta(
                department_id=department_id,
                expert_id=expert["id"],
                requested_year="all",
            )
        except Exception as e:
            return Formatters.error_response(
                f"خطا در دریافت اطلاعات: {str(e)}"
            )

        if not meta:
            return Formatters.error_response("اطلاعات کارشناس پیدا نشد.")

        total = meta["total"]
        statuses = meta.get("statuses", [])

        lines = [
            f'<i class="fa-solid fa-user" style="color:#3D8499"></i> '
            f'<strong>{escape(expert["full_name"])}</strong> '
            f'در دپارتمان «<strong>{escape(meta["department"]["title"])}</strong>»\n'
            f'📊 مجموع اسناد: <strong class="num-highlight">{total}</strong>\n'
        ]

        if statuses:
            lines.append("")
            lines.append('<strong>به تفکیک وضعیت:</strong>')
            for s in statuses:
                color = s.get("color") or "#3D8499"
                lines.append(
                    f'<i class="fa-solid fa-circle-dot" '
                    f'style="color:{color};font-size:9px"></i> '
                    f'{escape(s["title"])}: <strong>{s["count"]}</strong>'
                )

        return Formatters.response(
            "\n".join(lines),
            "count",
            [{"expert": expert["full_name"], "total": total}],
            suggestions=[
                f"لیست اسناد {expert['full_name']}",
                "پرمشغله‌ترین کارشناس کیست؟",
                "آمار کلی",
            ],
        )

    # ============================================================
    # ★ ۲. لیست اسناد کارشناس
    # ============================================================
    @IntentRegistry.register(
        name="list_expert_documents",
        patterns=[
            r"(لیست|نشون|نمایش|بگو|بیار)\s*اسناد\s*(کارشناس|آقای|خانم|مهندس)?\s*(?P<expert>[\u0600-\u06FF\w\s]{2,30})",
            r"اسناد\s+(?P<expert>[\u0600-\u06FF\w\s]{2,30})\s*(چیا|چی|چیه|کدوم)",
        ],
        priority=88,
        confidence=0.88,
        description="لیست اسناد یک کارشناس",
    )
    @staticmethod
    def handle_list_expert_documents(question, entities, user_id, is_admin):
        expert_name = (entities.get("expert") or "").strip()
        if not expert_name:
            return Formatters.error_response("نام کارشناس مشخص نشد.")

        expert = ExpertDocumentsHandlers._find_expert_by_name(expert_name)
        if not expert:
            return Formatters.error_response(
                f'کارشناسی با نام «{escape(expert_name)}» پیدا نشد.',
                suggestions=["پرمشغله‌ترین کارشناس کیست؟"],
            )

        department_id = expert.get("department_id")
        if not department_id:
            return Formatters.error_response(
                f'کارشناس «{escape(expert["full_name"])}» به دپارتمانی متصل نیست.'
            )

        try:
            data = DepartmentExpertDocumentsService.get_documents_json(
                department_id=department_id,
                expert_id=expert["id"],
                requested_year="all",
                page=1,
            )
        except Exception as e:
            return Formatters.error_response(
                f"خطا در دریافت اسناد: {str(e)}"
            )

        if not data or not data.get("records"):
            return Formatters.response(
                f'<i class="fa-solid fa-inbox" style="color:#94a3b8"></i> '
                f'کارشناس <strong>{escape(expert["full_name"])}</strong> '
                f'هیچ سندی ندارد.',
                "list",
                [],
                suggestions=["آمار کلی", "لیست کارشناسان"],
            )

        # ★ حداکثر ۲۰ سند
        records = data["records"][:20]
        total = data["total"]

        lines = [
            f'<i class="fa-solid fa-file-lines" style="color:#3D8499"></i> '
            f'<strong>اسناد {escape(expert["full_name"])}</strong> '
            f'<span class="text-muted">({total} سند، نمایش {len(records)})</span>\n'
        ]

        for i, d in enumerate(records, 1):
            subject = escape(d.get("subject") or "بدون موضوع")
            code = escape(d.get("code_dfc") or "-")
            status = escape(d.get("status_title") or "-")
            deadline = escape(d.get("deadline_jalali") or "")
            doc_id = d.get("id")

            lines.append(
                f'<span class="doc-num">{i}.</span> '
                f'<a href="#" class="doc-link" data-doc-id="{doc_id}">'
                f'<i class="fa-solid fa-file-lines"></i> {subject}'
                f'</a>'
            )

            meta_parts = [
                f'<i class="fa-solid fa-bookmark"></i> {code}',
                f'<i class="fa-solid fa-circle-dot"></i> {status}',
            ]
            if deadline:
                meta_parts.append(
                    f'<i class="fa-solid fa-clock"></i> {deadline}'
                )

            lines.append(
                f'<span class="doc-meta">'
                f'{" &nbsp;•&nbsp; ".join(meta_parts)}'
                f'</span>'
            )
            lines.append("")

        return Formatters.response(
            "\n".join(lines),
            "list",
            records,
            suggestions=[
                f"شمارش اسناد {expert['full_name']}",
                "پرمشغله‌ترین کارشناس کیست؟",
                "آمار کلی",
            ],
        )

    # ============================================================
    # ★ ۳. وضعیت اسناد کارشناس
    # ============================================================
    @IntentRegistry.register(
        name="expert_status_breakdown",
        patterns=[
            r"وضعیت\s*اسناد\s*(کارشناس|آقای|خانم)?\s*(?P<expert>[\u0600-\u06FF\w\s]{2,30})",
            r"اسناد\s+(?P<expert>[\u0600-\u06FF\w\s]{2,30})\s*(به تفکیک|از نظر)\s*وضعیت",
        ],
        priority=86,
        confidence=0.87,
        description="تفکیک وضعیت اسناد کارشناس",
    )
    @staticmethod
    def handle_expert_status_breakdown(question, entities, user_id, is_admin):
        expert_name = (entities.get("expert") or "").strip()
        if not expert_name:
            return Formatters.error_response("نام کارشناس مشخص نشد.")

        expert = ExpertDocumentsHandlers._find_expert_by_name(expert_name)
        if not expert:
            return Formatters.error_response(
                f'کارشناسی با نام «{escape(expert_name)}» پیدا نشد.'
            )

        department_id = expert.get("department_id")
        if not department_id:
            return Formatters.error_response(
                f'کارشناس «{escape(expert["full_name"])}» به دپارتمانی متصل نیست.'
            )

        try:
            meta = DepartmentExpertDocumentsService.get_documents_meta(
                department_id=department_id,
                expert_id=expert["id"],
                requested_year="all",
            )
        except Exception as e:
            return Formatters.error_response(f"خطا: {str(e)}")

        if not meta:
            return Formatters.error_response("اطلاعات پیدا نشد.")

        statuses = meta.get("statuses", [])
        total = meta["total"]

        if not statuses:
            return Formatters.empty_response(
                f'هیچ سندی برای {escape(expert["full_name"])} یافت نشد.'
            )

        items = [
            {
                "label": s["title"],
                "value": s["count"],
                "color": s.get("color") or "#3D8499",
            }
            for s in statuses
        ]

        lines = [
            f'<i class="fa-solid fa-chart-pie" style="color:#667eea"></i> '
            f'<strong>وضعیت اسناد {escape(expert["full_name"])}</strong> '
            f'<span class="text-muted">(مجموع: {total})</span>\n'
        ]

        for it in items:
            color = it.get("color") or "#3D8499"
            percent = round(it["value"] / total * 100, 1) if total else 0
            lines.append(
                f'<i class="fa-solid fa-circle" '
                f'style="color:{color};font-size:9px"></i> '
                f'{escape(it["label"])}: '
                f'<strong>{it["value"]}</strong> '
                f'<span class="text-muted">({percent}٪)</span>'
            )

        return Formatters.response(
            "\n".join(lines),
            "chart",
            items,
            suggestions=[
                f"لیست اسناد {expert['full_name']}",
                "پرمشغله‌ترین کارشناس کیست؟",
            ],
        )

    # ============================================================
    # ★ ۴. کارشناسان یک دپارتمان
    # ============================================================
    @IntentRegistry.register(
        name="department_experts",
        patterns=[
            r"(کارشناسان|کارشناس‌های|پرسنل)\s*دپارتمان\s+(?P<dept>[\u0600-\u06FF\w\s]{2,30})",
            r"دپارتمان\s+(?P<dept>[\u0600-\u06FF\w\s]{2,30})\s*(چند|چیا)\s*کارشناس",
        ],
        priority=87,
        confidence=0.88,
        description="کارشناسان یک دپارتمان",
    )
    @staticmethod
    def handle_department_experts(question, entities, user_id, is_admin):
        dept_name = (entities.get("dept") or "").strip()
        if not dept_name:
            return Formatters.error_response("نام دپارتمان مشخص نشد.")

        conn = get_connection()
        try:
            # پیدا کردن دپارتمان
            dept = conn.execute("""
                SELECT id, title
                FROM departments
                WHERE REPLACE(REPLACE(LOWER(title), 'ي', 'ی'), 'ك', 'ک')
                      LIKE ?
                AND is_active = 1
                LIMIT 1
            """, (f"%{dept_name.lower()}%",)).fetchone()

            if not dept:
                return Formatters.error_response(
                    f'دپارتمانی با نام «{escape(dept_name)}» پیدا نشد.'
                )

            # کارشناسان این دپارتمان با تعداد اسناد
            rows = conn.execute("""
                SELECT
                    u.id,
                    u.full_name,
                    u.username,
                    COUNT(d.id) AS documents_count
                FROM users u
                LEFT JOIN documents d ON d.user_id = u.id
                WHERE u.department_id = ?
                  AND u.is_active = 1
                GROUP BY u.id
                ORDER BY documents_count DESC
            """, (dept["id"],)).fetchall()

        except Exception as e:
            return Formatters.error_response(f"خطا: {str(e)}")
        finally:
            conn.close()

        if not rows:
            return Formatters.empty_response(
                f'دپارتمان «{escape(dept["title"])}» کارشناسی ندارد.'
            )

        items = [
            {
                "label": r["full_name"] or r["username"] or "بدون نام",
                "value": r["documents_count"],
            }
            for r in rows
        ]

        lines = [
            f'<i class="fa-solid fa-users" style="color:#3D8499"></i> '
            f'<strong>کارشناسان دپارتمان {escape(dept["title"])}</strong> '
            f'<span class="text-muted">({len(items)} نفر)</span>\n'
        ]

        medals = ["fa-medal", "fa-award", "fa-star"]

        for i, it in enumerate(items):
            if i < 3:
                icon = medals[i]
                color = "#f59e0b"
            else:
                icon = "fa-user"
                color = "#3D8499"

            lines.append(
                f'<i class="fa-solid {icon}" style="color:{color}"></i> '
                f'<strong>{escape(it["label"])}</strong>: '
                f'<strong class="num-highlight">{it["value"]}</strong> سند'
            )

        return Formatters.response(
            "\n".join(lines),
            "list",
            items,
            suggestions=[
                "پرمشغله‌ترین کارشناس کیست؟",
                "آمار کلی",
            ],
        )