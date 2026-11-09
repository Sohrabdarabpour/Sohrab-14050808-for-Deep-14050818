from database.connection import get_connection
from database.documents import add_document, delete_document
from helpers.date_helper import DateHelper
class DocumentService:
    @staticmethod
    def get_all():
        connection = get_connection()
        try:
            return connection.execute(
                """
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
                ORDER BY d.id DESC
                """
            ).fetchall()
        finally:
            connection.close()
    @staticmethod
    def get_by_id(document_id):
        connection = get_connection()
        try:
            return connection.execute(
                """
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
                WHERE d.id = ?
                """,
                (document_id,)
            ).fetchone()
        finally:
            connection.close()
    @staticmethod
    def get_available_years():
        """سال‌های شمسی موجود — فقط ستون تاریخ خوانده می‌شود، نه کل اسناد."""
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT DISTINCT date_received
                FROM documents
                WHERE IFNULL(date_received, '') <> ''
                """
            ).fetchall()
        finally:
            connection.close()

        years = set()
        for row in rows:
            year = DateHelper.get_jalali_year(row["date_received"])
            if year:
                years.add(year)

        return sorted(years, reverse=True)
    @staticmethod
    def get_filtered_documents(year="all"):
        documents = DocumentService.get_all()
        if year == "all":
            return documents
        try:
            selected_year = int(year)
        except (ValueError, TypeError):
            return documents
        filtered_documents = []
        for document in documents:
            document_year = DateHelper.get_jalali_year(
                document["date_received"]
            )
            if document_year == selected_year:
                filtered_documents.append(document)
        return filtered_documents
    @staticmethod
    def get_statistics(documents):
        status_statistics = {}
        department_statistics = {}
        area_statistics = {}
        for document in documents:
            status_id = document["status_id"]
            status_code = document["status_code"] or "undefined"
            status_title = document["status_title"] or "بدون وضعیت"
            status_color = document["status_color"] or "#95A5A6"
            status_key = status_id if status_id is not None else status_code
            if status_key not in status_statistics:
                status_statistics[status_key] = {
                    "id": status_id,
                    "code": status_code,
                    "title": status_title,
                    "color": status_color,
                    "count": 0
                }
            status_statistics[status_key]["count"] += 1
            department_id = document["department_id"]
            department_title = document["department_title"] or "بدون دپارتمان"
            department_code = document["department_code"] or "undefined"
            department_key = department_id if department_id is not None else department_code
            if department_key not in department_statistics:
                department_statistics[department_key] = {
                    "id": department_id,
                    "code": department_code,
                    "title": department_title,
                    "count": 0
                }
            department_statistics[department_key]["count"] += 1
            area_id = document["area_id"]
            area_title = (
                document["area_title"]
                or document["area"]
                or "بدون ناحیه"
            )
            area_code = document["area_code"] or "undefined"
            area_key = area_id if area_id is not None else area_code
            if area_key not in area_statistics:
                area_statistics[area_key] = {
                    "id": area_id,
                    "code": area_code,
                    "title": area_title,
                    "count": 0
                }
            area_statistics[area_key]["count"] += 1
        statuses = list(status_statistics.values())
        departments = list(department_statistics.values())
        areas = list(area_statistics.values())
        statuses.sort(
            key=lambda item: (
                item["title"] == "بدون وضعیت",
                -item["count"]
            )
        )
        departments.sort(
            key=lambda item: (
                item["title"] == "بدون دپارتمان",
                -item["count"]
            )
        )
        areas.sort(
            key=lambda item: (
                item["title"] == "بدون ناحیه",
                -item["count"]
            )
        )
        return {
            "total": len(documents),
            "statuses": statuses,
            "departments": departments,
            "areas": areas
        }
    # ============================================================
    # ★ صفحه‌بندی و آمار در SQL (بدون بارگذاری کل جدول)
    # ============================================================
    PAGE_SIZE = 24
    MAX_PAGE_SIZE = 100

    #: ستون‌ها و joinهای مشترک بین شمارش، صفحه و آمار
    _LIST_SQL = """
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
    """

    @staticmethod
    def _year_filter(year):
        """شرط SQL برای فیلتر سال شمسی → (where, params)."""
        date_range = DateHelper.get_gregorian_range_from_jalali_year(year)
        if not date_range:
            return "", ()
        return "AND d.date_received >= ? AND d.date_received < ?", date_range

    @staticmethod
    def get_page(year="all", page=1, per_page=None):
        """یک صفحه از اسناد + اطلاعات صفحه‌بندی.

        Returns:
            dict با کلیدهای records, total, page, pages, per_page
        """
        per_page = per_page or DocumentService.PAGE_SIZE
        try:
            per_page = max(1, min(int(per_page), DocumentService.MAX_PAGE_SIZE))
        except (TypeError, ValueError):
            per_page = DocumentService.PAGE_SIZE

        try:
            page = max(1, int(page))
        except (TypeError, ValueError):
            page = 1

        where_sql, params = DocumentService._year_filter(year)

        connection = get_connection()
        try:
            total_row = connection.execute(
                f"SELECT COUNT(*) AS c FROM documents d WHERE 1=1 {where_sql}",
                params,
            ).fetchone()
            total = int(total_row["c"] or 0) if total_row else 0

            pages = max(1, (total + per_page - 1) // per_page) if total else 1
            page = min(page, pages)
            offset = (page - 1) * per_page

            if total:
                records = connection.execute(
                    f"""
                    {DocumentService._LIST_SQL}
                    WHERE 1=1 {where_sql}
                    ORDER BY d.id DESC
                    LIMIT ? OFFSET ?
                    """,
                    params + (per_page, offset),
                ).fetchall()
            else:
                records = []
        finally:
            connection.close()

        return {
            "records": records,
            "total": total,
            "page": page,
            "pages": pages,
            "per_page": per_page,
        }

    @staticmethod
    def get_statistics(year="all"):
        """آمار وضعیت/دپارتمان/ناحیه با GROUP BY — بدون حلقه در پایتون."""
        where_sql, params = DocumentService._year_filter(year)
        connection = get_connection()
        try:
            total_row = connection.execute(
                f"SELECT COUNT(*) AS c FROM documents d WHERE 1=1 {where_sql}",
                params,
            ).fetchone()
            total = int(total_row["c"] or 0) if total_row else 0

            statuses = [
                dict(row)
                for row in connection.execute(
                    f"""
                    SELECT
                        s.id AS id,
                        COALESCE(s.code, 'undefined') AS code,
                        COALESCE(s.title, 'بدون وضعیت') AS title,
                        COALESCE(s.color, '#95A5A6') AS color,
                        COUNT(*) AS count
                    FROM documents d
                    LEFT JOIN document_statuses s ON s.id = d.status_id
                    WHERE 1=1 {where_sql}
                    GROUP BY s.id, s.code, s.title, s.color
                    ORDER BY (s.id IS NULL) ASC, count DESC
                    """,
                    params,
                ).fetchall()
            ]

            departments = [
                dict(row)
                for row in connection.execute(
                    f"""
                    SELECT
                        dep.id AS id,
                        COALESCE(dep.code, 'undefined') AS code,
                        COALESCE(dep.title, 'بدون دپارتمان') AS title,
                        COUNT(*) AS count
                    FROM documents d
                    LEFT JOIN departments dep ON dep.id = d.department_id
                    WHERE 1=1 {where_sql}
                    GROUP BY dep.id, dep.code, dep.title
                    ORDER BY (dep.id IS NULL) ASC, count DESC
                    """,
                    params,
                ).fetchall()
            ]

            areas = [
                dict(row)
                for row in connection.execute(
                    f"""
                    SELECT
                        a.id AS id,
                        COALESCE(a.code, 'undefined') AS code,
                        CASE
                            WHEN a.id IS NULL THEN 'بدون ناحیه'
                            ELSE COALESCE(a.title, 'بدون ناحیه')
                        END AS title,
                        COUNT(*) AS count
                    FROM documents d
                    LEFT JOIN areas a ON a.id = d.area_id
                    WHERE 1=1 {where_sql}
                    GROUP BY a.id, a.code, a.title
                    ORDER BY (a.id IS NULL) ASC, count DESC
                    """,
                    params,
                ).fetchall()
            ]
        finally:
            connection.close()

        return {
            "total": total,
            "statuses": statuses,
            "departments": departments,
            "areas": areas,
        }

    @staticmethod
    def create(data):
        return add_document(data)
    @staticmethod
    def update(document_id, data):
        if not data:
            return False
        connection = get_connection()
        fields = list(data.keys())
        values = [data[field] for field in fields]
        set_clause = ", ".join(
            [f"{field} = ?" for field in fields]
        )
        values.append(document_id)
        try:
            cursor = connection.execute(
                f"""
                UPDATE documents
                SET {set_clause}
                WHERE id = ?
                """,
                values
            )
            connection.commit()
            return cursor.rowcount > 0
        except Exception:
            connection.rollback()
            return False
        finally:
            connection.close()
    @staticmethod
    def delete(document_id):
        return delete_document(document_id)