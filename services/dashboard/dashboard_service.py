# ★ اضافه شدن date برای مقایسه تاریخ
from datetime import datetime, date
import jdatetime
from database.connection import get_connection


class DashboardService:
    # ★ اندازه صفحه برای AJAX
    PAGE_SIZE = 50

    # ★ آستانه هشدار مهلت (روز)
    DEADLINE_NEAR_THRESHOLD = 2

    # ★★★ مقادیر ممکن برای «در انتظار امضای مدیریت» ★★★
    MANAGER_APPROVAL_VALUES = [
        "در انتظار امضاي مديريت",   # با ي و ك عربی
        "در انتظار امضای مدیریت",   # با ی و ک فارسی
        "در انتظار تایید مدیریت",
        "در انتظار تاييد مديريت",
    ]

    # ★ فیلدهای قابل جستجو
    SEARCH_FIELDS = [
        "d.subject",
        "d.project_name",
        "d.contractor",
        "d.code_dfc",
        "d.automation_number",
        "d.contract_number",
        "d.contractor_letter_number",
        "d.expert_name",
        "d.Responsible_Party",
        "d.date_letter",
        "d.date_received",
        "d.date_referral",
        "d.deadline",
        "d.request_complete_docs",
        "d.complete_docs_by_contractor",
        "d.response_announce_date",
        "d.final_letter_number",
        "d.final_delay",
        "d.colleague",
        "d.doc_response_status",
    ]

    STATUS_CODES = [
        "completed",
        "in_progress",
        "informational",
        "stopped",
        "deleted",
    ]

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _safe_get(row, key, default=None):
        try:
            keys = row.keys()
        except AttributeError:
            return default
        if key in keys:
            return row[key]
        return default

    @staticmethod
    def _to_jalali_year(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return jdatetime.datetime.fromgregorian(datetime=value).year

        value = str(value).strip()
        if not value:
            return None
        value = value.replace("/", "-")
        try:
            parts = value.split("-")
            if len(parts) >= 3:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2].split(" ")[0])
                if year < 1700:
                    return year
                return jdatetime.date.fromgregorian(
                    year=year, month=month, day=day
                ).year
        except (ValueError, TypeError):
            return None
        return None

    @staticmethod
    def _to_jalali_str(value):
        if value is None or value == "":
            return ""
        try:
            if isinstance(value, datetime):
                jd = jdatetime.datetime.fromgregorian(datetime=value)
                return jd.strftime("%Y/%m/%d")
            value_str = str(value).strip().replace("/", "-")
            parts = value_str.split("-")
            if len(parts) >= 3:
                y = int(parts[0])
                m = int(parts[1])
                d = int(parts[2].split(" ")[0])
                if y < 1700:
                    return f"{y:04d}/{m:02d}/{d:02d}"
                jd = jdatetime.date.fromgregorian(year=y, month=m, day=d)
                return jd.strftime("%Y/%m/%d")
        except (ValueError, TypeError):
            return str(value)
        return str(value)

    # ★ تبدیل مقدار deadline به date میلادی برای مقایسه
    @staticmethod
    def _parse_deadline_to_date(value):
        """
        تبدیل مقدار deadline به آبجکت date میلادی برای مقایسه.
        ورودی می‌تونه شمسی (str) یا میلادی (datetime/str) باشه.
        """
        if value is None or value == "":
            return None

        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        value_str = str(value).strip().replace("/", "-")
        parts = value_str.split("-")
        if len(parts) < 3:
            return None

        try:
            y = int(parts[0])
            m = int(parts[1])
            d = int(parts[2].split(" ")[0])
        except (ValueError, TypeError):
            return None

        try:
            if y < 1700:
                # ★ تاریخ شمسی → تبدیل به میلادی
                jd = jdatetime.date(y, m, d)
                gd = jd.togregorian()
                return date(gd.year, gd.month, gd.day)
            else:
                # ★ تاریخ میلادی
                return date(y, m, d)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def normalize_search(value):
        value = str(value or "").strip().lower()
        value = value.replace("ي", "ی").replace("ك", "ک")
        return value

    @staticmethod
    def normalize_page(page):
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
        if page < 1:
            page = 1
        return page

    @staticmethod
    def get_year_range(year):
        if year == "all" or year is None:
            return None
        try:
            year = int(year)
        except (ValueError, TypeError):
            return None
        start_gregorian = jdatetime.date(year, 1, 1).togregorian()
        end_gregorian = jdatetime.date(year + 1, 1, 1).togregorian()
        return (
            start_gregorian.strftime("%Y/%m/%d"),
            end_gregorian.strftime("%Y/%m/%d"),
        )

    @staticmethod
    def normalize_response_status_text(value):
        """
        نرمال‌سازی متن وضعیت پاسخ مدرک (تبدیل ی/ک عربی به فارسی و strip)
        """
        if value is None:
            return ""
        value = str(value).strip()
        value = value.replace("ي", "ی").replace("ك", "ک")
        return value

    @staticmethod
    def is_manager_approval(value):
        """
        بررسی اینکه آیا مقدار doc_response_status برابر با یکی از مقادیر
        «در انتظار امضای مدیریت» هست یا نه (با نرمال‌سازی).
        """
        normalized = DashboardService.normalize_response_status_text(value)
        for possible in DashboardService.MANAGER_APPROVAL_VALUES:
            if normalized == DashboardService.normalize_response_status_text(possible):
                return True
        return False

    # ============================================================
    # ★★★ USER — اطلاعات کاربر جاری ★★★
    # ============================================================

    @staticmethod
    def get_user(user_id):
        """
        اطلاعات کاربر جاری (شامل avatar) رو برمی‌گردونه.
        """
        connection = get_connection()
        try:
            user = connection.execute(
                """
                SELECT id, full_name, username, avatar
                FROM users
                WHERE id = ?
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()

            if not user:
                return None

            return {
                "id": user["id"],
                "full_name": user["full_name"],
                "username": user["username"],
                "avatar": user["avatar"],
            }
        finally:
            connection.close()

    # ============================================================
    # YEARS
    # ============================================================

    @staticmethod
    def get_available_years(user_id):
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT DISTINCT date_received
                FROM documents
                WHERE user_id = ?
                AND date_received IS NOT NULL
                AND date_received != ''
                """,
                (user_id,),
            ).fetchall()
        finally:
            connection.close()

        years = set()
        for row in rows:
            year = DashboardService._to_jalali_year(row["date_received"])
            if year:
                years.add(year)
        return sorted(years, reverse=True)

    @staticmethod
    def normalize_year(user_id, requested_year):
        available_years = DashboardService.get_available_years(user_id)
        if requested_year in (None, "", "all"):
            return "all", available_years
        try:
            selected_year = int(requested_year)
        except (ValueError, TypeError):
            return "all", available_years
        if selected_year not in available_years:
            return "all", available_years
        return selected_year, available_years

    # ============================================================
    # ★★★ CONTRACTORS — لیست پیمانکاران یکتا ★★★
    # ============================================================

    @staticmethod
    def get_available_contractors(user_id, year_range=None):
        """لیست پیمانکاران یکتا برای فیلتر"""
        connection = get_connection()
        try:
            where_clauses = [
                "user_id = ?",
                "contractor IS NOT NULL",
                "contractor != ''",
            ]
            params = [user_id]

            if year_range:
                where_clauses.append(
                    "date_received >= ? AND date_received < ?"
                )
                params.extend([year_range[0], year_range[1]])

            where_sql = " AND ".join(where_clauses)

            rows = connection.execute(
                f"""
                SELECT DISTINCT contractor
                FROM documents
                WHERE {where_sql}
                ORDER BY contractor ASC
                """,
                params,
            ).fetchall()
        finally:
            connection.close()

        return [r["contractor"] for r in rows]

    # ============================================================
    # ★★★ GROUPS — لیست گروه‌های مدرک یکتا ★★★
    # ============================================================

    @staticmethod
    def get_available_groups(user_id, year_range=None):
        """لیست گروه‌های مدرک یکتا برای فیلتر"""
        connection = get_connection()
        try:
            where_clauses = [
                "user_id = ?",
                "document_group IS NOT NULL",
                "document_group != ''",
            ]
            params = [user_id]

            if year_range:
                where_clauses.append(
                    "date_received >= ? AND date_received < ?"
                )
                params.extend([year_range[0], year_range[1]])

            where_sql = " AND ".join(where_clauses)

            rows = connection.execute(
                f"""
                SELECT DISTINCT document_group
                FROM documents
                WHERE {where_sql}
                ORDER BY document_group ASC
                """,
                params,
            ).fetchall()
        finally:
            connection.close()

        return [r["document_group"] for r in rows]

    # ============================================================
    # ★★★ RESPONSE STATUSES — وضعیت‌های پاسخ مدرک ★★★
    # ============================================================

    @staticmethod
    def get_available_response_statuses(user_id, year_range=None):
        """لیست وضعیت‌های پاسخ مدرک یکتا برای فیلتر"""
        connection = get_connection()
        try:
            where_clauses = [
                "user_id = ?",
                "doc_response_status IS NOT NULL",
                "doc_response_status != ''",
            ]
            params = [user_id]

            if year_range:
                where_clauses.append(
                    "date_received >= ? AND date_received < ?"
                )
                params.extend([year_range[0], year_range[1]])

            where_sql = " AND ".join(where_clauses)

            rows = connection.execute(
                f"""
                SELECT DISTINCT doc_response_status
                FROM documents
                WHERE {where_sql}
                ORDER BY doc_response_status ASC
                """,
                params,
            ).fetchall()
        finally:
            connection.close()

        return [r["doc_response_status"] for r in rows]

    # ============================================================
    # ★★★ COUNT MANAGER APPROVAL — شمارش در انتظار امضای مدیریت ★★★
    # ============================================================

    @staticmethod
    def count_manager_approval(user_id, year_range=None):
        """
        تعداد اسنادی که وضعیت پاسخ مدرک آن‌ها «در انتظار امضای مدیریت» است.
        با نرمال‌سازی ي/ك عربی به ی/ک فارسی.
        """
        connection = get_connection()
        try:
            where_clauses = [
                "user_id = ?",
                "doc_response_status IS NOT NULL",
                "doc_response_status != ''",
            ]
            params = [user_id]

            if year_range:
                where_clauses.append(
                    "date_received >= ? AND date_received < ?"
                )
                params.extend([year_range[0], year_range[1]])

            where_sql = " AND ".join(where_clauses)

            # ★ نرمال‌سازی در SQL: ي → ی و ك → ک
            normalized_status = (
                "REPLACE(REPLACE(TRIM(doc_response_status), 'ي', 'ی'), 'ك', 'ک')"
            )

            # ★ ساخت شرط OR برای همه مقادیر ممکن
            or_conditions = []
            for val in DashboardService.MANAGER_APPROVAL_VALUES:
                normalized_val = DashboardService.normalize_response_status_text(val)
                or_conditions.append(f"{normalized_status} = ?")
                params.append(normalized_val)

            or_sql = "(" + " OR ".join(or_conditions) + ")"

            row = connection.execute(
                f"""
                SELECT COUNT(*) AS cnt
                FROM documents
                WHERE {where_sql} AND {or_sql}
                """,
                params,
            ).fetchone()

            return int(row["cnt"] or 0)
        finally:
            connection.close()

    # ============================================================
    # STATUSES
    # ============================================================

    @staticmethod
    def get_all_statuses():
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT id, title, code, color, sort_order
                FROM document_statuses
                WHERE is_active = 1
                ORDER BY sort_order ASC, id ASC
                """
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "code": r["code"],
                "color": r["color"],
                "sort_order": r["sort_order"],
            }
            for r in rows
        ]

    # ============================================================
    # ★★★ DEADLINE BREAKDOWN — تفکیک بر اساس وضعیت ★★★
    # ============================================================

    @staticmethod
    def get_deadline_breakdown_by_status(
        user_id, year_range=None, status_code="in_progress"
    ):
        """
        برای یک وضعیت سند (پیش‌فرض: in_progress)، اسنادش را به سه دسته تقسیم می‌کند:
        - overdue (گذشته از مهلت) → قرمز
        - near (نزدیک به مهلت ≤ threshold) → زرد
        - normal (فرصت دارد) → آبی

        جمع این سه دسته = تعداد کل اسناد آن وضعیت
        """
        today_gregorian = date.today()
        threshold = DashboardService.DEADLINE_NEAR_THRESHOLD

        connection = get_connection()
        try:
            where_clauses = [
                "d.user_id = ?",
                "d.deadline IS NOT NULL",
                "d.deadline != ''",
                "s.code = ?",
            ]
            params = [user_id, status_code]

            if year_range:
                where_clauses.append(
                    "d.date_received >= ? AND d.date_received < ?"
                )
                params.extend([year_range[0], year_range[1]])

            where_sql = " AND ".join(where_clauses)

            rows = connection.execute(
                f"""
                SELECT
                    d.id,
                    d.deadline,
                    s.code AS status_code
                FROM documents d
                LEFT JOIN document_statuses s ON d.status_id = s.id
                WHERE {where_sql}
                """,
                params,
            ).fetchall()
        finally:
            connection.close()

        breakdown = {}

        for row in rows:
            sc = row["status_code"] or "unknown"

            if sc not in breakdown:
                breakdown[sc] = {
                    "overdue": 0,
                    "near": 0,
                    "normal": 0,
                    "manager_approval": 0,   # ★ جدید
                    "total": 0,
                    "_overdue_days": [],
                    "_near_days": [],
                    "_normal_days": [],
                }

            deadline_date = DashboardService._parse_deadline_to_date(
                row["deadline"]
            )
            if not deadline_date:
                continue

            days_left = (deadline_date - today_gregorian).days

            if days_left < 0:
                breakdown[sc]["overdue"] += 1
                breakdown[sc]["_overdue_days"].append(abs(days_left))
            elif days_left <= threshold:
                breakdown[sc]["near"] += 1
                breakdown[sc]["_near_days"].append(days_left)
            else:
                breakdown[sc]["normal"] += 1
                breakdown[sc]["_normal_days"].append(days_left)

            breakdown[sc]["total"] += 1

        # ★ تبدیل لیست‌ها به min و max
        for sc, data in breakdown.items():
            overdue_days = data.pop("_overdue_days", [])
            near_days = data.pop("_near_days", [])
            normal_days = data.pop("_normal_days", [])

            data["overdue_days"] = min(overdue_days) if overdue_days else 0
            data["overdue_days_max"] = max(overdue_days) if overdue_days else 0
            data["near_days"] = min(near_days) if near_days else 0
            data["near_days_max"] = max(near_days) if near_days else 0
            data["normal_days"] = min(normal_days) if normal_days else 0
            data["normal_days_max"] = max(normal_days) if normal_days else 0

        return breakdown

    # ============================================================
    # ★★★ DEADLINE ALERTS — هشدار مهلت ★★★
    # ============================================================

    @staticmethod
    def get_deadline_alerts(user_id, year_range=None):
        """
        اسناد in_progress که:
        - مهلت (deadline) دارند
        - تا مهلت‌شان threshold روز یا کمتر مانده (شامل گذشته)
        """
        today_gregorian = date.today()
        threshold = DashboardService.DEADLINE_NEAR_THRESHOLD

        connection = get_connection()
        try:
            where_clauses = [
                "d.user_id = ?",
                "d.deadline IS NOT NULL",
                "d.deadline != ''",
                "s.code = 'in_progress'",
            ]
            params = [user_id]

            if year_range:
                where_clauses.append(
                    "d.date_received >= ? AND d.date_received < ?"
                )
                params.extend([year_range[0], year_range[1]])

            where_sql = " AND ".join(where_clauses)

            rows = connection.execute(
                f"""
                SELECT
                    d.id,
                    d.subject,
                    d.project_name,
                    d.contractor,
                    d.code_dfc,
                    d.deadline,
                    d.status_id,
                    s.title AS status_title,
                    s.code AS status_code,
                    s.color AS status_color
                FROM documents d
                LEFT JOIN document_statuses s ON d.status_id = s.id
                WHERE {where_sql}
                ORDER BY d.deadline ASC
                """,
                params,
            ).fetchall()
        finally:
            connection.close()

        overdue = []
        near_deadline = []

        for row in rows:
            deadline_date = DashboardService._parse_deadline_to_date(
                row["deadline"]
            )
            if not deadline_date:
                continue

            days_left = (deadline_date - today_gregorian).days

            doc = {
                "id": row["id"],
                "subject": row["subject"],
                "project_name": row["project_name"],
                "contractor": row["contractor"],
                "code_dfc": row["code_dfc"],
                "deadline": row["deadline"],
                "deadline_jalali": DashboardService._to_jalali_str(
                    row["deadline"]
                ),
                "status_title": row["status_title"],
                "status_code": row["status_code"],
                "status_color": row["status_color"],
                "days_left": days_left,
            }

            if days_left < 0:
                doc["alert_type"] = "overdue"
                doc["days_text"] = f"{abs(days_left)} روز گذشته"
                overdue.append(doc)
            elif days_left <= threshold:
                doc["alert_type"] = "near"
                if days_left == 0:
                    doc["days_text"] = "امروز"
                elif days_left == 1:
                    doc["days_text"] = "فردا"
                else:
                    doc["days_text"] = f"{days_left} روز مانده"
                near_deadline.append(doc)

        return {
            "overdue": overdue,
            "near_deadline": near_deadline,
            "counts": {
                "overdue": len(overdue),
                "near_deadline": len(near_deadline),
                "total": len(overdue) + len(near_deadline),
            },
        }

    # ============================================================
    # ★★★ META — برای HTML اولیه (سبک) ★★★
    # ============================================================

    @staticmethod
    def get_dashboard_meta(user_id, requested_year="all"):
        """
        فقط متادیتا: user + statuses + شمارش‌ها + سال‌ها + total
        + هشدارهای مهلت (تفکیک‌شده بر اساس وضعیت)
        + تعداد در انتظار امضای مدیریت
        """
        connection = get_connection()
        try:
            user = connection.execute(
                """
                SELECT id, full_name, username, avatar
                FROM users
                WHERE id = ?
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()

            selected_year, available_years = (
                DashboardService.normalize_year(user_id, requested_year)
            )
            year_range = DashboardService.get_year_range(selected_year)

            where_clauses = ["d.user_id = ?"]
            params = [user_id]

            if year_range:
                where_clauses.append(
                    "d.date_received >= ? AND d.date_received < ?"
                )
                params.extend([year_range[0], year_range[1]])

            where_sql = " AND ".join(where_clauses)

            # ★ شمارش کل
            total_row = connection.execute(
                f"SELECT COUNT(*) AS total FROM documents d WHERE {where_sql}",
                params,
            ).fetchone()
            total = int(total_row["total"] or 0)

            # ★ شمارش per status
            status_rows = connection.execute(
                f"""
                SELECT
                    s.id, s.title, s.code, s.color, s.sort_order,
                    COUNT(d.id) AS count
                FROM documents d
                LEFT JOIN document_statuses s ON d.status_id = s.id
                WHERE {where_sql} AND s.id IS NOT NULL
                GROUP BY s.id, s.title, s.code, s.color, s.sort_order
                ORDER BY s.sort_order ASC, s.id ASC
                """,
                params,
            ).fetchall()
        finally:
            connection.close()

        # ★ همه statuses (حتی با count=0)
        all_statuses = DashboardService.get_all_statuses()
        count_map = {r["id"]: int(r["count"] or 0) for r in status_rows}

        # ★ تفکیک هشدار فقط برای in_progress (با احترام به فیلتر سال)
        deadline_breakdown = DashboardService.get_deadline_breakdown_by_status(
            user_id, year_range=year_range, status_code="in_progress"
        )

        # ★★★ تعداد در انتظار امضای مدیریت ★★★
        manager_approval_count = DashboardService.count_manager_approval(
            user_id, year_range=year_range
        )

        statuses = []
        for s in all_statuses:
            bd = {}
            if s["code"] == "in_progress":
                bd = deadline_breakdown.get("in_progress", {}).copy()
                # ★ اضافه کردن تعداد در انتظار امضای مدیریت به breakdown
                bd["manager_approval"] = manager_approval_count

            statuses.append({
                "id": s["id"],
                "title": s["title"],
                "code": s["code"],
                "color": s["color"],
                "sort_order": s["sort_order"],
                "count": count_map.get(s["id"], 0),
                "deadline_breakdown": bd,
            })

        # ★ هشدارهای مهلت (لیست کامل برای مودال)
        deadline_alerts = DashboardService.get_deadline_alerts(
            user_id, year_range=year_range
        )

        return {
            "user": dict(user) if user else None,
            "available_years": available_years,
            "selected_year": selected_year,
            "statuses": statuses,
            "total": total,
            "deadline_alerts": deadline_alerts,
            "manager_approval_count": manager_approval_count,   # ★ جدید
        }

    # ============================================================
    # ★★★ ITEMS JSON — برای AJAX ★★★
    # ============================================================

    @staticmethod
    def build_search_sql(search):
        if not search:
            return "", []
        conditions = []
        params = []
        for field in DashboardService.SEARCH_FIELDS:
            normalized_field = (
                f"REPLACE("
                f"REPLACE("
                f"LOWER(COALESCE({field}, '')),"
                f"'ي', 'ی'"
                f"),"
                f"'ك', 'ک'"
                f")"
            )
            conditions.append(f"{normalized_field} LIKE ?")
            params.append(f"%{search}%")
        return ("(" + " OR ".join(conditions) + ")", params)

    @staticmethod
    def get_documents_json(
        user_id,
        requested_year="all",
        search="",
        page=1,
        status_code=None,
        deadline_filter=None,       # "overdue" | "near" | "normal" | "manager_approval"
    ):
        connection = get_connection()
        try:
            selected_year, _ = DashboardService.normalize_year(
                user_id, requested_year
            )
            year_range = DashboardService.get_year_range(selected_year)
            page = DashboardService.normalize_page(page)
            search = DashboardService.normalize_search(search)

            where_clauses = ["d.user_id = ?"]
            base_params = [user_id]

            if year_range:
                where_clauses.append(
                    "d.date_received >= ? AND d.date_received < ?"
                )
                base_params.extend([year_range[0], year_range[1]])

            if status_code:
                where_clauses.append("s.code = ?")
                base_params.append(status_code)

            search_sql, search_params = DashboardService.build_search_sql(search)
            if search_sql:
                where_clauses.append(search_sql)
                base_params.extend(search_params)

            where_sql = " AND ".join(where_clauses)

            # ★★★ فیلتر بر اساس نوع مهلت (فقط روی in_progress) ★★★
            if deadline_filter in ("overdue", "near", "normal"):
                if not status_code:
                    status_code = "in_progress"
                    where_clauses.append("s.code = ?")
                    base_params.append("in_progress")
                    where_sql = " AND ".join(where_clauses)

                today = date.today()
                threshold = DashboardService.DEADLINE_NEAR_THRESHOLD

                probe_rows = connection.execute(
                    f"""
                    SELECT d.id, d.deadline
                    FROM documents d
                    LEFT JOIN document_statuses s ON d.status_id = s.id
                    WHERE {where_sql}
                      AND d.deadline IS NOT NULL
                      AND d.deadline != ''
                    """,
                    base_params,
                ).fetchall()

                matched_ids = []
                for r in probe_rows:
                    dl = DashboardService._parse_deadline_to_date(r["deadline"])
                    if not dl:
                        continue
                    days_left = (dl - today).days

                    if deadline_filter == "overdue" and days_left < 0:
                        matched_ids.append(r["id"])
                    elif deadline_filter == "near" and 0 <= days_left <= threshold:
                        matched_ids.append(r["id"])
                    elif deadline_filter == "normal" and days_left > threshold:
                        matched_ids.append(r["id"])

                if not matched_ids:
                    return {
                        "success": True,
                        "records": [],
                        "total": 0,
                        "page": 1,
                        "page_size": DashboardService.PAGE_SIZE,
                        "total_pages": 1,
                        "has_more": False,
                        "selected_year": selected_year,
                        "status_code": status_code,
                        "search": search,
                        "deadline_filter": deadline_filter,
                    }

                placeholders = ",".join(["?"] * len(matched_ids))
                where_clauses.append(f"d.id IN ({placeholders})")
                base_params.extend(matched_ids)
                where_sql = " AND ".join(where_clauses)

            # ★★★ فیلتر در انتظار امضای مدیریت ★★★
            elif deadline_filter == "manager_approval":
                # ★ نرمال‌سازی ي/ك عربی به ی/ک فارسی
                normalized_field = (
                    "REPLACE(REPLACE(TRIM(d.doc_response_status), 'ي', 'ی'), 'ك', 'ک')"
                )

                or_conditions = []
                for val in DashboardService.MANAGER_APPROVAL_VALUES:
                    normalized_val = DashboardService.normalize_response_status_text(val)
                    or_conditions.append(f"{normalized_field} = ?")
                    base_params.append(normalized_val)

                or_sql = "(" + " OR ".join(or_conditions) + ")"
                where_clauses.append(or_sql)
                where_sql = " AND ".join(where_clauses)

            # ★★★ [FIX] لیست را بدون ORDER BY و LIMIT می‌گیریم
            # (چون مرتب‌سازی بر اساس تاریخ ارجاع در پایتون انجام می‌شود
            #  و ممکن است تاریخ‌ها شمسی باشند که SQLite نمی‌تواند درست مرتب کند)
            rows = connection.execute(
                f"""
                SELECT
                    d.*,
                    u.full_name AS user_full_name,
                    s.title AS status_title,
                    s.code AS status_code,
                    s.color AS status_color,
                    a.title AS area_title,
                    a.code AS area_code,
                    dep.title AS department_title,
                    dep.code AS department_code
                FROM documents d
                LEFT JOIN users u ON d.user_id = u.id
                LEFT JOIN document_statuses s ON d.status_id = s.id
                LEFT JOIN areas a ON d.area_id = a.id
                LEFT JOIN departments dep ON d.department_id = dep.id
                WHERE {where_sql}
                """,
                base_params,
            ).fetchall()

            # ★ تبدیل Row → dict + تاریخ شمسی + days_left
            today_for_days = date.today()
            all_documents = []
            for row in rows:
                doc = dict(row)
                doc["date_letter_jalali"] = DashboardService._to_jalali_str(
                    DashboardService._safe_get(row, "date_letter")
                )
                doc["date_received_jalali"] = DashboardService._to_jalali_str(
                    DashboardService._safe_get(row, "date_received")
                )
                doc["date_referral_jalali"] = DashboardService._to_jalali_str(
                    DashboardService._safe_get(row, "date_referral")
                )
                doc["deadline_jalali"] = DashboardService._to_jalali_str(
                    DashboardService._safe_get(row, "deadline")
                )
                doc["created_at_jalali"] = DashboardService._to_jalali_str(
                    DashboardService._safe_get(row, "created_at")
                )

                # ★ محاسبه روزهای باقیمانده تا مهلت
                dl_date = DashboardService._parse_deadline_to_date(
                    DashboardService._safe_get(row, "deadline")
                )
                if dl_date:
                    doc["days_left"] = (dl_date - today_for_days).days
                else:
                    doc["days_left"] = None

                all_documents.append(doc)

            # ★★★ [NEW] مرتب‌سازی بر اساس تاریخ ارجاع (آخرین ارجاع بالا) ★★★
            def _sort_key(doc):
                """
                اسناد با تاریخ ارجاع معتبر اول، سپس بر اساس تاریخ نزولی
                (جدیدترین بالا). اسنادی که تاریخ ارجاع ندارند در انتها.
                """
                ref_date = DashboardService._parse_deadline_to_date(
                    doc.get("date_referral")
                )
                if ref_date is None:
                    # ★ (1, ...) → اسناد بدون تاریخ بعد از همه
                    return (1, 0)
                # ★ نزولی: date معکوس
                return (0, -ref_date.toordinal())

            all_documents.sort(key=_sort_key)

            # ★★★ حالا صفحه‌بندی روی لیست مرتب‌شده ★★★
            total = len(all_documents)
            page_size = DashboardService.PAGE_SIZE
            total_pages = max(1, (total + page_size - 1) // page_size)
            if page > total_pages:
                page = total_pages
            offset = (page - 1) * page_size

            documents = all_documents[offset: offset + page_size]

            return {
                "success": True,
                "records": documents,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_more": page < total_pages,
                "selected_year": selected_year,
                "status_code": status_code,
                "search": search,
                "deadline_filter": deadline_filter,
            }
        finally:
            connection.close()