from datetime import datetime
import jdatetime
from database.connection import get_connection


class DepartmentPerformanceService:
    """
    سرویس تحلیل عملکرد دپارتمان‌ها

    ★ وضعیت‌ها بر اساس code تفکیک می‌شن:
      - completed      → تکمیل‌شده
      - in_progress    → باقی‌مانده فعال
      - informational  → خارج از محاسبه
      - stopped        → خارج از محاسبه
      - deleted        → خارج از محاسبه
      - unknown/None   → باقی‌مانده فعال (اگه status_id نداشته باشه)
    """

    # ★ کدهای خارج از محاسبه
    EXCLUDED_CODES = {"deleted", "stopped", "informational"}

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _to_jalali_month(value):
        if value is None:
            return None, None

        try:
            if isinstance(value, datetime):
                jd = jdatetime.datetime.fromgregorian(datetime=value)
                return jd.year, jd.month

            value_str = str(value).strip().replace("/", "-")
            parts = value_str.split("-")

            if len(parts) >= 3:
                y = int(parts[0])
                m = int(parts[1])
                d = int(parts[2].split(" ")[0])

                if y < 1700:
                    return y, m

                jd = jdatetime.date.fromgregorian(year=y, month=m, day=d)
                return jd.year, jd.month

        except (ValueError, TypeError):
            return None, None

        return None, None

    @staticmethod
    def _to_jalali_year(value):
        year, _ = DepartmentPerformanceService._to_jalali_month(value)
        return year

    @staticmethod
    def _get_year_range(year):
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
    def _categorize_status(code):
        """
        دسته‌بندی وضعیت:
          completed → تکمیل‌شده
          excluded  → خارج از محاسبه
          pending   → باقی‌مانده فعال
        """
        if code == "completed":
            return "completed"
        if code in DepartmentPerformanceService.EXCLUDED_CODES:
            return "excluded"
        return "pending"

    # ============================================================
    # METADATA
    # ============================================================

    @staticmethod
    def get_available_years(connection):
        rows = connection.execute(
            """
            SELECT DISTINCT date_received
            FROM documents
            WHERE date_received IS NOT NULL
              AND date_received != ''
            """
        ).fetchall()

        years = set()
        for row in rows:
            year = DepartmentPerformanceService._to_jalali_year(
                row["date_received"]
            )
            if year:
                years.add(year)

        return sorted(years, reverse=True)

    @staticmethod
    def get_departments(connection):
        rows = connection.execute(
            """
            SELECT id, title, code
            FROM departments
            ORDER BY title COLLATE NOCASE ASC
            """
        ).fetchall()

        return [dict(r) for r in rows]

    # ============================================================
    # ★★★ ۱) SUMMARY ★★★
    # ============================================================

    @staticmethod
    def get_summary(year="all", department_id=None, area_id=None):
        connection = get_connection()

        try:
            where_clauses = []
            params = []

            year_range = DepartmentPerformanceService._get_year_range(year)
            if year_range:
                where_clauses.append(
                    "d.date_received >= ? AND d.date_received < ?"
                )
                params.extend([year_range[0], year_range[1]])

            if department_id:
                where_clauses.append("d.department_id = ?")
                params.append(department_id)

            if area_id:
                where_clauses.append("d.area_id = ?")
                params.append(area_id)

            where_sql = (
                " AND ".join(where_clauses)
                if where_clauses else "1=1"
            )

            # ★ گروه‌بندی بر اساس code
            status_rows = connection.execute(
                f"""
                SELECT
                    s.code AS status_code,
                    s.title AS status_title,
                    s.color AS status_color,
                    COUNT(d.id) AS count
                FROM documents d
                LEFT JOIN document_statuses s ON d.status_id = s.id
                WHERE {where_sql}
                GROUP BY s.code, s.title, s.color
                """,
                params
            ).fetchall()

            total = 0
            completed = 0
            pending = 0
            excluded = 0
            status_breakdown = []

            for row in status_rows:
                code = row["status_code"] or "unknown"
                title = row["status_title"] or "بدون وضعیت"
                color = row["status_color"] or "#94a3b8"
                count = int(row["count"] or 0)

                total += count
                category = DepartmentPerformanceService._categorize_status(code)

                if category == "completed":
                    completed += count
                elif category == "pending":
                    pending += count
                else:
                    excluded += count

                status_breakdown.append({
                    "code": code,
                    "title": title,
                    "color": color,
                    "count": count,
                    "category": category
                })

            # ★ مرتب‌سازی
            category_order = {
                "completed": 0,
                "pending": 1,
                "excluded": 2
            }
            status_breakdown.sort(
                key=lambda x: (
                    category_order.get(x["category"], 9),
                    -x["count"]
                )
            )

            # ★ نرخ تکمیل
            effective_total = completed + pending
            completion_rate = 0
            if effective_total > 0:
                completion_rate = round(
                    (completed / effective_total) * 100, 1
                )

            return {
                "total": total,
                "completed": completed,
                "pending": pending,
                "excluded": excluded,
                "effective_total": effective_total,
                "completion_rate": completion_rate,
                "status_breakdown": status_breakdown
            }

        finally:
            connection.close()

    # ============================================================
    # ★★★ ۲) MONTHLY TREND ★★★
    # ============================================================

    @staticmethod
    def get_monthly_trend(year="all", department_id=None, area_id=None):
        connection = get_connection()

        try:
            where_clauses = []
            params = []

            year_range = DepartmentPerformanceService._get_year_range(year)
            if year_range:
                where_clauses.append(
                    "d.date_received >= ? AND d.date_received < ?"
                )
                params.extend([year_range[0], year_range[1]])

            if department_id:
                where_clauses.append("d.department_id = ?")
                params.append(department_id)

            if area_id:
                where_clauses.append("d.area_id = ?")
                params.append(area_id)

            where_sql = (
                " AND ".join(where_clauses)
                if where_clauses else "1=1"
            )

            rows = connection.execute(
                f"""
                SELECT
                    d.date_received,
                    s.code AS status_code
                FROM documents d
                LEFT JOIN document_statuses s ON d.status_id = s.id
                WHERE {where_sql}
                  AND d.date_received IS NOT NULL
                  AND d.date_received != ''
                """,
                params
            ).fetchall()

            if year == "all" or year is None:
                months_set = set()
                for row in rows:
                    y, m = DepartmentPerformanceService._to_jalali_month(
                        row["date_received"]
                    )
                    if y and m:
                        months_set.add((y, m))
                all_months = sorted(months_set, key=lambda x: (x[0], x[1]))
            else:
                try:
                    y = int(year)
                    all_months = [(y, m) for m in range(1, 13)]
                except (ValueError, TypeError):
                    all_months = []

            monthly = {}
            for y, m in all_months:
                monthly[(y, m)] = {
                    "total": 0,
                    "completed": 0,
                    "pending": 0,
                    "excluded": 0
                }

            for row in rows:
                y, m = DepartmentPerformanceService._to_jalali_month(
                    row["date_received"]
                )
                if not y or not m:
                    continue

                key = (y, m)
                if key not in monthly:
                    monthly[key] = {
                        "total": 0,
                        "completed": 0,
                        "pending": 0,
                        "excluded": 0
                    }

                monthly[key]["total"] += 1
                code = row["status_code"]
                category = DepartmentPerformanceService._categorize_status(code)

                if category == "completed":
                    monthly[key]["completed"] += 1
                elif category == "pending":
                    monthly[key]["pending"] += 1
                else:
                    monthly[key]["excluded"] += 1

            month_names = [
                "فروردین", "اردیبهشت", "خرداد", "تیر",
                "مرداد", "شهریور", "مهر", "آبان",
                "آذر", "دی", "بهمن", "اسفند"
            ]

            labels = []
            total_data = []
            completed_data = []
            pending_data = []

            for y, m in all_months:
                if year == "all":
                    labels.append(f"{month_names[m - 1]} {y}")
                else:
                    labels.append(month_names[m - 1])

                data = monthly.get((y, m), {
                    "total": 0, "completed": 0,
                    "pending": 0, "excluded": 0
                })

                effective_total = data["completed"] + data["pending"]

                total_data.append(effective_total)
                completed_data.append(data["completed"])
                pending_data.append(data["pending"])

            return {
                "labels": labels,
                "total": total_data,
                "completed": completed_data,
                "pending": pending_data
            }

        finally:
            connection.close()

    # ============================================================
    # ★★★ ۳) RANKING ★★★
    # ============================================================

    @staticmethod
    def get_department_ranking(year="all", area_id=None):
        connection = get_connection()

        try:
            where_clauses = []
            params = []

            year_range = DepartmentPerformanceService._get_year_range(year)
            if year_range:
                where_clauses.append(
                    "d.date_received >= ? AND d.date_received < ?"
                )
                params.extend([year_range[0], year_range[1]])

            if area_id:
                where_clauses.append("d.area_id = ?")
                params.append(area_id)

            where_sql = (
                " AND ".join(where_clauses)
                if where_clauses else "1=1"
            )

            # ★ همه اسناد با code وضعیت
            rows = connection.execute(
                f"""
                SELECT
                    dep.id AS department_id,
                    dep.title AS department_title,
                    dep.code AS department_code,
                    COUNT(d.id) AS total,
                    s.code AS status_code
                FROM departments dep
                LEFT JOIN documents d ON d.department_id = dep.id
                LEFT JOIN document_statuses s ON d.status_id = s.id
                WHERE {where_sql}
                   OR d.id IS NULL
                GROUP BY dep.id, dep.title, dep.code, s.code
                """,
                params
            ).fetchall()

            # ★ جمع‌آوری در پایتون (چون تقسیم در SQL وابسته به کدهاست)
            dept_map = {}

            for row in rows:
                did = row["department_id"]
                if did not in dept_map:
                    dept_map[did] = {
                        "department_id": did,
                        "department_title": row["department_title"],
                        "department_code": row["department_code"],
                        "total": 0,
                        "completed": 0,
                        "pending": 0,
                        "excluded": 0,
                        "effective_total": 0,
                        "completion_rate": 0,
                        "normalized_volume": 0,
                        "score": 0
                    }

                dept_map[did]["total"] += int(row["total"] or 0)

                code = row["status_code"]
                if code is None:
                    # ★ اسنادی که status_id ندارن → pending
                    dept_map[did]["pending"] += int(row["total"] or 0)
                else:
                    category = DepartmentPerformanceService._categorize_status(code)
                    if category == "completed":
                        dept_map[did]["completed"] += int(row["total"] or 0)
                    elif category == "pending":
                        dept_map[did]["pending"] += int(row["total"] or 0)
                    else:
                        dept_map[did]["excluded"] += int(row["total"] or 0)

            # ★ محاسبه نرخ و امتیاز
            results = []
            max_effective_total = 0

            for did, item in dept_map.items():
                effective_total = item["completed"] + item["pending"]
                item["effective_total"] = effective_total

                if effective_total == 0:
                    continue

                item["completion_rate"] = round(
                    (item["completed"] / effective_total) * 100, 1
                )

                if effective_total > max_effective_total:
                    max_effective_total = effective_total

                results.append(item)

            RATE_WEIGHT = 0.6
            VOLUME_WEIGHT = 0.4

            for r in results:
                if max_effective_total > 0:
                    r["normalized_volume"] = round(
                        (r["effective_total"] / max_effective_total) * 100, 1
                    )

                r["score"] = round(
                    (r["completion_rate"] * RATE_WEIGHT) +
                    (r["normalized_volume"] * VOLUME_WEIGHT),
                    1
                )

            results.sort(
                key=lambda x: (-x["score"], -x["completed"], -x["effective_total"])
            )

            return results

        finally:
            connection.close()

    # ============================================================
    # ★★★ ۴) DASHBOARD DATA ★★★
    # ============================================================

    @staticmethod
    def get_dashboard_data(year="all", department_id=None, area_id=None):
        connection = get_connection()

        try:
            available_years = DepartmentPerformanceService.get_available_years(
                connection
            )
            departments = DepartmentPerformanceService.get_departments(
                connection
            )

        finally:
            connection.close()

        summary = DepartmentPerformanceService.get_summary(
            year=year,
            department_id=department_id,
            area_id=area_id
        )

        monthly_trend = DepartmentPerformanceService.get_monthly_trend(
            year=year,
            department_id=department_id,
            area_id=area_id
        )

        ranking = DepartmentPerformanceService.get_department_ranking(
            year=year,
            area_id=area_id
        )

        return {
            "success": True,
            "summary": summary,
            "monthly_trend": monthly_trend,
            "ranking": ranking,
            "available_years": available_years,
            "departments": departments,
            "filters": {
                "year": year,
                "department_id": department_id,
                "area_id": area_id
            }
        }
        
        
     # ============================================================
    # ★★★ ۵) MONTHLY PER DEPARTMENT — برای Brush روی رتبه‌بندی ★★★
    # ============================================================

    @staticmethod
    def get_monthly_per_department(year="all", department_id=None, area_id=None):
        """
        داده ماهانه هر دپارتمان رو برمی‌گردونه.
        برای محاسبه امتیاز در بازه زمانی دلخواه (Brush).

        خروجی:
        {
            'months': ['فروردین 1403', 'اردیبهشت 1403', ...],  # ترتیب ماه‌ها
            'departments': [
                {
                    'id': 1,
                    'title': 'دپارتمان الف',
                    'excluded_total': 15,
                    'monthly': [
                        {'effective': 12, 'completed': 8, 'pending': 4},  # ماه 0
                        {'effective': 15, 'completed': 10, 'pending': 5}, # ماه 1
                        ...
                    ]
                },
                ...
            ]
        }
        """
        connection = get_connection()

        try:
            where_clauses = []
            params = []

            year_range = DepartmentPerformanceService._get_year_range(year)
            if year_range:
                where_clauses.append(
                    "d.date_received >= ? AND d.date_received < ?"
                )
                params.extend([year_range[0], year_range[1]])

            if department_id:
                where_clauses.append("d.department_id = ?")
                params.append(department_id)

            if area_id:
                where_clauses.append("d.area_id = ?")
                params.append(area_id)

            where_sql = (
                " AND ".join(where_clauses)
                if where_clauses else "1=1"
            )

            # ★ همه اسناد با department + date + status
            rows = connection.execute(
                f"""
                SELECT
                    dep.id AS department_id,
                    dep.title AS department_title,
                    d.date_received,
                    s.code AS status_code
                FROM departments dep
                LEFT JOIN documents d ON d.department_id = dep.id
                LEFT JOIN document_statuses s ON d.status_id = s.id
                WHERE (d.id IS NULL OR ({where_sql}))
                """,
                params
            ).fetchall()

            # ★ پیدا کردن همه ماه‌های موجود
            months_set = set()
            for row in rows:
                y, m = DepartmentPerformanceService._to_jalali_month(
                    row["date_received"]
                )
                if y and m:
                    months_set.add((y, m))

            # ★ اگه سال خاصی انتخاب شده، همه ۱۲ ماه سال
            if year != "all" and year is not None:
                try:
                    y = int(year)
                    months_list = [(y, m) for m in range(1, 13)]
                except (ValueError, TypeError):
                    months_list = sorted(months_set, key=lambda x: (x[0], x[1]))
            else:
                months_list = sorted(months_set, key=lambda x: (x[0], x[1]))

            if not months_list:
                return {
                    "months": [],
                    "months_short": [],
                    "departments": []
                }

            # ★ ایندکس ماه‌ها برای دسترسی سریع
            month_index = {ym: i for i, ym in enumerate(months_list)}

            month_names_short = [
                "فرو", "ارد", "خرد", "تیر",
                "مرد", "شهر", "مهر", "آبا",
                "آذر", "دی", "بهم", "اسف"
            ]
            month_names_full = [
                "فروردین", "اردیبهشت", "خرداد", "تیر",
                "مرداد", "شهریور", "مهر", "آبان",
                "آذر", "دی", "بهمن", "اسفند"
            ]

            months_labels = []
            months_labels_short = []

            for y, m in months_list:
                if year == "all":
                    months_labels.append(f"{month_names_full[m - 1]} {y}")
                    months_labels_short.append(f"{month_names_short[m - 1]} {str(y)[-2:]}")
                else:
                    months_labels.append(month_names_full[m - 1])
                    months_labels_short.append(month_names_short[m - 1])

            # ★ ساختار per-department
            dept_map = {}

            for row in rows:
                did = row["department_id"]
                if did is None:
                    continue

                if did not in dept_map:
                    dept_map[did] = {
                        "id": did,
                        "title": row["department_title"],
                        "excluded_total": 0,
                        "monthly": [
                            {"effective": 0, "completed": 0, "pending": 0}
                            for _ in months_list
                        ]
                    }

                y, m = DepartmentPerformanceService._to_jalali_month(
                    row["date_received"]
                )
                if not y or not m:
                    continue

                key = (y, m)
                if key not in month_index:
                    continue

                idx = month_index[key]
                code = row["status_code"]
                category = DepartmentPerformanceService._categorize_status(code)

                if category == "completed":
                    dept_map[did]["monthly"][idx]["completed"] += 1
                    dept_map[did]["monthly"][idx]["effective"] += 1
                elif category == "pending":
                    dept_map[did]["monthly"][idx]["pending"] += 1
                    dept_map[did]["monthly"][idx]["effective"] += 1
                else:
                    dept_map[did]["excluded_total"] += 1

            return {
                "months": months_labels,
                "months_short": months_labels_short,
                "departments": list(dept_map.values())
            }

        finally:
            connection.close()       