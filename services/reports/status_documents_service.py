from datetime import datetime
import jdatetime
from database.connection import get_connection
class StatusDocumentsService:
    PAGE_SIZE=30
    SEARCH_FIELDS=[
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
    @staticmethod
    def _to_jalali_year(value):
        if value is None:
            return None
        if isinstance(value,datetime):
            return jdatetime.datetime.fromgregorian(
                datetime=value
            ).year
        value=str(value).strip()
        if not value:
            return None
        value=value.replace("/","-")
        try:
            parts=value.split("-")
            if len(parts)>=3:
                year=int(parts[0])
                month=int(parts[1])
                day=int(parts[2].split(" ")[0])
                if year<1700:
                    return year
                return jdatetime.date.fromgregorian(
                    year=year,
                    month=month,
                    day=day
                ).year
        except (ValueError,TypeError):
            return None
        return None
    @staticmethod
    def normalize_search(value):
        value=str(value or "").strip().lower()
        value=value.replace("ي","ی").replace("ك","ک")
        return value
    @staticmethod
    def get_status(connection,status_code):
        return connection.execute(
            """
            SELECT
                id,
                title,
                code,
                color,
                sort_order
            FROM document_statuses
            WHERE code=?
            AND is_active=1
            LIMIT 1
            """,
            (status_code,)
        ).fetchone()
    @staticmethod
    def build_search_sql(search):
        if not search:
            return "",[]
        conditions=[]
        params=[]
        for field in StatusDocumentsService.SEARCH_FIELDS:
            normalized_field=(
                f"REPLACE("
                f"REPLACE("
                f"LOWER(COALESCE({field},'')),"
                f"'ي','ی'"
                f"),"
                f"'ك','ک'"
                f")"
            )
            conditions.append(
                f"{normalized_field} LIKE ?"
            )
            params.append(
                f"%{search}%"
            )
        return (
            "("+" OR ".join(conditions)+")",
            params
        )
    @staticmethod
    def normalize_page(page):
        try:
            page=int(page)
        except (ValueError,TypeError):
            page=1
        if page<1:
            page=1
        return page
    @staticmethod
    def get_available_years(connection):
        rows=connection.execute(
            """
            SELECT DISTINCT date_received
            FROM documents
            WHERE date_received IS NOT NULL
            AND date_received!=''
            """
        ).fetchall()
        years=set()
        for row in rows:
            year=StatusDocumentsService._to_jalali_year(
                row["date_received"]
            )
            if year:
                years.add(year)
        return sorted(
            years,
            reverse=True
        )
    @staticmethod
    def normalize_year(connection,requested_year):
        available_years=StatusDocumentsService.get_available_years(
            connection
        )
        if requested_year in (None,"","all"):
            return "all",available_years
        try:
            selected_year=int(requested_year)
        except (ValueError,TypeError):
            return "all",available_years
        if selected_year not in available_years:
            return "all",available_years
        return selected_year,available_years
    @staticmethod
    def get_year_range(year):
        if year=="all" or year is None:
            return None
        try:
            year=int(year)
        except (ValueError,TypeError):
            return None
        start_gregorian=jdatetime.date(
            year,
            1,
            1
        ).togregorian()
        end_gregorian=jdatetime.date(
            year+1,
            1,
            1
        ).togregorian()
        return (
            start_gregorian.strftime("%Y/%m/%d"),
            end_gregorian.strftime("%Y/%m/%d")
        )
    @staticmethod
    def get_documents(
        status_code,
        requested_year="all",
        search="",
        page=1
    ):
        connection=get_connection()
        try:
            status=StatusDocumentsService.get_status(
                connection,
                status_code
            )
            if not status:
                return None
            selected_year,available_years=(
                StatusDocumentsService.normalize_year(
                    connection,
                    requested_year
                )
            )
            page=StatusDocumentsService.normalize_page(
                page
            )
            search=StatusDocumentsService.normalize_search(
                search
            )
            where_clauses=[
                "d.status_id=?"
            ]
            base_params=[
                status["id"]
            ]
            year_range=StatusDocumentsService.get_year_range(
                selected_year
            )
            if year_range:
                start_date,end_date=year_range
                where_clauses.append(
                    "d.date_received>=? AND d.date_received<?"
                )
                base_params.extend([
                    start_date,
                    end_date
                ])
            search_sql,search_params=(
                StatusDocumentsService.build_search_sql(
                    search
                )
            )
            if search_sql:
                where_clauses.append(
                    search_sql
                )
                base_params.extend(
                    search_params
                )
            where_sql=" AND ".join(
                where_clauses
            )
            total_row=connection.execute(
                f"""
                SELECT
                    COUNT(*) AS total
                FROM documents d
                WHERE {where_sql}
                """,
                base_params
            ).fetchone()
            total=int(
                total_row["total"] or 0
            )
            page_size=StatusDocumentsService.PAGE_SIZE
            total_pages=max(
                1,
                (total+page_size-1)//page_size
            )
            if page>total_pages:
                page=total_pages
            offset=(page-1)*page_size
            documents=connection.execute(
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
                LEFT JOIN users u
                    ON d.user_id=u.id
                LEFT JOIN document_statuses s
                    ON d.status_id=s.id
                LEFT JOIN areas a
                    ON d.area_id=a.id
                LEFT JOIN departments dep
                    ON d.department_id=dep.id
                WHERE {where_sql}
                ORDER BY d.id DESC
                LIMIT ? OFFSET ?
                """,
                base_params+[
                    page_size,
                    offset
                ]
            ).fetchall()
            return {
                "status":status,
                "documents":documents,
                "total":total,
                "page":page,
                "page_size":page_size,
                "total_pages":total_pages,
                "available_years":available_years,
                "selected_year":selected_year,
                "search":search
            }
        finally:
            connection.close()