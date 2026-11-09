from datetime import datetime
import jdatetime
from database.connection import get_connection


class DepartmentExpertDocumentsService:
    # ★ برای AJAX کوچیک‌تر
    PAGE_SIZE = 50

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
        "d.colleague"
    ]

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _safe_get(row, key, default=None):
        """
        خوندن امن از sqlite3.Row.
        اگه ستون وجود نداشت، default برمی‌گردونه.
        """
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
                    year=year,
                    month=month,
                    day=day
                ).year
        except (ValueError, TypeError):
            return None
        return None

    @staticmethod
    def _to_jalali_str(value):
        """
        تاریخ میلادی/شمسی رو به رشته شمسی YYYY/MM/DD تبدیل می‌کنه.
        برای نمایش در JSON.
        """
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

    # ============================================================
    # GETTERS
    # ============================================================

    @staticmethod
    def get_department(connection, department_id):
        return connection.execute(
            """
            SELECT
                id,
                title,
                code
            FROM departments
            WHERE id = ?
            LIMIT 1
            """,
            (department_id,)
        ).fetchone()

    @staticmethod
    def get_expert(
        connection,
        department_id,
        expert_id,
        area_id=None,
        year_range=None
    ):
        # ★ ۱) کاربر (بدون JOIN)
        user = connection.execute(
            """
            SELECT id, full_name, username, avatar, gender
            FROM users
            WHERE id = ?
            LIMIT 1
            """,
            (expert_id,)
        ).fetchone()

        if not user:
            return None

        # ★ ۲) تعداد اسناد با فیلتر
        doc_where = ["d.user_id = ?", "d.department_id = ?"]
        doc_params = [expert_id, department_id]

        if area_id is not None:
            doc_where.append("d.area_id = ?")
            doc_params.append(area_id)

        if year_range:
            doc_where.append("d.date_received >= ? AND d.date_received < ?")
            doc_params.extend([year_range[0], year_range[1]])

        doc_where_sql = " AND ".join(doc_where)

        count_row = connection.execute(
            f"""
            SELECT COUNT(d.id) AS document_count
            FROM documents d
            WHERE {doc_where_sql}
            """,
            doc_params
        ).fetchone()

        document_count = int(count_row["document_count"] or 0) if count_row else 0

        return {
            "id": user["id"],
            "full_name": user["full_name"],
            "username": user["username"],
            "avatar": user["avatar"],
            "gender": user["gender"] or "male",
            "document_count": document_count
        }

    @staticmethod
    def build_search_sql(search):
        if not search:
            return "", []

        conditions = []
        params = []

        for field in DepartmentExpertDocumentsService.SEARCH_FIELDS:
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
    def get_available_years(connection, department_id, expert_id, area_id=None):
        where_clauses = [
            "department_id = ?",
            "user_id = ?",
            "date_received IS NOT NULL",
            "date_received != ''"
        ]
        params = [department_id, expert_id]

        if area_id is not None:
            where_clauses.append("area_id = ?")
            params.append(area_id)

        where_sql = " AND ".join(where_clauses)

        rows = connection.execute(
            f"""
            SELECT DISTINCT date_received
            FROM documents
            WHERE {where_sql}
            """,
            params
        ).fetchall()

        years = set()
        for row in rows:
            year = DepartmentExpertDocumentsService._to_jalali_year(
                row["date_received"]
            )
            if year:
                years.add(year)

        return sorted(years, reverse=True)

    @staticmethod
    def normalize_year(connection, department_id, expert_id, requested_year, area_id=None):
        available_years = (
            DepartmentExpertDocumentsService.get_available_years(
                connection, department_id, expert_id, area_id=area_id
            )
        )

        if requested_year in (None, "", "all"):
            return "all", available_years

        try:
            selected_year = int(requested_year)
        except (ValueError, TypeError):
            return "all", available_years

        if selected_year not in available_years:
            return "all", available_years

        return selected_year, available_years

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
            end_gregorian.strftime("%Y/%m/%d")
        )

    @staticmethod
    def get_statuses(connection, where_sql, params):
        rows = connection.execute(
            f"""
            SELECT
                s.id,
                s.title,
                s.code,
                s.color,
                COUNT(d.id) AS count
            FROM documents d
            LEFT JOIN document_statuses s
                ON d.status_id = s.id
            WHERE {where_sql}
            AND s.id IS NOT NULL
            GROUP BY s.id, s.title, s.code, s.color
            ORDER BY s.id ASC
            """,
            params
        ).fetchall()

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "code": row["code"],
                "color": row["color"],
                "count": int(row["count"] or 0)
            }
            for row in rows
        ]

    # ============================================================
    # ★★★ GET DOCUMENTS META — بدون لیست اسناد (سریع) ★★★
    # ============================================================

    @staticmethod
    def get_documents_meta(
        department_id,
        expert_id,
        requested_year="all",
        area_id=None
    ):
        connection = get_connection()

        try:
            department = DepartmentExpertDocumentsService.get_department(
                connection, department_id
            )
            if not department:
                return None

            selected_year, available_years = (
                DepartmentExpertDocumentsService.normalize_year(
                    connection, department_id, expert_id,
                    requested_year, area_id=area_id
                )
            )

            year_range = DepartmentExpertDocumentsService.get_year_range(
                selected_year
            )

            expert = DepartmentExpertDocumentsService.get_expert(
                connection, department_id, expert_id,
                area_id=area_id, year_range=year_range
            )
            if not expert:
                return None

            where_clauses = ["d.department_id = ?", "d.user_id = ?"]
            base_params = [department_id, expert_id]

            if area_id is not None:
                where_clauses.append("d.area_id = ?")
                base_params.append(area_id)

            if year_range:
                where_clauses.append(
                    "d.date_received >= ? AND d.date_received < ?"
                )
                base_params.extend([year_range[0], year_range[1]])

            where_sql = " AND ".join(where_clauses)

            statuses = DepartmentExpertDocumentsService.get_statuses(
                connection, where_sql, base_params
            )

            total_row = connection.execute(
                f"SELECT COUNT(*) AS total FROM documents d WHERE {where_sql}",
                base_params
            ).fetchone()
            total = int(total_row["total"] or 0)

            # ★ ساخت expert_data با gender
            expert_data = {
                "id": expert["id"],
                "full_name": expert["full_name"],
                "username": expert["username"],
                "avatar": expert["avatar"],
                "gender": expert.get("gender") or "male",    # ★ جدید
                "document_count": int(expert["document_count"] or 0)
            }

            return {
                "department": department,
                "expert": expert_data,
                "statuses": statuses,
                "total": total,
                "available_years": available_years,
                "selected_year": selected_year,
                "area_id": area_id
            }

        finally:
            connection.close()

    # ============================================================
    # ★★★ GET DOCUMENTS JSON — برای AJAX ★★★
    # ============================================================

    @staticmethod
    def get_documents_json(
        department_id,
        expert_id,
        requested_year="all",
        search="",
        page=1,
        area_id=None,
        status_code=None
    ):
        connection = get_connection()

        try:
            selected_year, _ = DepartmentExpertDocumentsService.normalize_year(
                connection, department_id, expert_id,
                requested_year, area_id=area_id
            )

            year_range = DepartmentExpertDocumentsService.get_year_range(
                selected_year
            )

            page = DepartmentExpertDocumentsService.normalize_page(page)
            search = DepartmentExpertDocumentsService.normalize_search(search)

            where_clauses = ["d.department_id = ?", "d.user_id = ?"]
            base_params = [department_id, expert_id]

            if area_id is not None:
                where_clauses.append("d.area_id = ?")
                base_params.append(area_id)

            if year_range:
                where_clauses.append(
                    "d.date_received >= ? AND d.date_received < ?"
                )
                base_params.extend([year_range[0], year_range[1]])

            if status_code:
                where_clauses.append("s.code = ?")
                base_params.append(status_code)

            search_sql, search_params = (
                DepartmentExpertDocumentsService.build_search_sql(search)
            )
            if search_sql:
                where_clauses.append(search_sql)
                base_params.extend(search_params)

            where_sql = " AND ".join(where_clauses)

            total_row = connection.execute(
                f"""
                SELECT COUNT(d.id) AS total
                FROM documents d
                LEFT JOIN document_statuses s ON d.status_id = s.id
                WHERE {where_sql}
                """,
                base_params
            ).fetchone()
            total = int(total_row["total"] or 0)

            page_size = DepartmentExpertDocumentsService.PAGE_SIZE
            total_pages = max(1, (total + page_size - 1) // page_size)
            if page > total_pages:
                page = total_pages

            offset = (page - 1) * page_size

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
                ORDER BY d.id DESC
                LIMIT ? OFFSET ?
                """,
                base_params + [page_size, offset]
            ).fetchall()

            # تبدیل Row → dict + تاریخ شمسی (با استفاده از _safe_get)
            documents = []
            for row in rows:
                doc = dict(row)

                doc["date_letter_jalali"] = (
                    DepartmentExpertDocumentsService._to_jalali_str(
                        DepartmentExpertDocumentsService._safe_get(row, "date_letter")
                    )
                )
                doc["date_received_jalali"] = (
                    DepartmentExpertDocumentsService._to_jalali_str(
                        DepartmentExpertDocumentsService._safe_get(row, "date_received")
                    )
                )
                doc["date_referral_jalali"] = (
                    DepartmentExpertDocumentsService._to_jalali_str(
                        DepartmentExpertDocumentsService._safe_get(row, "date_referral")
                    )
                )
                doc["deadline_jalali"] = (
                    DepartmentExpertDocumentsService._to_jalali_str(
                        DepartmentExpertDocumentsService._safe_get(row, "deadline")
                    )
                )
                doc["created_at_jalali"] = (
                    DepartmentExpertDocumentsService._to_jalali_str(
                        DepartmentExpertDocumentsService._safe_get(row, "created_at")
                    )
                )

                documents.append(doc)

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
            }

        finally:
            connection.close()

    # ============================================================
    # ★ متد قدیمی — نگه‌داشته شد برای سازگاری عقب‌رو
    # ============================================================

    @staticmethod
    def get_documents(
        department_id,
        expert_id,
        requested_year="all",
        search="",
        page=1,
        area_id=None
    ):
        connection = get_connection()

        try:
            department = DepartmentExpertDocumentsService.get_department(
                connection, department_id
            )
            if not department:
                return None

            selected_year, available_years = (
                DepartmentExpertDocumentsService.normalize_year(
                    connection, department_id, expert_id,
                    requested_year, area_id=area_id
                )
            )

            page = DepartmentExpertDocumentsService.normalize_page(page)
            search = DepartmentExpertDocumentsService.normalize_search(search)
            year_range = DepartmentExpertDocumentsService.get_year_range(
                selected_year
            )

            expert = DepartmentExpertDocumentsService.get_expert(
                connection, department_id, expert_id,
                area_id=area_id, year_range=year_range
            )
            if not expert:
                return None

            where_clauses = ["d.department_id = ?", "d.user_id = ?"]
            base_params = [department_id, expert_id]

            if area_id is not None:
                where_clauses.append("d.area_id = ?")
                base_params.append(area_id)

            if year_range:
                where_clauses.append(
                    "d.date_received >= ? AND d.date_received < ?"
                )
                base_params.extend([year_range[0], year_range[1]])

            search_sql, search_params = (
                DepartmentExpertDocumentsService.build_search_sql(search)
            )
            if search_sql:
                where_clauses.append(search_sql)
                base_params.extend(search_params)

            where_sql = " AND ".join(where_clauses)

            total_row = connection.execute(
                f"SELECT COUNT(*) AS total FROM documents d WHERE {where_sql}",
                base_params
            ).fetchone()
            total = int(total_row["total"] or 0)

            page_size = DepartmentExpertDocumentsService.PAGE_SIZE
            total_pages = max(1, (total + page_size - 1) // page_size)
            if page > total_pages:
                page = total_pages

            offset = (page - 1) * page_size

            documents = connection.execute(
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
                ORDER BY d.id DESC
                LIMIT ? OFFSET ?
                """,
                base_params + [page_size, offset]
            ).fetchall()

            statuses = DepartmentExpertDocumentsService.get_statuses(
                connection, where_sql, base_params
            )

            # ★ ساخت expert_data با gender
            expert_data = {
                "id": expert["id"],
                "full_name": expert["full_name"],
                "username": expert["username"],
                "avatar": expert["avatar"],
                "gender": expert.get("gender") or "male",    # ★ جدید
                "document_count": int(expert["document_count"] or 0)
            }

            return {
                "department": department,
                "expert": expert_data,
                "records": documents,
                "documents": documents,
                "statuses": statuses,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "available_years": available_years,
                "selected_year": selected_year,
                "search": search,
                "area_id": area_id
            }

        finally:
            connection.close()