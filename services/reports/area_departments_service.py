import jdatetime
from datetime import datetime
from database.connection import get_connection


class AreaDepartmentsService:

    @staticmethod
    def _to_jalali_year(value):
        if value is None:
            return None

        if isinstance(value, datetime):
            return jdatetime.datetime.fromgregorian(
                datetime=value
            ).year

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
    def get_area(connection, area_id):
        return connection.execute(
            """
            SELECT
                id,
                title,
                code
            FROM areas
            WHERE id=?
            LIMIT 1
            """,
            (area_id,)
        ).fetchone()

    @staticmethod
    def get_available_years(connection, area_id):
        rows = connection.execute(
            """
            SELECT DISTINCT date_received
            FROM documents
            WHERE area_id=?
            AND date_received IS NOT NULL
            AND date_received!=''
            """,
            (area_id,)
        ).fetchall()

        years = set()

        for row in rows:
            year = AreaDepartmentsService._to_jalali_year(
                row["date_received"]
            )

            if year:
                years.add(year)

        return sorted(
            years,
            reverse=True
        )

    @staticmethod
    def normalize_year(
        connection,
        area_id,
        requested_year
    ):
        available_years = (
            AreaDepartmentsService.get_available_years(
                connection,
                area_id
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

        start_gregorian = jdatetime.date(
            year,
            1,
            1
        ).togregorian()

        end_gregorian = jdatetime.date(
            year + 1,
            1,
            1
        ).togregorian()

        return (
            start_gregorian.strftime("%Y/%m/%d"),
            end_gregorian.strftime("%Y/%m/%d")
        )

    @staticmethod
    def get_departments(
        connection,
        area_id,
        selected_year
    ):
        where_clauses = [
            "d.area_id=?",
            "d.department_id IS NOT NULL"
        ]

        params = [
            area_id
        ]

        year_range = AreaDepartmentsService.get_year_range(
            selected_year
        )

        if year_range:
            start_date, end_date = year_range

            where_clauses.append(
                "d.date_received>=? AND d.date_received<?"
            )

            params.extend([
                start_date,
                end_date
            ])

        where_sql = " AND ".join(
            where_clauses
        )

        rows = connection.execute(
            f"""
            SELECT
                dep.id,
                dep.title,
                dep.code,
                COUNT(d.id) AS document_count
            FROM departments dep
            INNER JOIN documents d
                ON d.department_id=dep.id
            WHERE {where_sql}
            GROUP BY
                dep.id,
                dep.title,
                dep.code
            ORDER BY
                dep.id ASC
            """,
            params
        ).fetchall()

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "code": row["code"],
                "count": int(
                    row["document_count"] or 0
                )
            }
            for row in rows
        ]

    @staticmethod
    def get_total_documents(
        connection,
        area_id,
        selected_year
    ):
        where_clauses = [
            "area_id=?"
        ]

        params = [
            area_id
        ]

        year_range = AreaDepartmentsService.get_year_range(
            selected_year
        )

        if year_range:
            start_date, end_date = year_range

            where_clauses.append(
                "date_received>=? AND date_received<?"
            )

            params.extend([
                start_date,
                end_date
            ])

        where_sql = " AND ".join(
            where_clauses
        )

        row = connection.execute(
            f"""
            SELECT
                COUNT(*) AS total
            FROM documents
            WHERE {where_sql}
            """,
            params
        ).fetchone()

        return int(
            row["total"] or 0
        )

    @staticmethod
    def get_report(
        area_id,
        requested_year="all"
    ):
        connection = get_connection()

        try:
            area = AreaDepartmentsService.get_area(
                connection,
                area_id
            )

            if not area:
                return None

            selected_year, available_years = (
                AreaDepartmentsService.normalize_year(
                    connection,
                    area_id,
                    requested_year
                )
            )

            departments = (
                AreaDepartmentsService.get_departments(
                    connection,
                    area_id,
                    selected_year
                )
            )

            total_documents = (
                AreaDepartmentsService.get_total_documents(
                    connection,
                    area_id,
                    selected_year
                )
            )

            return {
                "area": area,
                "departments": departments,
                "available_years": available_years,
                "selected_year": selected_year,
                "total_documents": total_documents,
                "area_id":area_id
                
                
            }

        finally:
            connection.close()