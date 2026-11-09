from datetime import datetime
import jdatetime
from database.connection import get_connection
class StatusReportService:
    @staticmethod
    def _to_jalali_year(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return jdatetime.datetime.fromgregorian(
                datetime=value
            ).year
        value=str(value).strip()
        if not value:
            return None
        value=value.replace("/", "-")
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
            year=StatusReportService._to_jalali_year(
                row["date_received"]
            )
            if year:
                years.add(year)
        return sorted(
            years,
            reverse=True
        )
    @staticmethod
    def get_statuses(connection):
        return connection.execute(
            """
            SELECT
                id,
                title,
                code,
                color,
                sort_order
            FROM document_statuses
            WHERE is_active=1
            ORDER BY sort_order ASC,id ASC
            """
        ).fetchall()
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
    def get_report_data(requested_year="all"):
        connection=get_connection()
        try:
            available_years=StatusReportService.get_available_years(
                connection
            )
            if requested_year=="all":
                selected_year="all"
            else:
                try:
                    selected_year=int(requested_year)
                except (ValueError,TypeError):
                    selected_year="all"
                if selected_year not in available_years:
                    selected_year="all"
            statuses=StatusReportService.get_statuses(
                connection
            )
            year_range=StatusReportService.get_year_range(
                selected_year
            )
            where_clauses=[]
            params=[]
            if year_range:
                where_clauses.append(
                    "d.date_received>=? AND d.date_received<?"
                )
                params.extend(
                    year_range
                )
            where_sql=""
            if where_clauses:
                where_sql="WHERE "+" AND ".join(
                    where_clauses
                )
            rows=connection.execute(
                f"""
                SELECT
                    d.status_id,
                    COUNT(*) AS total
                FROM documents d
                {where_sql}
                GROUP BY d.status_id
                """,
                params
            ).fetchall()
            counts={
                row["status_id"]:row["total"]
                for row in rows
            }
            statistics=[]
            total=0
            for status in statuses:
                count=counts.get(
                    status["id"],
                    0
                )
                total+=count
                statistics.append({
                    "id":status["id"],
                    "title":status["title"],
                    "code":status["code"],
                    "color":status["color"],
                    "sort_order":status["sort_order"],
                    "count":count
                })
            return {
                "statuses":statistics,
                "total":total,
                "available_years":available_years,
                "selected_year":selected_year
            }
        finally:
            connection.close()